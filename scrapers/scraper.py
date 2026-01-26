#!/usr/bin/env python3
import os
import time
import random
import requests

API_BASE_URL = os.getenv("API_BASE_URL", "https://real-estate-scraper-production.up.railway.app")

SOURCES = [
    {"id": 1, "name": "Zillow"},
    {"id": 2, "name": "Realtor"},
    {"id": 3, "name": "Redfin"},
    {"id": 4, "name": "Facebook"},
    {"id": 5, "name": "Craigslist"},
]

LOCATIONS = [
    ("Houston", "TX"),
    ("Dallas", "TX"),
    ("Phoenix", "AZ"),
    ("Tampa", "FL"),
    ("Winnipeg", "MB"),
]

def make_deal(source):
    city, state = random.choice(LOCATIONS)
    price = random.randint(60000, 150000)
    arv = int(price * 1.5)

    return {
        "title": f"{source['name']} Deal",
        "price": price,
        "city": city,
        "state": state,
        "address": f"{random.randint(10,999)} Main St",
        "arv": arv,
        "repairs": int(arv * 0.2),
        "source": source["name"],
        "url": f"https://example.com/{int(time.time())}",
        "score": random.randint(60, 90),
    }

def run():
    print("Running scraper...")

    # health check
    r = requests.get(f"{API_BASE_URL}/health")
    print("API health:", r.status_code)

    for source in SOURCES:
        deal = make_deal(source)

        resp = requests.post(
            f"{API_BASE_URL}/admin/webhooks/deal-ingest",
            json=deal,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        print("POST", resp.status_code, deal["title"])

        if resp.status_code != 200 and resp.status_code != 201:
            print(resp.text)

        time.sleep(0.5)

    print("Done.")

if __name__ == "__main__":
    run()
