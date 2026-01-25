from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from dotenv import load_dotenv
import json

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import buyer notifications
try:
    from buyer_notifications import run_buyer_notifications
    HAS_BUYER_NOTIFICATIONS = True
except ImportError:
    HAS_BUYER_NOTIFICATIONS = False
    logger.warning("Buyer notifications module not available")

app = FastAPI(title="VortexAI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL not set")
    return psycopg2.connect(DATABASE_URL)

@app.get("/")
def root():
    return {"system": "VortexAI", "status": "running"}

@app.get("/health")
def health():
    if not DATABASE_URL:
        return {"status": "ok", "db": "not_configured"}
    try:
        conn = get_db_connection()
        conn.close()
        return {"status": "ok", "db": "connected"}
    except:
        return {"status": "ok", "db": "offline"}

@app.get("/seller", response_class=HTMLResponse)
def seller_portal():
    return """
    <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto;">
            <h1>Seller Portal</h1>
            <p>Submit your property for deals</p>
        </body>
    </html>
    """

@app.get("/buyer", response_class=HTMLResponse)
def buyer_portal():
    return """
    <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto;">
            <h1>Buyer Portal</h1>
            <p>Browse and purchase deals</p>
        </body>
    </html>
    """

@app.post("/admin/webhooks/deal-ingest")
def ingest_deal(data: dict):
    """Ingest new deals from scrapers"""
    if not DATABASE_URL or not psycopg2:
        return {"status": "error", "message": "Database not configured"}
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Insert deal into database
        cur.execute("""
            INSERT INTO deals (name, email, asset_type, location, price, description, score, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            data.get('name', 'Unknown'),
            data.get('email', 'unknown@local'),
            data.get('asset_type', 'real_estate'),
            data.get('location', 'Unknown'),
            data.get('price', 0),
            data.get('description', ''),
            data.get('score', 5)
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {"status": "ok", "message": "Deal ingested"}
    except Exception as e:
        logger.error(f"Error ingesting deal: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/admin/deals")
def get_deals():
    """Get all deals"""
    if not DATABASE_URL or not psycopg2:
        return {"status": "error", "deals": []}
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM deals ORDER BY created_at DESC LIMIT 100")
        deals = cur.fetchall()
        cur.close()
        conn.close()
        return {"status": "ok", "count": len(deals), "deals": deals}
    except Exception as e:
        logger.error(f"Error fetching deals: {e}")
        return {"status": "error", "message": str(e), "deals": []}

@app.post("/triggers/send-deals-to-buyers")
def trigger_send_deals_to_buyers():
    """Trigger endpoint for scheduled buyer notifications (fires every 5 min)"""
    if not HAS_BUYER_NOTIFICATIONS:
        return {"status": "error", "message": "Buyer notifications not available"}
    
    try:
        result = run_buyer_notifications()
        return {"status": "ok", **result}
    except Exception as e:
        logger.error(f"Error in buyer notifications: {e}")
        return {"status": "error", "message": str(e)}
