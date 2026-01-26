from services.notifications import notify_buyers_for_deal
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

import psycopg2
from psycopg2.extras import RealDictCursor

# Level 2/3/4 services
from services.scoring import score_deal
from services.matching import match_buyers
from services.ai_assistant import analyze_deal

# Stripe
import stripe

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app_production")

app = FastAPI(title="VortexAI", version="4.0.0")

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

# Stripe env
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Optional: map specific price IDs to roles (recommended)
STRIPE_PRICE_PRO = os.getenv("STRIPE_PRICE_PRO", "")   # -> buyer_paid
STRIPE_PRICE_VIP = os.getenv("STRIPE_PRICE_VIP", "")   # -> enterprise

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

logger.info("Database configured")


def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


# =======================
# MODELS
# =======================

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
    phone: str = ""  # optional for future SMS


# =======================
# HELPERS
# =======================

def json_dump(obj):
    if obj is None:
        return None
    import json
    return json.dumps(obj)

def utc_ts_from_unix(unix_ts: Optional[int]):
    if not unix_ts:
        return None
    return datetime.fromtimestamp(int(unix_ts), tz=timezone.utc)

def plan_to_role_from_price(price_id: str) -> str:
    """
    Map Stripe price -> role.
    Preferred: set STRIPE_PRICE_PRO and STRIPE_PRICE_VIP.
    Fallback: default buyer_paid for any paid subscription.
    """
    if price_id and STRIPE_PRICE_VIP and price_id == STRIPE_PRICE_VIP:
        return "enterprise"
    if price_id and STRIPE_PRICE_PRO and price_id == STRIPE_PRICE_PRO:
        return "buyer_paid"
    # fallback: treat unknown paid plans as buyer_paid
    return "buyer_paid"

def role_is_paid(role: str) -> bool:
    return role in ["buyer_paid", "enterprise", "admin"]


# =======================
# BASIC ENDPOINTS
# =======================

@app.get("/")
def root():
    return {"system": "VortexAI", "status": "operational"}

@app.get("/health")
def health():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM deals")
        deals_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM buyers WHERE active = true")
        buyers_count = cur.fetchone()[0]
        cur.close()
        conn.close()

        return {
            "status": "ok",
            "deals": deals_count,
            "buyers": buyers_count,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# =======================
# DEAL INGEST (LEVEL 2 + 3 + 4)
# =======================

@app.post("/admin/webhooks/deal-ingest")
def ingest_deal(data: DealData):
    conn = None
    cur = None

    try:
        deal_data = data.dict()

        # ---------- LEVEL 2: AI SCORING ----------
        scores = score_deal(deal_data)
        deal_data.update(scores)

        conn = get_db_connection()
        cur = conn.cursor()

        # Insert deal
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
            deal_data.get("profit_score", 0),
            deal_data.get("urgency_score", 0),
            deal_data.get("risk_score", 0),
            deal_data.get("ai_score", 0),
            deal_data.get("url"),
            deal_data.get("source"),
            json_dump(deal_data.get("metadata"))
        ))

        deal_id = cur.fetchone()[0]

        # ---------- LEVEL 3: BUYER MATCHING (PAID ONLY) ----------
        cur_buyers = conn.cursor(cursor_factory=RealDictCursor)
        cur_buyers.execute("SELECT * FROM buyers WHERE active = true")
        buyers = cur_buyers.fetchall()
        cur_buyers.close()

        # Only paid buyers get matches
        paid_buyers = [b for b in buyers if role_is_paid((b.get("role") or "buyer_free"))]

        matches = match_buyers({"id": deal_id, **deal_data}, paid_buyers)

        for m in matches:
            cur.execute("""
                INSERT INTO deal_matches (deal_id, buyer_id, status, created_at)
                VALUES (%s,%s,'matched',NOW())
            """, (m["deal_id"], m["buyer_id"]))

        # ---------- LEVEL 4: AI ASSISTANT (STORE INSIGHT) ----------
        insight = analyze_deal({**deal_data, "id": deal_id})

        # NOTE: requires UNIQUE(deal_id) on deal_ai_insights; if not present, remove ON CONFLICT section.
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

        logger.info(f"✅ Deal #{deal_id} scored={deal_data.get('ai_score')} matched={len(matches)}")

        return {
            "status": "ok",
            "deal_id": deal_id,
            "ai_score": deal_data.get("ai_score", 0),
            "matches": len(matches)
        }

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ ingest failed: {e}")
        return {"status": "error", "message": str(e)}

    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass


