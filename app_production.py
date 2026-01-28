#!/usr/bin/env python3
"""
VortexAI Production Backend - MINIMAL WORKING VERSION
Testing baseline deployment without form data issues
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import logging
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, func
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vortexai_minimal")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/vortexai")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ============================================================================
# DATABASE MODELS
# ============================================================================

class Deal(Base):
    __tablename__ = "deals"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String)
    asset_type = Column(String)
    location = Column(String)
    price = Column(Float)
    score = Column(Float, default=0)
    recommendation = Column(String, default="skip")
    created_at = Column(DateTime, default=datetime.now)

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="VortexAI Deal Platform",
    description="AI-powered deal finding and buyer matching",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables created/verified")
except Exception as e:
    logger.error(f"Database error: {e}")

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class DealData(BaseModel):
    name: str
    email: str = "unknown@local"
    asset_type: str
    location: str
    price: float

class DealResponse(BaseModel):
    id: int
    name: str
    email: str
    asset_type: str
    location: str
    price: float
    score: float
    recommendation: str
    created_at: datetime

    class Config:
        from_attributes = True

class SellerIntakeData(BaseModel):
    """Seller intake form - JSON body (no multipart)"""
    name: str
    email: str
    phone: str = ""
    property_address: str = ""
    property_type: str = ""
    asking_price: float = 0
    urgency_level: str = "normal"
    description: str = ""

class BuyerIntakeData(BaseModel):
    """Buyer intake form - JSON body (no multipart)"""
    name: str
    email: str
    phone: str = ""
    buyer_type: str = "investor"  # investor, wholesaler, end_user
    asset_types: str = ""  # comma-separated
    locations: str = ""  # comma-separated
    budget_min: float = 0
    budget_max: float = 0
    description: str = ""

# ============================================================================
# HEALTH & ROOT ENDPOINTS
# ============================================================================

@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return {
            "status": "healthy",
            "service": "VortexAI API",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "VortexAI Deal Platform API",
        "version": "1.0.0",
        "docs": "/docs"
    }

# ============================================================================
# DEAL ENDPOINTS
# ============================================================================

@app.post("/admin/webhooks/deal-ingest")
async def ingest_deal(deal: DealData):
    """Ingest a new deal"""
    try:
        db = SessionLocal()
        new_deal = Deal(
            name=deal.name,
            email=deal.email,
            asset_type=deal.asset_type,
            location=deal.location,
            price=deal.price,
            score=75.0,  # Basic scoring
            recommendation="post"
        )
        db.add(new_deal)
        db.commit()
        db.refresh(new_deal)
        db.close()
        
        return {
            "status": "success",
            "deal_id": new_deal.id,
            "message": "Deal ingested successfully"
        }
    except Exception as e:
        logger.error(f"Ingest error: {e}")
        return {"status": "error", "error": str(e)}, 500

@app.get("/admin/deals")
async def get_deals(skip: int = 0, limit: int = 100):
    """Get all deals"""
    try:
        db = SessionLocal()
        deals = db.query(Deal).offset(skip).limit(limit).all()
        total = db.query(func.count(Deal.id)).scalar()
        db.close()
        
        return {
            "status": "success",
            "total": total,
            "deals": [DealResponse.from_orm(d).__dict__ for d in deals]
        }
    except Exception as e:
        logger.error(f"Fetch error: {e}")
        return {"status": "error", "error": str(e)}, 500

@app.get("/api/buyers")
async def get_buyers():
    """Get buyers list"""
    return {
        "status": "success",
        "buyers": [],
        "message": "Buyer management coming soon"
    }

# ============================================================================
# INTAKE ENDPOINTS - JSON BODIES (NO MULTIPART DEPENDENCY)
# ============================================================================

@app.post("/intake/seller")
async def intake_seller(data: SellerIntakeData):
    """Seller intake endpoint - JSON body submission"""
    try:
        logger.info(f"Seller intake: {data.name} ({data.email})")
        return {
            "status": "success",
            "message": "Thank you for submitting your property!",
            "seller_id": f"seller_{datetime.now().timestamp()}",
            "next_steps": "Our team will contact you within 24 hours"
        }
    except Exception as e:
        logger.error(f"Seller intake error: {e}")
        return {"status": "error", "error": str(e)}

@app.post("/intake/buyer")
async def intake_buyer(data: BuyerIntakeData):
    """Buyer intake endpoint - JSON body submission"""
    try:
        logger.info(f"Buyer intake: {data.name} ({data.email})")
        return {
            "status": "success",
            "message": "Welcome! We'll match you with deals.",
            "buyer_id": f"buyer_{datetime.now().timestamp()}",
            "next_steps": "Check your email for deal recommendations"
        }
    except Exception as e:
        logger.error(f"Buyer intake error: {e}")
        return {"status": "error", "error": str(e)}

# ============================================================================
# COMMISSION ENDPOINTS (PLACEHOLDER)
# ============================================================================

@app.post("/api/commissions")
async def create_commission(data: dict):
    """Create commission record"""
    return {
        "status": "success",
        "message": "Commission tracking available"
    }

@app.post("/api/commissions/track")
async def track_commission(data: dict):
    """Track commission on closed deal"""
    return {
        "status": "success",
        "message": "Commission tracked"
    }

@app.post("/api/commissions/payout")
async def process_payout(data: dict):
    """Process commission payout"""
    return {
        "status": "success",
        "message": "Payout processing available"
    }

@app.get("/api/commissions/history")
async def get_commission_history():
    """Get commission payout history"""
    return {
        "status": "success",
        "payouts": []
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
