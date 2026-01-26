from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from dotenv import load_dotenv
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor

from services.scoring import score_deal
from services.matching import match_buyers

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app_production")

app = FastAPI(title="VortexAI", version="3.2.0")

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
# DEAL INGEST (LEVEL 2 + 3)
# =======================

@app.post("/admin/webhooks/deal-ingest")
def ingest_deal(data: DealData):
    try:
        deal_data = data.dict()

        # -------- Level 2: AI Scoring --------
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
            deal_data["email"],
            deal_data["asset_type"],
            deal_data["location"],
            deal_data["price"],
            deal_data["description"],
            deal_data["profit_score"],
            deal_data["urgency_score"],
            deal_data["risk_score"],
            deal_data["ai_score"],
            deal_data.get("url"),
            deal_data.get("source"),
            json_dump(deal_data.get("metadata"))
        ))

        deal_id = cur.fetchone()[0]

        # -------- Level 3: Buyer Matching --------
        cur.execute("SELECT * FROM buyers WHERE active=true")
        buyers = cur.fetchall()

        matches = match_buyers({"id": deal_id, **deal_data}, buyers)

        for m in matches:
            cur.execute("""
                INSERT INTO deal_matches (deal_id, buyer_id, status, created_at)
                VALUES (%s,%s,'matched',NOW())
            """, (m["deal_id"], m["buyer_id"]))

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"✅ Deal #{deal_id} scored={deal_data['ai_score']} matched={len(matches)}")

        return {
            "status": "ok",
            "deal_id": deal_id,
            "ai_score": deal_data["ai_score"],
            "matches": len(matches)
        }

    except Exception as e:
        logger.error(f"❌ ingest failed: {e}")
        return {"status": "error", "message": str(e)}

def json_dump(obj):
    if obj is None:
        return None
    import json
    return json.dumps(obj)

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
# BUYERS
# =======================

@app.post("/buyers/register")
def register_buyer(buyer: BuyerRegister):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO buyers
        (name,email,location,asset_types,min_budget,max_budget,active,created_at)
        VALUES (%s,%s,%s,%s,%s,%s,true,NOW())
    """, (
        buyer.name,
        buyer.email,
        buyer.location,
        buyer.asset_types,
        buyer.min_budget,
        buyer.max_budget
    ))

    conn.commit()
    cur.close()
    conn.close()

    return {"status": "ok"}

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
    return "<h2>VortexAI running</h2><p>Use /admin/deals</p>"