# =======================
# DEAL QUERIES
# =======================

@app.get("/admin/deals")
def get_deals(limit: int = 100):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT *
        FROM deals
        ORDER BY created_at DESC
        LIMIT %s
    """, (limit,))

    deals = cur.fetchall()
    cur.close()
    conn.close()

    return {"status": "success", "count": len(deals), "deals": deals}

@app.get("/admin/deals/green")
def get_green_deals():
    return get_by_score(80, 100)

@app.get("/admin/deals/yellow")
def get_yellow_deals():
    return get_by_score(60, 79)

@app.get("/admin/deals/red")
def get_red_deals():
    return get_by_score(0, 59)

def get_by_score(min_s, max_s):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT *
        FROM deals
        WHERE score BETWEEN %s AND %s
        ORDER BY score DESC
        LIMIT 50
    """, (min_s, max_s))

    deals = cur.fetchall()
    cur.close()
    conn.close()

    return {"status": "success", "count": len(deals), "deals": deals}


# =======================
# MATCHES
# =======================

@app.get("/admin/matches")
def admin_matches(limit: int = 100):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT *
        FROM deal_matches
        ORDER BY created_at DESC
        LIMIT %s
    """, (limit,))

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"status": "success", "count": len(rows), "matches": rows}


# =======================
# AI INSIGHTS (LEVEL 4)
# =======================

@app.get("/admin/ai/latest")
def ai_latest(limit: int = 25):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT d.id as deal_id, d.asset_type, d.location, d.price, d.score,
               a.summary, a.recommendation, a.tags, a.confidence, a.created_at
        FROM deal_ai_insights a
        JOIN deals d ON d.id = a.deal_id
        ORDER BY a.created_at DESC
        LIMIT %s
    """, (limit,))

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"status": "success", "count": len(rows), "insights": rows}

@app.get("/admin/ai/deal/{deal_id}")
def ai_for_deal(deal_id: int):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT *
        FROM deal_ai_insights
        WHERE deal_id = %s
        LIMIT 1
    """, (deal_id,))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return {"status": "not_found", "deal_id": deal_id}
    return {"status": "success", "insight": row}


# =======================
# BUYERS
# =======================

@app.post("/buyers/register")
def register_buyer(buyer: BuyerRegister):
    """
    Creates a free buyer by default.
    If STRIPE_SECRET_KEY exists, optionally creates Stripe customer and stores stripe_customer_id.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    stripe_customer_id = None

    # Optional: create Stripe customer at registration time
    if STRIPE_SECRET_KEY:
        try:
            customer = stripe.Customer.create(
                email=buyer.email,
                name=buyer.name,
                metadata={"asset_types": buyer.asset_types}
            )
            stripe_customer_id = customer.get("id")
        except Exception as e:
            logger.warning(f"⚠️ Stripe customer create failed (continuing): {e}")

    cur.execute("""
        INSERT INTO buyers
        (name,email,location,asset_types,min_budget,max_budget,active,created_at,role,stripe_customer_id,phone)
        VALUES (%s,%s,%s,%s,%s,%s,true,NOW(),%s,%s,%s)
    """, (
        buyer.name,
        buyer.email,
        buyer.location,
        buyer.asset_types,
        buyer.min_budget,
        buyer.max_budget,
        "buyer_free",
        stripe_customer_id,
        buyer.phone
    ))

    conn.commit()
    cur.close()
    conn.close()

    return {"status": "ok", "role": "buyer_free"}

