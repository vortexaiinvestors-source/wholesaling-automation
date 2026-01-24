"""
VORTEXAI PRODUCTION BACKEND – FULL AUTOMATION ENGINE (FIXED)
Database: Railway Postgres
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import logging
import os
import asyncio

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# -------------------
# LOGGING
# -------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vortexai")

# -------------------
# DATABASE
# -------------------
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# -------------------
# MODELS
# -------------------

class Deal(Base):
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    email = Column(String(255))
    asset_type = Column(String(50))
    location = Column(String(255))
    price = Column(Integer)
    url = Column(String(500))
    source = Column(String(100))
    ai_score = Column(Float, default=75.0)
    urgency_level = Column(String(50), default="medium")
    notified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(Text)

class Buyer(Base):
    __tablename__ = "buyers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    city = Column(String(255))
    min_profit = Column(Integer, default=15000)
    asset_type = Column(String(50), default="any")
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# -------------------
# FASTAPI
# -------------------

app = FastAPI(title="VortexAI Platform", version="3.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------
# HELPERS
# -------------------

def is_qualified(deal: Deal, buyer: Buyer):
    return (
        buyer.city.lower() in deal.location.lower()
        and deal.price >= buyer.min_profit
        and deal.ai_score >= 55
        and not deal.notified
    )

def send_email(buyer: Buyer, deal: Deal):
    logger.info(
        f"EMAIL → {buyer.email} | Deal #{deal.id} | {deal.asset_type} | "
        f"{deal.location} | ${deal.price} | Score {deal.ai_score}"
    )

# -------------------
# API ENDPOINTS
# -------------------

@app.get("/health")
async def health():
    db = SessionLocal()
    count = db.query(Deal).count()
    db.close()
    return {"status": "ok", "deals": count}

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
            ai_score=data.get("ai_score", 60),
            urgency_level="high"
        )

        db.add(deal)
        db.commit()
        db.refresh(deal)

        logger.info(f"✅ Deal #{deal.id} ingested: {deal.asset_type} | ${deal.price} | Score {deal.ai_score}")

        return {"status": "success", "deal_id": deal.id}

    except Exception as e:
        db.rollback()
        logger.error(f"Ingest error: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        db.close()

@app.get("/admin/deals")
async def list_deals():
    db = SessionLocal()
    total = db.query(Deal).count()
    db.close()
    return {"total": total}

# -------------------
# BUYERS API
# -------------------

@app.post("/api/buyers")
async def create_buyer(data: dict):
    db = SessionLocal()

    buyer = Buyer(
        name=data["name"],
        email=data["email"],
        phone=data.get("phone", ""),
        city=data["city
