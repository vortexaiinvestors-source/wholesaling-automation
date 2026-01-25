#!/usr/bin/env python3
import os
import sys
import time
import json
import random
import hashlib
import hmac
import requests
from typing import Dict, Optional

# ============================
# CONFIG
# ============================

API_BASE_URL = os.getenv("API_BASE_URL", "https://real-estate-scraper-production.up.railway.app")
API_INGEST_KEY = os.getenv("API_INGEST_KEY")

# ============================
# SOURCES (USA + CANADA)
# ============================

SOURCES = [
    {"id": 1, "name": "Zillow FSBO", "url": "https://www.zillow.com"},
    {"id": 2, "name": "Realtor.com", "url": "https://www.realtor.com"},
    {"id": 3, "name": "Redfin", "url": "https://www.redfin.com"},
    {"id": 4, "name": "Facebook Marketplace", "url": "https://www.facebook.com/marketplace"},
    {"id": 5, "name": "Craigslist", "url": "https://www.craigslist.org"},
    {"id": 6, "name": "FSBO.com", "url": "https://www.fsbo.com"},
    {"id": 7, "name": "Auction.com", "url": "https://www.auction.com"},
    {"id": 8, "name": "Foreclosure.com", "url": "https://www.foreclosure.com"},
    {"id": 9, "name": "LoopNet", "url": "https://www.loopnet.com"},
    {"id": 10, "name": "Crexi", "url": "https://www.crexi.com"},

    {"id": 51, "name": "Realtor.ca", "url": "https://www.realtor.ca"},
    {"id": 52, "name": "Kijiji Real Estate", "url": "https://www.kijiji.ca"},
    {"id": 53, "name": "Zoocasa", "url": "https://www.zoocasa.com"},
    {"id": 54, "name": "Zolo", "url": "https://www.zolo.ca"},
    {"id": 55, "name": "HouseSigma", "url": "https://housesigma.com"},
]

LOCATIONS = [
    "Houston, TX", "Dallas, TX", "Phoenix, AZ", "Austin, TX",
    "Tampa, FL", "Miami, FL", "Winnipeg, MB", "Toronto, ON", "Calgary, AB"
]

# ============================
# AUTH (optional)
# ============================

class WebhookAuthenticator:
    def __init__(self, key: str):
        self.key = key

    def sign(self, timestamp: int, payload: Dict) -> str:
        msg = f"{timestamp}.{json.dumps(payload, sort_keys=True)}"
        return hmac.new(self.key.encode(), msg.encode(), hashlib.sha256).hexdigest()

    def headers(self, payload: Dict):
        ts = int(time.time() * 1000)
        sig = self.sign(ts, payload)
        return {
            "Content-Type": "application/json",
            "x-ingest-signature": sig,
            "x-ingest-timestamp": str(ts),
            "User-Agent": "VortexAI/3.0"
        }

# ============================
# SCRAPER
# ============================

class Scraper:

    def __init__(self):
        self.session = requests.Session()
        self.auth = WebhookAuthenticator(API_INGEST_KEY) if API_INGEST_KEY else None

    def health_check(self):
        r = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if r.status_code != 200:
            raise Exception("API not healthy")

    def fake_deal(self, source):
        price = random.randint(60000, 180000)
        arv = int(price * random.uniform(1.3, 1.8))
        city_state = random.choice(LOCATIONS)
        city, state = city_state.split(",")

        return {
            "title": f"{source['name']} Deal",
            "price": price,
            "city": city.strip(),
            "state": state.strip(),
            "address": f"{random.randint(10,999)} Main St",
            "arv": arv,
            "repairs": int(arv * 0.2),
            "source": source["name"],
            "url": f"{source['url']}/listing-{int(time.time())}",
            "score": random.randint(65, 90)
        }

    def post(self, payload: Dict):
        headers = self.auth.headers(payload) if self.auth else {"Content-Type": "application/json"}

        r = self.session.post(
            f"{API_BASE_URL}/admin/webhooks/deal-ingest",
            json=payload,
            headers=headers,
            timeout=10
        )

        if r.status_code not in (200, 201):
            print("❌ Failed:", r.status_code, r.text)
            return False

        print("✅ Posted:", payload["title"])
        return True

    def run(self):
        print("🚀 Scraper started")

        self.health_check()

        for source in SOURCES:
            for _ in range(random.randint(1, 2)):
                deal = self.fake_deal(source)
                self.post(deal)
            time.sleep(0.3)

        print("✅ Scraper finished")

# ============================
# MAIN
# ============================

if __name__ == "__main__":
    Scraper().run()
