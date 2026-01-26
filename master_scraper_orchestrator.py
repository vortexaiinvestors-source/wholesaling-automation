#!/usr/bin/env python3
"""
VortexAI Multi-Asset Bot (WORKING with your API schema)

This bot generates TEST deals across many asset types and POSTs them to:
POST {API_BASE_URL}/admin/webhooks/deal-ingest

API expects EXACT payload:
{
  "name": "string",
  "email": "string",
  "asset_type": "string",
  "location": "string",
  "price": 0,
  "url": "string",
  "source": "string"
}

Later: replace generate_fake_deal() with real scrapers per source.
"""

import os
import time
import random
import hashlib
import logging
from typing import Dict, List, Tuple
import requests

# -----------------------
# ENV / CONFIG
# -----------------------
API_BASE_URL = os.getenv("API_BASE_URL", "https://real-estate-scraper-production.up.railway.app").rstrip("/")
RUN_MODE = os.getenv("RUN_MODE", "once").lower()  # "once" or "loop"
DEALS_PER_SOURCE = int(os.getenv("DEALS_PER_SOURCE", "2"))  # how many deals to create per source per run
SLEEP_BETWEEN_POSTS = float(os.getenv("SLEEP_BETWEEN_POSTS", "0.35"))
SLEEP_BETWEEN_SOURCES = float(os.getenv("SLEEP_BETWEEN_SOURCES", "0.5"))
LOOP_SLEEP_SECONDS = int(os.getenv("LOOP_SLEEP_SECONDS", "900"))  # 15 min default

# Optional: simple duplicate protection (in-memory per run)
ENABLE_DUP_PROTECTION = os.getenv("ENABLE_DUP_PROTECTION", "true").lower() == "true"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("vortex_bot")

# -----------------------
# LOCATIONS (USA + CANADA)
# -----------------------
US_LOCATIONS = [
    "Houston, TX", "Dallas, TX", "Austin, TX", "San Antonio, TX",
    "Phoenix, AZ", "Tampa, FL", "Miami, FL", "Orlando, FL",
    "Atlanta, GA", "Charlotte, NC", "Nashville, TN", "Las Vegas, NV",
    "Los Angeles, CA", "San Diego, CA", "Seattle, WA", "Denver, CO",
    "Chicago, IL", "Columbus, OH", "Detroit, MI", "Philadelphia, PA",
    "New York, NY", "Boston, MA"
]

CA_LOCATIONS = [
    "Winnipeg, MB", "Brandon, MB", "Steinbach, MB",
    "Toronto, ON", "Ottawa, ON", "Hamilton, ON",
    "Calgary, AB", "Edmonton, AB",
    "Vancouver, BC", "Surrey, BC",
    "Regina, SK", "Saskatoon, SK",
    "Montreal, QC", "Quebec City, QC",
    "Halifax, NS"
]

ALL_LOCATIONS = US_LOCATIONS + CA_LOCATIONS