@app.get("/buyers")
def get_buyers():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT * FROM buyers WHERE active=true")
    buyers = cur.fetchall()

    cur.close()
    conn.close()

    return {"status": "success", "count": len(buyers), "buyers": buyers}


# =======================
# STRIPE WEBHOOK (MONETIZATION)
# =======================

@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    if not STRIPE_WEBHOOK_SECRET:
        return {"status": "error", "message": "STRIPE_WEBHOOK_SECRET not set"}

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        logger.error(f"❌ Stripe webhook signature verify failed: {e}")
        return {"status": "error", "message": "invalid signature"}

    event_type = event.get("type", "")
    obj = event["data"]["object"]

    # Helper: find buyer by email
    def find_buyer_by_email(email: str):
        if not email:
            return None
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM buyers WHERE email=%s LIMIT 1", (email,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row

    # Helper: upsert subscription record
    def upsert_subscription(buyer_id: int, stripe_customer_id: str, stripe_subscription_id: str,
                            plan_name: str, status: str, current_period_end_unix: Optional[int]):
        cpe = utc_ts_from_unix(current_period_end_unix)
        conn = get_db_connection()
        cur = conn.cursor()

        # update if exists else insert (works even if no unique constraints exist)
        cur.execute("""
            SELECT id FROM stripe_subscriptions
            WHERE stripe_subscription_id = %s
            LIMIT 1
        """, (stripe_subscription_id,))
        existing = cur.fetchone()

        if existing:
            cur.execute("""
                UPDATE stripe_subscriptions
                SET buyer_id=%s,
                    stripe_customer_id=%s,
                    plan_name=%s,
                    status=%s,
                    current_period_end=%s
                WHERE stripe_subscription_id=%s
            """, (buyer_id, stripe_customer_id, plan_name, status, cpe, stripe_subscription_id))
        else:
            cur.execute("""
                INSERT INTO stripe_subscriptions
                (buyer_id, stripe_customer_id, stripe_subscription_id, plan_name, status, current_period_end, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,NOW())
            """, (buyer_id, stripe_customer_id, stripe_subscription_id, plan_name, status, cpe))

        conn.commit()
        cur.close()
        conn.close()

    # Helper: set buyer role
    def set_buyer_role(email: str, role: str, stripe_customer_id: Optional[str] = None):
        conn = get_db_connection()
        cur = conn.cursor()
        if stripe_customer_id:
            cur.execute("""
                UPDATE buyers
                SET role=%s, stripe_customer_id=%s
                WHERE email=%s
            """, (role, stripe_customer_id, email))
        else:
            cur.execute("""
                UPDATE buyers
                SET role=%s
                WHERE email=%s
            """, (role, email))
        conn.commit()
        cur.close()
        conn.close()

    try:
        # 1) Checkout completed (best for “first time purchase”)
        if event_type == "checkout.session.completed":
            email = (obj.get("customer_details") or {}).get("email") or obj.get("customer_email") or ""
            stripe_customer_id = obj.get("customer")
            stripe_subscription_id = obj.get("subscription")  # present if subscription mode

            buyer = find_buyer_by_email(email)
            if not buyer:
                logger.warning(f"⚠️ Stripe checkout completed but buyer not found for email={email}")
                return {"status": "ok", "note": "buyer not found"}

            # Determine role by pulling subscription (to get price id)
            role = "buyer_paid"
            plan_name = "paid"
            status = "active"
            cpe_unix = None

            if stripe_subscription_id and STRIPE_SECRET_KEY:
                sub = stripe.Subscription.retrieve(stripe_subscription_id)
                status = sub.get("status", "active")
                cpe_unix = sub.get("current_period_end")
                # get first price id
                items = ((sub.get("items") or {}).get("data") or [])
                price_id = None
                if items:
                    price_id = ((items[0].get("price") or {}).get("id"))
                role = plan_to_role_from_price(price_id or "")
                plan_name = price_id or "paid"

                upsert_subscription(
                    buyer_id=buyer["id"],
                    stripe_customer_id=stripe_customer_id,
                    stripe_subscription_id=stripe_subscription_id,
                    plan_name=plan_name,
                    status=status,
                    current_period_end_unix=cpe_unix
                )

            set_buyer_role(email=email, role=role, stripe_customer_id=stripe_customer_id)

            logger.info(f"✅ Stripe checkout activated buyer={email} role={role}")
            return {"status": "ok", "event": event_type}

        # 2) Subscription updated/created
        if event_type in ["customer.subscription.created", "customer.subscription.updated"]:
            stripe_subscription_id = obj.get("id")
            stripe_customer_id = obj.get("customer")
            status = obj.get("status", "")
            cpe_unix = obj.get("current_period_end")

            # Get price id
            items = ((obj.get("items") or {}).get("data") or [])
            price_id = None
            if items:
                price_id = ((items[0].get("price") or {}).get("id"))
            plan_name = price_id or "subscription"

            # Get customer email from Stripe
            email = ""
            if STRIPE_SECRET_KEY and stripe_customer_id:
                cust = stripe.Customer.retrieve(stripe_customer_id)
                email = cust.get("email") or ""

            buyer = find_buyer_by_email(email)
            if not buyer:
                logger.warning(f"⚠️ Subscription event but buyer not found for email={email}")
                return {"status": "ok", "note": "buyer not found"}

            # Role logic: active/trialing => paid; otherwise free
            if status in ["active", "trialing"]:
                role = plan_to_role_from_price(price_id or "")
            else:
                role = "buyer_free"

            upsert_subscription(
                buyer_id=buyer["id"],
                stripe_customer_id=stripe_customer_id,
                stripe_subscription_id=stripe_subscription_id,
                plan_name=plan_name,
                status=status,
                current_period_end_unix=cpe_unix
            )

            set_buyer_role(email=email, role=role, stripe_customer_id=stripe_customer_id)

            logger.info(f"✅ Subscription sync buyer={email} status={status} role={role}")
            return {"status": "ok", "event": event_type}

        # 3) Subscription deleted => downgrade
        if event_type == "customer.subscription.deleted":
            stripe_customer_id = obj.get("customer")
            email = ""
            if STRIPE_SECRET_KEY and stripe_customer_id:
                cust = stripe.Customer.retrieve(stripe_customer_id)
                email = cust.get("email") or ""

            if email:
                set_buyer_role(email=email, role="buyer_free", stripe_customer_id=stripe_customer_id)
                logger.info(f"✅ Subscription deleted -> buyer downgraded email={email}")

            return {"status": "ok", "event": event_type}

        # Other events: ignore safely
        return {"status": "ok", "event": event_type}

    except Exception as e:
        logger.error(f"❌ Stripe webhook processing failed: {e}")
        return {"status": "error", "message": str(e)}


# =======================
# KPI
# =======================

@app.get("/admin/kpis")
def get_kpis():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM deals")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM deals WHERE DATE(created_at)=CURRENT_DATE")
    today = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM buyers WHERE active=true")
    buyers = cur.fetchone()[0]

    cur.execute("SELECT AVG(price) FROM deals")
    avg_price = cur.fetchone()[0] or 0

    cur.close()
    conn.close()

    return {
        "total_deals": total,
        "deals_today": today,
        "active_buyers": buyers,
        "avg_price": round(avg_price, 2)
    }


# =======================
# ADMIN UI
# =======================

@app.get("/admin", response_class=HTMLResponse)
def admin_ui():
    return """
    <h2>VortexAI running</h2>
    <ul>
      <li>/admin/deals</li>
      <li>/admin/matches</li>
      <li>/admin/ai/latest</li>
      <li>/admin/kpis</li>
    </ul>
    """
