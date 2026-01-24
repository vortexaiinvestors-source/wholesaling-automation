"""
VORTEXAI PRODUCTION BACKEND – FULL AUTOMATION ENGINE (STABLE)
Database: Supabase / Railway Postgres
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import logging
import os
import asyncio

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

# -------------------
# LOGGING
# -------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vortexai")

# -------------------
# DATABASE
# -------------------
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# -------------------
# MODELS
# -------------------

class Deal(Base):
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    email = Column(String(255))
    asset_type = Column(String(50), default="unknown")
    location = Column(String(255), default="")
    price = Column(Integer, default=0)
    url = Column(String(500))
    source = Column(String(100))
    ai_score = Column(Float, default=60.0)
    urgency_level = Column(String(50), default="medium")
    notified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(Text)

class Buyer(Base):
    __tablename__ = "buyers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50), default="")
    city = Column(String(255), default="")
    min_profit = Column(Integer, default=0)
    asset_type = Column(String(50), default="any")
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# -------------------
# FASTAPI
# -------------------

app = FastAPI(title="VortexAI Platform", version="3.3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------
# HELPERS
# -------------------

def is_qualified(deal: Deal, buyer: Buyer) -> bool:
    if deal.notified:
        return False

    if buyer.asset_type != "any" and buyer.asset_type.lower() != (deal.asset_type or "").lower():
        return False

    if buyer.city and buyer.city.lower() not in (deal.location or "").lower():
        return False

    if deal.price < buyer.min_profit:
        return False

    if deal.ai_score < 55:
        return False

    return True

def send_email(buyer: Buyer, deal: Deal):
    logger.info(
        f"📧 EMAIL → {buyer.email} | Deal #{deal.id} | {deal.asset_type} | "
        f"{deal.location} | ${deal.price} | Score {deal.ai_score}"
    )

# -------------------
# API ENDPOINTS
# -------------------

@app.get("/health")
async def health():
    db = SessionLocal()
    try:
        return {
            "status": "ok",
            "deals": db.query(Deal).count(),
            "buyers": db.query(Buyer).count()
        }
    finally:
        db.close()

@app.post("/admin/webhooks/deal-ingest")
async def ingest_deal(data: dict):
    db = SessionLocal()
    try:
        deal = Deal(
            name=data.get("name", "Unknown"),
            email=data.get("email", ""),
            asset_type=data.get("asset_type", "unknown"),
            location=data.get("location", ""),
            price=int(data.get("price", 0)),
            url=data.get("url"),
            source=data.get("source", "manual"),
            ai_score=float(data.get("ai_score", 60)),
            urgency_level=data.get("urgency_level", "high"),
            metadata=str(data.get("metadata")) if data.get("metadata") else None,
        )

        db.add(deal)
        db.commit()
        db.refresh(deal)

        logger.info(f"✅ Deal #{deal.id} ingested | ${deal.price} | score={deal.ai_score}")
        return {"status": "success", "deal_id": deal.id}

    except Exception as e:
        db.rollback()
        logger.error(f"Ingest error: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        db.close()

@app.get("/admin/deals")
async def list_deals(limit: int = 50):
    db = SessionLocal()
    try:
        deals = db.query(Deal).order_by(Deal.id.desc()).limit(limit).all()
        return {"total": len(deals)}
    finally:
        db.close()

# -------------------
# BUYERS API
# -------------------

@app.post("/api/buyers")
async def create_buyer(data: dict):
    db = SessionLocal()
    try:
        buyer = Buyer(
            name=data["name"],
            email=data["email"],
            phone=data.get("phone", ""),
            city=data.get("city", ""),
            min_profit=int(data.get("min_profit", 0)),
            asset_type=data.get("asset_type", "any"),
        )
        db.add(buyer)
        db.commit()
        db.refresh(buyer)
        return {"status": "success", "buyer_id": buyer.id}
    finally:
        db.close()

@app.get("/api/buyers")
async def list_buyers():
    db = SessionLocal()
    try:
        buyers = db.query(Buyer).all()
        return {"total": len(buyers), "buyers": [b.email for b in buyers]}
    finally:
        db.close()

# -------------------
# AUTOMATION ENGINE
# -------------------

async def automation_loop():
    await asyncio.sleep(10)
    while True:
        logger.info("🔁 Automation cycle starting...")

        db = SessionLocal()
        try:
            buyers = db.query(Buyer).all()
            deals = db.query(Deal).filter(Deal.notified == False).all()

            matched = 0
            for deal in deals:
                for buyer in buyers:
                    if is_qualified(deal, buyer):
                        send_email(buyer, deal)
                        deal.notified = True
                        matched += 1
                        break

            db.commit()
            logger.info(f"✅ Automation finished – matched {matched} deals")

        except Exception as e:
            db.rollback()
            logger.error(f"Automation error: {e}")

        finally:
            db.close()

        await asyncio.sleep(900)

@app.on_event("startup")
async def start_scheduler():
    asyncio.create_task(automation_loop())

# -------------------
# RUN (local only)
# -------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