# -----------------------
# SOURCES BY ASSET TYPE
# (These are "source labels" for now; real scraping comes later)
# -----------------------
SOURCES: Dict[str, List[Dict[str, str]]] = {
    # 🏠 Real Estate
    "real_estate": [
        {"name": "zillow", "url": "https://www.zillow.com"},
        {"name": "realtor", "url": "https://www.realtor.com"},
        {"name": "redfin", "url": "https://www.redfin.com"},
        {"name": "craigslist_real_estate", "url": "https://www.craigslist.org"},
        {"name": "facebook_marketplace_real_estate", "url": "https://www.facebook.com/marketplace"},
        {"name": "loopnet", "url": "https://www.loopnet.com"},
        {"name": "crexi", "url": "https://www.crexi.com"},
        {"name": "realtor_ca", "url": "https://www.realtor.ca"},
        {"name": "kijiji_real_estate", "url": "https://www.kijiji.ca"},
        {"name": "zolo", "url": "https://www.zolo.ca"},
    ],

    # 🚗 Cars & Luxury Vehicles
    "cars": [
        {"name": "autotrader", "url": "https://www.autotrader.com"},
        {"name": "cars_com", "url": "https://www.cars.com"},
        {"name": "cargurus", "url": "https://www.cargurus.com"},
        {"name": "facebook_marketplace_cars", "url": "https://www.facebook.com/marketplace"},
        {"name": "craigslist_cars", "url": "https://www.craigslist.org"},
        {"name": "copart", "url": "https://www.copart.com"},
        {"name": "iaai", "url": "https://www.iaai.com"},
        {"name": "autotrader_ca", "url": "https://www.autotrader.ca"},
        {"name": "kijiji_cars", "url": "https://www.kijiji.ca"},
    ],

    # 🚜 Farm & Heavy Equipment
    "farm_equipment": [
        {"name": "machinery_pete", "url": "https://www.machinerypete.com"},
        {"name": "tractorhouse", "url": "https://www.tractorhouse.com"},
        {"name": "fastline", "url": "https://www.fastline.com"},
        {"name": "facebook_marketplace_farm", "url": "https://www.facebook.com/marketplace"},
        {"name": "kijiji_farm", "url": "https://www.kijiji.ca"},
    ],

    # 🏗 Construction Equipment
    "construction_equipment": [
        {"name": "ironplanet", "url": "https://www.ironplanet.com"},
        {"name": "rbauction", "url": "https://www.rbauction.com"},
        {"name": "equipmenttrader", "url": "https://www.equipmenttrader.com"},
        {"name": "machinio", "url": "https://www.machinio.com"},
        {"name": "govplanet", "url": "https://www.govplanet.com"},
    ],

    # 🚛 Commercial Trucks & Trailers
    "trucks": [
        {"name": "commercialtrucktrader", "url": "https://www.commercialtrucktrader.com"},
        {"name": "truckpaper", "url": "https://www.truckpaper.com"},
        {"name": "facebook_marketplace_trucks", "url": "https://www.facebook.com/marketplace"},
        {"name": "craigslist_trucks", "url": "https://www.craigslist.org"},
        {"name": "kijiji_trucks", "url": "https://www.kijiji.ca"},
    ],

    # 🛥 Boats & Marine
    "boats": [
        {"name": "boat_trader", "url": "https://www.boattrader.com"},
        {"name": "yachtworld", "url": "https://www.yachtworld.com"},
        {"name": "facebook_marketplace_boats", "url": "https://www.facebook.com/marketplace"},
        {"name": "craigslist_boats", "url": "https://www.craigslist.org"},
    ],

    # ⌚ Luxury items (Rolex, jewelry, etc.)
    "luxury_items": [
        {"name": "chrono24", "url": "https://www.chrono24.com"},
        {"name": "ebay_luxury", "url": "https://www.ebay.com"},
        {"name": "facebook_marketplace_luxury", "url": "https://www.facebook.com/marketplace"},
        {"name": "kijiji_luxury", "url": "https://www.kijiji.ca"},
        {"name": "grailed", "url": "https://www.grailed.com"},
    ],

    # 📦 Wholesale products / pallets / liquidation
    "wholesale_products": [
        {"name": "liquidation_com", "url": "https://www.liquidation.com"},
        {"name": "bstock", "url": "https://bstock.com"},
        {"name": "directliquidation", "url": "https://www.directliquidation.com"},
        {"name": "bulq", "url": "https://www.bulq.com"},
        {"name": "govdeals", "url": "https://www.govdeals.com"},
    ],

    # 🏢 Business assets / businesses for sale / digital assets
    "business_assets": [
        {"name": "bizbuysell", "url": "https://www.bizbuysell.com"},
        {"name": "businessesforsale", "url": "https://www.businessesforsale.com"},
        {"name": "flippa", "url": "https://flippa.com"},
        {"name": "facebook_marketplace_business", "url": "https://www.facebook.com/marketplace"},
        {"name": "craigslist_business", "url": "https://www.craigslist.org"},
    ],

    # 💎 Collectibles (bonus category)
    "collectibles": [
        {"name": "ebay_collectibles", "url": "https://www.ebay.com"},
        {"name": "facebook_marketplace_collectibles", "url": "https://www.facebook.com/marketplace"},
        {"name": "kijiji_collectibles", "url": "https://www.kijiji.ca"},
    ],
}

