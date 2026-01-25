#!/usr/bin/env python3
"""
VortexAI Master Scraper Orchestrator (WORKING)

Goal:
- Generate deals (from scrapers later)
- Send deals to FastAPI backend using DatabaseConnector
- Confirm ingestion works end-to-end

This version:
✅ Proves end-to-end flow right now (without needing Zillow/Redfin keys)
✅ Creates a few test deals and sends them to your Railway backend
✅ Lets you validate /admin/deals immediately

Later:
You can plug real scrapers into `collect_deals()`.
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

from database_connector import DatabaseConnector

# Load env vars (.env locally; Railway variables in production)
load_dotenv()

# ---------------------------
# LOGGING
# ---------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("master_scraper")

# ---------------------------
# CONFIG
# ---------------------------
REGIONS = {
    "CANADA": ["MB", "ON", "AB", "BC", "SK"],
    "US": ["TX", "FL", "GA", "AZ"]
}

SOURCES = ["zillow", "redfin", "facebook_marketplace", "craigslist"]


def collect_deals() -> List[Dict[str, Any]]:
    """
    TEMP: Create a few test deals.
    Replace this later with real scraper results.
    """
    now = datetime.utcnow().isoformat()
    deals = [
        {
            "seller_name": "Test Seller A",
            "email": "sellerA@test.com",
            "address": "123 Oak St",
            "city": "Winnipeg",
            "state": "MB",
            "zip_code": "R3C 0A1",
            "list_price": 90000,
            "mao": 85000,
            "estimated_arv": 160000,
            "estimated_repairs": 25000,
            "source": "orchestrator-test",
            "source_url": "https://example.com/deal/123-oak",
            "ai_score": 75,
            "timestamp": now,
        },
        {
            "seller_name": "Test Seller B",
            "email": "sellerB@test.com",
            "address": "55 River Rd",
            "city": "Winnipeg",
            "state": "MB",
            "zip_code": "R2C 1B2",
            "list_price": 120000,
            "mao": 100000,
            "estimated_arv": 190000,
            "estimated_repairs": 35000,
            "source": "orchestrator-test",
            "source_url": "https://example.com/deal/55-river",
            "ai_score": 82,
            "timestamp": now,
        },
        {
            "seller_name": "Test Seller C",
            "email": "sellerC@test.com",
            "address": "9 Sunset Blvd",
            "city": "Winnipeg",
            "state": "MB",
            "zip_code": "R2W 2C3",
            "list_price": 65000,
            "mao": 60000,
            "estimated_arv": 130000,
            "estimated_repairs": 30000,
            "source": "orchestrator-test",
            "source_url": "https://example.com/deal/9-sunset",
            "ai_score": 60,
            "timestamp": now,
        },
    ]
    return deals


def run_once() -> None:
    """
    Runs a single cycle:
    1) Collect deals
    2) Send to backend
    """
    logger.info("🚀 Starting orchestrator run...")
    db = DatabaseConnector()

    deals = collect_deals()
    logger.info(f"Collected {len(deals)} deals (test mode)")

    sent = 0
    failed = 0

    for d in deals:
        ok = db.store_property(d)
        if ok:
            sent += 1
        else:
            failed += 1

    logger.info(f"✅ Done. Sent={sent} Failed={failed}")
    logger.info("Now check: /admin/deals on your Railway API.")


if __name__ == "__main__":
    run_once()
