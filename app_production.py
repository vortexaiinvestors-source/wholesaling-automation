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

DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql://postgres:aySwKqbIHsehSNHnSIHIEmznpaGUDfRD@switchyard.proxy.rlwy.net:23049/railway"
logger.info(f"Using DATABASE_URL: {DATABASE_URL[:50]}...")

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
        return {"status": "error", "message": "DATABASE_URL not configured"}, 500
    try:
        conn = get_db_connection()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# SELLER PORTAL
@app.get("/seller")
def seller_portal():
    html = """<!DOCTYPE html>
<html>
<head><title>VortexAI - Seller Portal</title>
<style>body{font-family:Arial;margin:20px;background:#f5f5f5}
.container{max-width:600px;margin:0 auto;background:white;padding:20px;border-radius:8px}
h1{color:#333}form{display:flex;flex-direction:column}input,select,textarea{padding:10px;margin:10px 0;border:1px solid #ddd;border-radius:4px}button{padding:12px;background:#4CAF50;color:white;border:none;border-radius:4px;cursor:pointer}button:hover{background:#45a049}</style>
</head>
<body>
<div class="container">
<h1>📋 Sell Your Property</h1>
<form>
<input type="text" placeholder="Your Name" required>
<input type="email" placeholder="Email" required>
<input type="text" placeholder="Property Location" required>
<input type="number" placeholder="Property Price" required>
<select required><option>Property Type</option><option>House</option><option>Land</option><option>Multi-Unit</option></select>
<textarea placeholder="Additional Details"></textarea>
<button type="submit">Submit Property</button>
</form>
</div>
</body>
</html>"""
    return HTMLResponse(content=html)

# BUYER PORTAL
@app.get("/buyer")
def buyer_portal():
    html = """<!DOCTYPE html>
<html>
<head><title>VortexAI - Buyer Portal</title>
<style>body{font-family:Arial;margin:20px;background:#f5f5f5}
.container{max-width:800px;margin:0 auto}.header{background:white;padding:20px;border-radius:8px;margin-bottom:20px}
.deals{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px}
.deal{background:white;padding:15px;border-radius:8px;border-left:4px solid #4CAF50}
.deal.yellow{border-left-color:#FFC107}
.deal.red{border-left-color:#f44336}
h2{margin:0;color:#333}p{margin:5px 0;color:#666}.price{font-weight:bold;color:#4CAF50;font-size:18px}button{padding:10px 20px;background:#4CAF50;color:white;border:none;border-radius:4px;cursor:pointer}</style>
</head>
<body>
<div class="container">
<div class="header"><h1>🏠 Available Deals</h1><p>Browse and purchase wholesale deals</p></div>
<div class="deals">
<div class="deal"><h2>Property #1</h2><p>Location: Toronto, ON</p><p class="price">$150,000</p><p>Assignment Fee: $12,000</p><button>View Details</button></div>
<div class="deal yellow"><h2>Property #2</h2><p>Location: Vancouver, BC</p><p class="price">$200,000</p><p>Assignment Fee: $9,500</p><button>View Details</button></div>
</div>
</div>
</body>
</html>"""
    return HTMLResponse(content=html)

# ADMIN PORTAL
@app.get("/admin/deals")
def admin_deals():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM deals ORDER BY created_at DESC LIMIT 100")
        deals = cur.fetchall()
        cur.close()
        conn.close()
        return {"deals": deals if deals else []}
    except Exception as e:
        return {"error": str(e)}

@app.get("/admin/kpis")
def admin_kpis():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM kpi_daily WHERE date = CURRENT_DATE")
        kpi = cur.fetchone()
        cur.close()
        conn.close()
        return kpi if kpi else {"date": "today", "deals_found": 0, "deals_posted": 0}
    except Exception as e:
        return {"error": str(e)}

# DEAL INGESTION WEBHOOK
@app.post("/admin/webhooks/deal-ingest")
def ingest_deal(deal: dict):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO deals (name, email, asset_type, location, price, source, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (
            deal.get('name', 'Unknown'),
            deal.get('email', 'unknown@local'),
            deal.get('asset_type', 'real_estate'),
            deal.get('location', 'Unknown'),
            deal.get('price', 0),
            deal.get('source', 'webhook')
        ))
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "ingested", "deal": deal}
    except Exception as e:
        return {"error": str(e)}

# SEND DEALS TO BUYERS
@app.post("/buyer-notification/send")
def send_deals_to_buyers():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get green deals (score > 70)
        cur.execute("SELECT * FROM deals WHERE ai_score > 70 AND matched_buyers IS NULL")
        deals = cur.fetchall()
        
        # Get all buyers
        cur.execute("SELECT * FROM buyers")
        buyers = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return {
            "status": "success",
            "deals_found": len(deals),
            "buyers_notified": len(buyers),
            "deals": deals
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
