#!/usr/bin/env python3
import os
import time
import random
import requests

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "https://real-estate-scraper-production.up.railway.app"
)

SOURCES = [
    {"id": 1, "name": "Zillow"},
    {"id": 2, "name": "Realtor"},
    {"id": 3, "name": "Redfin"},
    {"id": 4, "name": "Facebook Marketplace"},
    {"id": 5, "name": "Craigslist"},
]

LOCATIONS = [
    "Houston, TX",
    "Dallas, TX",
    "Phoenix, AZ",
    "Tampa, FL",
    "Winnipeg, MB",
    "Toronto, ON"
]

ASSET_TYPES = ["real_estate"]

def make_deal(source):
    return {
        "name": f"{source['name']} Seller",
        "email": f"lead{random.randint(1000,9999)}@example.com",
        "asset_type": random.choice(ASSET_TYPES),
        "location": random.choice(LOCATIONS),
        "price": random.randint(60000, 180000),
        "url": f"https://example.com/listing/{int(time.time())}",
        "source": source["name"]
    }

def run():
    print("🚀 Running scraper...")

    # Health check
    r = requests.get(f"{API_BASE_URL}/health", timeout=5)
    print("API health:", r.status_code)

    for source in SOURCES:
        deal = make_deal(source)

        resp = requests.post(
            f"{API_BASE_URL}/admin/webhooks/deal-ingest",
            json=deal,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        print("POST", resp.status_code, deal["name"], "from", source["name"])

        if resp.status_code not in (200, 201):
            print("Error:", resp.text)

        time.sleep(0.5)

    print("✅ Done. Scraper finished.")

if __name__ == "__main__":
    run()
