from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import os, json, logging
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import stripe

from services.scoring import score_deal
from services.matching import match_buyers
from services.ai_assistant import analyze_deal

# Optional
try:
    from services.notifications import notify_buyers_for_deal
except:
    def notify_buyers_for_deal(deal_id): pass

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vortexai")

app = FastAPI(title="VortexAI", version="5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_PRO = os.getenv("STRIPE_PRICE_PRO", "")
STRIPE_PRICE_VIP = os.getenv("STRIPE_PRICE_VIP", "")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


def db():
    return psycopg2.connect(DATABASE_URL)


def json_dump(obj):
    return json.dumps(obj) if obj else None


def is_paid(role: str):
    return role in ["buyer_paid", "enterprise", "admin"]


def price_to_role(price_id: str):
    if price_id == STRIPE_PRICE_VIP:
        return "enterprise"
    return "buyer_paid"


# ======================
# MODELS
# ======================

class DealData(BaseModel):
    name: str
    email: str = ""
    asset_type: str
    location: str
    price: float
    description: str = ""
    url: Optional[str] = None
    source: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BuyerRegister(BaseModel):
    name: str
    email: str
    location: str = ""
    asset_types: str = "real_estate"
    min_budget: float = 0
    max_budget: float = 10000000
    phone: str = ""


# ======================
# ROOT
# ======================

@app.get("/")
def root():
    return {"status": "VortexAI running"}


# ======================
# DEAL INGEST PIPELINE
# ======================

@app.post("/admin/webhooks/deal-ingest")
def ingest_deal(data: DealData):

    conn = db()
    cur = conn.cursor()

    try:
        deal = data.dict()

        # LEVEL 2 – scoring
        scores = score_deal(deal)
        deal.update(scores)

        cur.execute("""
            INSERT INTO deals
            (name,email,asset_type,location,price,description,
             profit_score,urgency_score,risk_score,score,url,source,metadata,created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
            RETURNING id
        """, (
            deal["name"], deal.get("email",""), deal["asset_type"], deal["location"],
            deal["price"], deal.get("description",""),
            deal["profit_score"], deal["urgency_score"], deal["risk_score"],
            deal["ai_score"], deal.get("url"), deal.get("source"), json_dump(deal.get("metadata"))
        ))

        deal_id = cur.fetchone()[0]

        # LEVEL 3 – buyer matching
        cur2 = conn.cursor(cursor_factory=RealDictCursor)
        cur2.execute("SELECT * FROM buyers WHERE active=true")
        buyers = cur2.fetchall()
        cur2.close()

        paid_buyers = [b for b in buyers if is_paid(b.get("role",""))]

        matches = match_buyers({**deal, "id": deal_id}, paid_buyers)

        for m in matches:
            cur.execute("""
                INSERT INTO deal_matches (deal_id,buyer_id,status,created_at)
                VALUES (%s,%s,'matched',NOW())
            """, (m["deal_id"], m["buyer_id"]))

        # LEVEL 4 – AI assistant
        insight = analyze_deal({**deal, "id": deal_id})

        cur.execute("""
            INSERT INTO deal_ai_insights
            (deal_id,summary,recommendation,tags,buyer_message,seller_message,confidence,created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,NOW())
            ON CONFLICT (deal_id) DO UPDATE SET
            summary=EXCLUDED.summary,
            recommendation=EXCLUDED.recommendation,
            tags=EXCLUDED.tags,
            buyer_message=EXCLUDED.buyer_message,
            seller_message=EXCLUDED.seller_message,
            confidence=EXCLUDED.confidence,
            created_at=NOW()
        """, (
            deal_id, insight["summary"], insight["recommendation"], insight["tags"],
            insight["buyer_message"], insight["seller_message"], insight["confidence"]
        ))

        conn.commit()

        # LEVEL 5 – notify buyers
        try:
            notify_buyers_for_deal(deal_id)
        except Exception as e:
            logger.warning(f"Notify failed: {e}")

        return {"status": "ok", "deal_id": deal_id, "matches": len(matches)}

    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}

    finally:
        cur.close()
        conn.close()


# ======================
# BUYER REGISTRATION
# ======================

@app.post("/buyers/register")
def register_buyer(buyer: BuyerRegister):

    conn = db()
    cur = conn.cursor()

    stripe_customer_id = None

    if STRIPE_SECRET_KEY:
        try:
            customer = stripe.Customer.create(
                email=buyer.email,
                name=buyer.name
            )
            stripe_customer_id = customer["id"]
        except:
            pass

    cur.execute("""
        INSERT INTO buyers
        (name,email,location,asset_types,min_budget,max_budget,active,created_at,role,stripe_customer_id,phone)
        VALUES (%s,%s,%s,%s,%s,%s,true,NOW(),'buyer_free',%s,%s)
    """, (
        buyer.name, buyer.email, buyer.location, buyer.asset_types,
        buyer.min_budget, buyer.max_budget, stripe_customer_id, buyer.phone
    ))

    conn.commit()
    cur.close()
    conn.close()

    return {"status": "ok"}


# ======================
# STRIPE CHECKOUT
# ======================

@app.post("/stripe/create-checkout")
def create_checkout(price_id: str, customer_email: str):

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="subscription",
        customer_email=customer_email,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url="https://yourdomain.com/success",
        cancel_url="https://yourdomain.com/cancel"
    )

    return {"checkout_url": session.url}


# ======================
# STRIPE WEBHOOK
# ======================

@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):

    payload = await request.body()
    sig = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig, STRIPE_WEBHOOK_SECRET
        )
    except Exception:
        return {"status": "invalid"}

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        customer_email = session.get("customer_email")
        price_id = session["metadata"].get("price_id") if session.get("metadata") else None

        role = price_to_role(price_id)

        conn = db()
        cur = conn.cursor()

        cur.execute("""
            UPDATE buyers SET role=%s WHERE email=%s
        """, (role, customer_email))

        conn.commit()
        cur.close()
        conn.close()

    return {"status": "ok"}


# ======================
# ADMIN
# ======================

@app.get("/admin")
def admin():
    return {"status": "admin ok"}
