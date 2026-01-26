from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from dotenv import load_dotenv
import json
from datetime import datetime
from pydantic import BaseModel

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Urgency keywords that increase deal quality
URGENCY_KEYWORDS = [
    "must sell", "urgent", "asap", "quick sale",
    "moving", "relocating", "divorce", "foreclosure",
    "inherited", "estate sale", "liquidation",
    "going out of business", "closing down"
]

# Location demand scoring (high-demand markets)
HIGH_DEMAND_AREAS = {
    "california": 1.3,
    "texas": 1.25,
    "florida": 1.2,
    "new york": 1.2,
    "arizona": 1.15,
    "georgia": 1.1,
    "north carolina": 1.1,
    "illinois": 1.05,
    "colorado": 1.1,
    "toronto": 1.35,
    "vancouver": 1.3,
    "calgary": 1.15,
    "ottawa": 1.1
}

class DealScorer:
    def __init__(self, db_url: str = None):
        """Initialize scorer with database connection"""
        self.db_url = db_url or os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL not set")
    
    def connect_db(self):
        """Connect to PostgreSQL"""
        try:
            conn = psycopg2.connect(self.db_url)
            return conn
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def score_deal(self, deal: dict) -> dict:
        """
        Score a single deal and assign color-coding
        
        Returns:
        {
            "score": 0-100,
            "color": "GREEN|YELLOW|RED",
            "assignment_fee": estimated_fee,
            "urgency": 0-100,
            "location_demand": 0-100,
            "recommendation": "buy|consider|skip"
        }
        """
        
        # Extract deal fields
        price = deal.get("price", 0)
        location = (deal.get("location") or "").lower()
        description = (deal.get("description") or "").lower()
        asset_type = deal.get("asset_type", "real_estate")
        
        # === 1. CALCULATE ARV (After Repair Value) ===
        # Use 70% rule: Purchase price = ARV × 0.7
        # For real estate, estimate based on location and condition
        if asset_type == "real_estate":
            arv = self._estimate_arv(price, location)
        else:
            arv = price * 1.5  # Conservative for non-real-estate
        
        # === 2. ESTIMATE REPAIR COSTS ===
        # For real estate deals, estimate repairs (0-30% of ARV)
        if asset_type == "real_estate":
            repair_percent = 0.20  # Default 20% repairs
            if "fixer" in description or "needs work" in description:
                repair_percent = 0.30
            elif "move-in" in description or "turnkey" in description:
                repair_percent = 0.10
            repairs = arv * repair_percent
        else:
            repairs = 0
        
        # === 3. CALCULATE MAO (Maximum Allowable Offer) ===
        # MAO = (ARV - Repairs - Holding Costs - Profit Margin) × 0.7
        holding_costs = arv * 0.05  # 5% for holding
        profit_margin = arv * 0.10  # 10% minimum profit
        
        mao = (arv - repairs - holding_costs - profit_margin) * 0.7
        
        # === 4. CALCULATE ASSIGNMENT FEE ===
        # Difference between what wholesaler pays and what buyer pays
        if price > 0:
            discount_percent = ((mao - price) / price) * 100
        else:
            discount_percent = 0
        
        # Assignment fee scales with discount
        if discount_percent > 30:  # Great deal
            assignment_fee = min(price * 0.25, arv * 0.15)  # Up to 25% of purchase price
        elif discount_percent > 20:  # Good deal
            assignment_fee = price * 0.15  # 15% of purchase price
        elif discount_percent > 10:  # Okay deal
            assignment_fee = price * 0.10  # 10% of purchase price
        else:  # Weak deal
            assignment_fee = max(price * 0.05, 2500)  # Minimum $2,500
        
        # === 5. URGENCY SCORE (0-100) ===
        urgency_score = self._calculate_urgency(description)
        
        # === 6. LOCATION DEMAND (0-100) ===
        location_score = self._calculate_location_demand(location)
        
        # === 7. OVERALL DEAL SCORE (0-100) ===
        # Weighted calculation
        discount_score = min(discount_percent * 2, 40)  # Max 40 points
        urgency_component = urgency_score * 0.30  # 30% weight
        location_component = location_score * 0.30  # 30% weight
        
        overall_score = discount_score + (urgency_component) + (location_component)
        overall_score = min(overall_score, 100)
        
        # === 8. COLOR CODING & RECOMMENDATION ===
        if assignment_fee >= 15000:
            color = "GREEN"
            recommendation = "buy_immediately"
        elif assignment_fee >= 7500:
            color = "YELLOW"
            recommendation = "consider"
        else:
            color = "RED"
            recommendation = "skip"
        
        return {
            "score": round(overall_score, 1),
            "color": color,
            "assignment_fee": round(assignment_fee, 0),
            "urgency_score": round(urgency_score, 1),
            "location_demand": round(location_score, 1),
            "arv_estimate": round(arv, 0),
            "repair_estimate": round(repairs, 0),
            "discount_percent": round(discount_percent, 1),
            "recommendation": recommendation,
            "reasoning": self._generate_reasoning(
                color, assignment_fee, urgency_score, 
                location_score, discount_percent
            )
        }
    
    def _estimate_arv(self, purchase_price: float, location: str) -> float:
        """Estimate After-Repair Value based on location and price"""
        
        # Location multipliers
        multiplier = HIGH_DEMAND_AREAS.get(location.split(",")[0].strip().lower(), 1.0)
        
        # ARV typically 50-100% higher than distressed purchase price
        # Conservative estimate: 1.6x purchase price
        base_arv = purchase_price * 1.6
        
        # Adjust for location demand
        adjusted_arv = base_arv * multiplier
        
        return adjusted_arv
    
    def _calculate_urgency(self, description: str) -> float:
        """Calculate urgency score (0-100) based on keywords"""
        
        if not description:
            return 30
        
        urgency_matches = sum(1 for keyword in URGENCY_KEYWORDS if keyword in description)
        
        # 0 matches = 20, each match adds 20 (max 100)
        urgency_score = 20 + (urgency_matches * 20)
        
        return min(urgency_score, 100)
    
    def _calculate_location_demand(self, location: str) -> float:
        """Calculate location demand score (0-100)"""
        
        if not location:
            return 50
        
        location_lower = location.lower()
        
        # Check for high-demand areas
        for area, multiplier in HIGH_DEMAND_AREAS.items():
            if area in location_lower:
                # Convert multiplier to score
                score = (multiplier - 1.0) * 100 + 50
                return min(score, 100)
        
        # Default mid-range demand for unknown areas
        return 50
    
    def _generate_reasoning(self, color: str, fee: float, 
                           urgency: float, location: float, 
                           discount: float) -> str:
        """Generate human-readable reasoning for the score"""
        
        reasons = []
        
        # Assignment fee reasoning
        if fee >= 15000:
            reasons.append(f"Strong assignment fee of ${fee:,.0f}")
        elif fee >= 7500:
            reasons.append(f"Moderate assignment fee of ${fee:,.0f}")
        else:
            reasons.append(f"Low assignment fee of ${fee:,.0f}")
        
        # Urgency
        if urgency > 70:
            reasons.append("High urgency indicators (seller motivated)")
        elif urgency > 40:
            reasons.append("Moderate urgency signals")
        
        # Location
        if location > 70:
            reasons.append("Excellent market demand")
        elif location > 50:
            reasons.append("Good market conditions")
        
        # Discount
        if discount > 30:
            reasons.append(f"Strong {discount:.0f}% discount")
        elif discount > 15:
            reasons.append(f"Moderate {discount:.0f}% discount")
        
        # Color-specific
        if color == "GREEN":
            reasons.append("✅ GREEN DEAL - Buy immediately")
        elif color == "YELLOW":
            reasons.append("🟡 YELLOW DEAL - Consider for secondary buyers")
        else:
            reasons.append("🔴 RED DEAL - Insufficient margin")
        
        return " | ".join(reasons)
