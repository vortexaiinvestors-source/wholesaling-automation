import os
import requests
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DatabaseConnector:
    """
    Unified connector:
    Scrapers → FastAPI webhook → Postgres → Automation → Buyers
    """

    def __init__(self):
        self.api_base = os.getenv("API_BASE_URL")
        if not self.api_base:
            raise RuntimeError("API_BASE_URL not set. Must point to your Railway FastAPI app.")

        self.ingest_url = f"{self.api_base.rstrip('/')}/admin/webhooks/deal-ingest"

        logger.info(f"DatabaseConnector initialized → {self.ingest_url}")

    def store_property(self, property_data: Dict[str, Any]) -> bool:
        """
        Sends property as a deal to FastAPI backend.
        """

        payload = {
            "name": property_data.get("seller_name", "Scraper Seller"),
            "email": property_data.get("email", ""),
            "asset_type": "real_estate",
            "location": self._build_location(property_data),
            "price": property_data.get("mao") or property_data.get("list_price") or 0,
            "url": property_data.get("source_url"),
            "source": property_data.get("source", "scraper"),
            "ai_score": property_data.get("ai_score", 60),
            "metadata": property_data,
        }

        try:
            r = requests.post(self.ingest_url, json=payload, timeout=20)

            if r.status_code >= 400:
                logger.error(f"❌ Backend ingest failed {r.status_code}: {r.text[:200]}")
                return False

            resp = r.json()
            logger.info(f"✅ Deal sent to backend → id={resp.get('deal_id')} location={payload['location']}")
            return True

        except Exception as e:
            logger.error(f"❌ Error sending deal to backend: {e}")
            return False

    def store_scraped_listing(self, listing_data: dict) -> bool:
        """
        Optional: just logs scraped listing as a low-priority deal
        """
        payload = {
            "name": "Scraped Listing",
            "asset_type": "real_estate",
            "location": listing_data.get("region", ""),
            "price": listing_data.get("price", 0),
            "url": listing_data.get("source_url"),
            "source": listing_data.get("source_name", "scraper"),
            "ai_score": 50,
            "metadata": listing_data,
        }

        try:
            r = requests.post(self.ingest_url, json=payload, timeout=20)
            return r.status_code < 400
        except Exception as e:
            logger.error(f"Error storing listing: {e}")
            return False

    def get_pending_properties(self) -> list:
        """
        No longer needed – backend handles matching.
        """
        return []

    def log_scrape_activity(self, source: str, count: int, status: str = 'success'):
        logger.info(f"Scraper log → source={source} count={count} status={status}")

    def _build_location(self, data: dict) -> str:
        parts = [
            data.get("address"),
            data.get("city"),
            data.get("state"),
            data.get("zip_code")
        ]
        return ", ".join([str(p) for p in parts if p])
