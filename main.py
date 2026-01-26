from services.notifications import notify_buyers_for_deal
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Optional, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor

from services.scoring import score_deal
from services.matching import match_buyers
from services.ai_assistant import analyze_deal

import stripe

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app_production")

app = FastAPI(title="VortexAI", version="4.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_PRO = os.getenv("STRIPE_PRICE_PRO", "")
STRIPE_PRICE_VIP = os.getenv("STRIPE_PRICE_VIP", "")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


class DealData(BaseModel):
    name: str
    email: str = ""
    asset_type: str
    location: str
    price: float
    description: str = ""
    url: Optional[str] = None
    source: Optional[str] = None
    ai_score: int = 60
    metadata: Optional[Dict[str, Any]] = None


class BuyerRegister(BaseModel):
    name: str
    email: str
    location: str = ""
    asset_types: str = "real_estate"
    min_budget: float = 0
    max_budget: float = 10000000
    phone: str = ""


def json_dump(obj):
    if obj is None:
        return None
    import json
    return json.dumps(obj)


def utc_ts_from_unix(unix_ts):
    if not unix_ts:
        return None
    return datetime.fromtimestamp(int(unix_ts), tz=timezone.utc)


def plan_to_role_from_price(price_id: str) -> str:
    if price_id == STRIPE_PRICE_VIP:
        return "enterprise"
    if price_id == STRIPE_PRICE_PRO:
        return "buyer_paid"
    return "buyer_paid"


def role_is_paid(role: str) -> bool:
    return role in ["buyer_paid", "enterprise", "admin"]


@app.get("/")
def root():
    return {"system": "VortexAI", "status": "operational"}


@app.post("/admin/webhooks/deal-ingest")
def ingest_deal(data: DealData):

    conn = None
    cur = None

    try:
        deal_data = data.dict()

        # LEVEL 2 – AI scoring
        scores = score_deal(deal_data)
        deal_data.update(scores)

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO deals (
                name, email, asset_type, location, price, description,
                profit_score, urgency_score, risk_score, score,
                url, source, metadata, created_at
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
            RETURNING id
        """, (
            deal_data["name"],
            deal_data.get("email", ""),
            deal_data["asset_type"],
            deal_data["location"],
            deal_data["price"],
            deal_data.get("description", ""),
            deal_data["profit_score"],
            deal_data["urgency_score"],
            deal_data["risk_score"],
            deal_data["ai_score"],
            deal_data.get("url"),
            deal_data.get("source"),
            json_dump(deal_data.get("metadata"))
        ))

        deal_id = cur.fetchone()[0]

        # LEVEL 3 – Buyer matching
        cur2 = conn.cursor(cursor_factory=RealDictCursor)
        cur2.execute("SELECT * FROM buyers WHERE active=true")
        buyers = cur2.fetchall()
        cur2.close()

        paid_buyers = [b for b in buyers if role_is_paid(b.get("role", ""))]

        matches = match_buyers({"id": deal_id, **deal_data}, paid_buyers)

        for m in matches:
            cur.execute("""
                INSERT INTO deal_matches (deal_id, buyer_id, status, created_at)
                VALUES (%s,%s,'matched',NOW())
            """, (m["deal_id"], m["buyer_id"]))

        # LEVEL 4 – AI Assistant
        insight = analyze_deal({**deal_data, "id": deal_id})

        cur.execute("""
            INSERT INTO deal_ai_insights
            (deal_id, summary, recommendation, tags, buyer_message, seller_message, confidence, created_at)
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
            deal_id,
            insight["summary"],
            insight["recommendation"],
            insight["tags"],
            insight["buyer_message"],
            insight["seller_message"],
            insight["confidence"]
        ))

        conn.commit()

        # LEVEL 5 – AUTO EMAIL BUYERS ✅
        try:
            notify_buyers_for_deal(deal_id)
        except Exception as e:
            logger.warning(f"Notification failed: {e}")

        logger.info(f"Deal #{deal_id} complete. Matches: {len(matches)}")

        return {
            "status": "ok",
            "deal_id": deal_id,
            "ai_score": deal_data["ai_score"],
            "matches": len(matches)
        }

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Ingest failed: {e}")
        return {"status": "error", "message": str(e)}

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.post("/buyers/register")
def register_buyer(buyer: BuyerRegister):

    conn = get_db_connection()
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
        buyer.name,
        buyer.email,
        buyer.location,
        buyer.asset_types,
        buyer.min_budget,
        buyer.max_budget,
        stripe_customer_id,
        buyer.phone
    ))

    conn.commit()
    cur.close()
    conn.close()

    return {"status": "ok"}


@app.get("/admin")
def admin_ui():
    return {"status": "VortexAI running"}
