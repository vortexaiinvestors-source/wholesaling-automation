import os
from supabase import create_client, Client
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DatabaseConnector:
    def __init__(self):
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')
        self.client: Client = create_client(self.url, self.key)
    
    def store_property(self, property_data: dict) -> bool:
        try:
            response = self.client.table('properties').insert({
                'address': property_data.get('address'),
                'city': property_data.get('city'),
                'state': property_data.get('state'),
                'zip_code': property_data.get('zip_code'),
                'list_price': property_data.get('list_price'),
                'estimated_arv': property_data.get('estimated_arv'),
                'estimated_repairs': property_data.get('estimated_repairs'),
                'mao': property_data.get('mao'),
                'source': property_data.get('source'),
                'source_url': property_data.get('source_url'),
                'raw_data': property_data
            }).execute()
            logger.info(f"Property stored: {property_data.get('address')}")
            return True
        except Exception as e:
            logger.error(f"Error storing property: {e}")
            return False
    
    def store_scraped_listing(self, listing_data: dict) -> bool:
        try:
            self.client.table('scraped_listings').insert({
                'source_name': listing_data.get('source_name'),
                'source_url': listing_data.get('source_url'),
                'region': listing_data.get('region'),
                'raw_data': listing_data,
                'processed': False
            }).execute()
            return True
        except Exception as e:
            logger.error(f"Error storing listing: {e}")
            return False
    
    def get_pending_properties(self) -> list:
        try:
            response = self.client.table('properties').select('*').eq('mao', None).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching pending properties: {e}")
            return []
    
    def log_scrape_activity(self, source: str, count: int, status: str = 'success'):
        try:
            self.client.table('api_logs').insert({
                'endpoint': f'scraper/{source}',
                'status_code': 200 if status == 'success' else 500,
                'response_time_ms': 1000,
                'request_data': {'source': source, 'count': count}
            }).execute()
        except Exception as e:
            logger.error(f"Error logging activity: {e}")