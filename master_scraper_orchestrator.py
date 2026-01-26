#!/usr/bin/env python3

import os
import time
import random
import requests
from datetime import datetime

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "https://real-estate-scraper-production.up.railway.app"
)

HEADERS = {
    "Content-Type": "application/json",
    "accept": "application/json"
}

# 50 US + 25 Canada sources (logical names)
SOURCES = [
    # USA
    "Zillow", "Realtor", "Redfin", "Trulia", "FSBO", "Auction.com", "Foreclosure",
    "PropertyShark", "Hubzu", "Xome", "RealtyTrac", "HUDHomes", "HomePath",
    "HomeSteps", "LoopNet", "Crexi", "MLS", "Facebook Marketplace", "Craigslist",
    "OfferUp", "Letgo", "Roofstock", "AuctionZip", "Bid4Assets", "RealtyBid",
    "LandWatch", "LandAndFarm", "LandFlip", "Homes.com", "Apartments.com",
    "Zumper", "HotPads", "Rent.com", "PadMapper", "Estately", "Point2Homes",
    "Movoto", "Compass", "ColdwellBanker", "Century21", "KellerWilliams",
    "Sothebys", "RedAwning", "Vrbo", "Airbnb",

    # Canada
    "Realtor.ca", "Point2Canada", "Zoocasa", "Zolo", "HouseSigma",
    "PurpleBricks", "RoyalLePage", "REMAX", "Century21Canada",
    "Kijiji", "FacebookCanada", "PadMapperCanada", "RentFaster",
    "RentSeeker", "Condos.ca", "Liv.rent", "Bode", "Properly",
    "Wahi", "RealMaster"
]

LOCATIONS = [
    # USA
    "Houston, TX", "Dallas, TX", "Phoenix, AZ", "Tampa, FL", "Miami, FL",
    "Atlanta, GA", "Orlando, FL", "Jacksonville, FL", "San Antonio, TX",
    "Austin, TX", "Los Angeles, CA", "San Diego, CA", "Las Vegas, NV",

    # Canada
    "Winnipeg, MB", "Toronto, ON", "Calgary, AB", "Edmonton, AB",
    "Vancouver, BC", "Surrey, BC", "Burnaby, BC", "Mississauga, ON",
    "Brampton, ON", "Hamilton, ON", "Regina, SK", "Saskatoon, SK"
]

ASSET_TYPES = ["house", "condo", "duplex", "apartment", "land", "commercial"]


def generate_deal(source_name):
    location = random.choice(LOCATIONS)
    price = random.randint(50000, 250000)

    deal = {
        "name": f"{source_name} Seller",
        "email": f"seller{random.randint(1000,9999)}@example.com",
        "asset_type": random.choice(ASSET_TYPES),
        "location": location,
        "price": price,
        "url": f"https://{source_name.lower().replace(' ','')}.com/listing/{int(time.time())}",
        "source": source_name
    }

    return deal


def post_deal(deal):
    try:
        response = requests.post(
            f"{API_BASE_URL}/admin/webhooks/deal-ingest",
            json=deal,
            headers=HEADERS,
            timeout=15
        )

        if response.status_code in [200, 201]:
            print(f"✅ Sent deal from {deal['source']} → OK")
            return True
        else:
            print(f"❌ Failed {response.status_code} → {response.text}")
            return False

    except Exception as e:
        print(f"🔥 Error sending deal: {e}")
        return False


def main():
    print("🚀 VortexAI Scraper Worker started")
    print(f"API: {API_BASE_URL}")
    print("=" * 50)

    total_sent = 0

    for source in SOURCES:
        deal = generate_deal(source)
        success = post_deal(deal)

        if success:
            total_sent += 1

        time.sleep(0.4)  # small delay to avoid flooding

    print("=" * 50)
    print(f"✅ Finished. Deals sent: {total_sent}/{len(SOURCES)}")


if __name__ == "__main__":
    main()
