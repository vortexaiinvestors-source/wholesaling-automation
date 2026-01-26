"""
VortexAI Master Scraper Worker
- Reads sources.json
- Collects deals (demo + real-ready)
- Sends to FastAPI ingest endpoint
"""

import json
import requests
import random
import time
import os
from datetime import datetime

API_ENDPOINT = os.getenv("DEAL_INGEST_URL", "http://localhost:8080/admin/webhooks/deal-ingest")
SOURCES_FILE = "sources.json"

HEADERS = {"Content-Type": "application/json"}

def load_sources():
    with open(SOURCES_FILE, "r") as f:
        return json.load(f)

def generate_demo_deal(source):
    prices = [15000, 22000, 48000, 7500, 120000]
    cities = ["Dallas, TX", "Miami, FL", "Toronto, ON", "Los Angeles, CA", "Chicago, IL"]

    return {
        "name": "Auto Scraper",
        "email": "bot@vortexai.com",
        "asset_type": source["category"],
        "location": random.choice(cities),
        "price": random.choice(prices),
        "description": f"Deal found from {source['name']}",
        "url": source["url"],
        "source": source["name"],
        "metadata": {
            "scraped_at": datetime.utcnow().isoformat()
        }
    }

def post_deal(deal):
    r = requests.post(API_ENDPOINT, json=deal, headers=HEADERS, timeout=15)
    return r.status_code == 200

def run():
    print("🚀 VortexAI Master Worker started")

    sources = load_sources()
    total = 0

    for src in sources:
        try:
            deal = generate_demo_deal(src)

            if post_deal(deal):
                print(f"✅ Posted deal from {src['name']}")
                total += 1
            else:
                print(f"❌ Failed posting {src['name']}")

            time.sleep(1)

        except Exception as e:
            print(f"⚠️ Error {src['name']} -> {e}")

    print(f"🎯 Completed run: {total} deals sent")

if __name__ == "__main__":
    run()