# -----------------------
# PRICE RANGES PER ASSET TYPE (helps keep deals "high value")
# -----------------------
PRICE_RANGES: Dict[str, Tuple[int, int]] = {
    "real_estate": (60000, 450000),
    "cars": (7000, 180000),
    "farm_equipment": (15000, 250000),
    "construction_equipment": (20000, 450000),
    "trucks": (15000, 220000),
    "boats": (12000, 650000),
    "luxury_items": (2000, 150000),
    "wholesale_products": (3000, 90000),
    "business_assets": (15000, 2500000),
    "collectibles": (200, 50000),
}

ASSET_TYPES = list(SOURCES.keys())

# -----------------------
# HELPERS
# -----------------------
def stable_hash(asset_type: str, location: str, price: int, url: str, source: str) -> str:
    s = f"{asset_type}|{location}|{price}|{url}|{source}"
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def generate_fake_deal(asset_type: str, source: Dict[str, str]) -> Dict:
    lo, hi = PRICE_RANGES.get(asset_type, (1000, 100000))
    price = random.randint(lo, hi)

    # Biased to Canada sometimes (you asked for mix)
    location = random.choice(ALL_LOCATIONS)

    # Basic "lead identity"
    lead_id = random.randint(1000, 9999)
    name = f"{asset_type.replace('_', ' ').title()} Lead {lead_id}"
    email = f"lead{lead_id}@example.com"

    # Fake url (later becomes real listing url)
    url = f"{source['url'].rstrip('/')}/listing/{asset_type}/{int(time.time())}-{random.randint(100,999)}"

    payload = {
        "name": name,
        "email": email,
        "asset_type": asset_type,     # MUST MATCH API
        "location": location,         # MUST MATCH API
        "price": price,               # MUST MATCH API
        "url": url,                   # MUST MATCH API
        "source": source["name"],     # MUST MATCH API
    }
    return payload

def post_deal(payload: Dict) -> bool:
    try:
        r = requests.post(
            f"{API_BASE_URL}/admin/webhooks/deal-ingest",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15
        )

        if r.status_code in (200, 201):
            # Example response: {"status":"success","deal_id":"deal_13","score":75,...}
            log.info(f"✅ POST {r.status_code} | {payload['asset_type']} | {payload['location']} | ${payload['price']} | {payload['source']}")
            return True

        log.error(f"❌ POST {r.status_code} | {r.text}")
        return False

    except Exception as e:
        log.error(f"🔥 POST error: {e}")
        return False

def health_check() -> bool:
    try:
        r = requests.get(f"{API_BASE_URL}/health", timeout=8)
        ok = r.status_code == 200
        log.info(f"Health check: {r.status_code} ({'OK' if ok else 'BAD'})")
        return ok
    except Exception as e:
        log.error(f"Health check failed: {e}")
        return False

# -----------------------
# MAIN RUN
# -----------------------
def run_once() -> None:
    if not health_check():
        return

    seen = set()
    total_sent = 0
    total_failed = 0

    # Shuffle so each run varies
    asset_types = ASSET_TYPES[:]
    random.shuffle(asset_types)

    for asset_type in asset_types:
        sources = SOURCES.get(asset_type, [])
        if not sources:
            continue

        random.shuffle(sources)

        for src in sources:
            for _ in range(DEALS_PER_SOURCE):
                payload = generate_fake_deal(asset_type, src)

                if ENABLE_DUP_PROTECTION:
                    h = stable_hash(payload["asset_type"], payload["location"], payload["price"], payload["url"], payload["source"])
                    if h in seen:
                        continue
                    seen.add(h)

                ok = post_deal(payload)
                if ok:
                    total_sent += 1
                else:
                    total_failed += 1

                time.sleep(SLEEP_BETWEEN_POSTS)

            time.sleep(SLEEP_BETWEEN_SOURCES)

    log.info(f"✅ Run complete. Sent={total_sent} Failed={total_failed}")

def main():
    log.info("🚀 VortexAI Multi-Asset Bot starting...")
    log.info(f"API_BASE_URL = {API_BASE_URL}")
    log.info(f"RUN_MODE = {RUN_MODE} | DEALS_PER_SOURCE = {DEALS_PER_SOURCE}")

    if RUN_MODE == "loop":
        while True:
            run_once()
            log.info(f"Sleeping {LOOP_SLEEP_SECONDS}s before next run...")
            time.sleep(LOOP_SLEEP_SECONDS)
    else:
        run_once()

if __name__ == "__main__":
    main()
