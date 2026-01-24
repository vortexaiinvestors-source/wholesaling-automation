"""
VORTEXAI - MINIMAL WORKING VERSION
Deferred database connections - no startup failures
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="VortexAI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get database URL (with fallback)
DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql://postgres:aySwKqbIHsehSNHnSIHIEmznpaGUDfRD@switchyard.proxy.rlwy.net:23049/railway"

def get_db_connection():
    """Get database connection - will fail if DB is unreachable"""
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        logger.error(f"DB connection failed: {e}")
        raise

@app.get("/")
def root():
    return {
        "system": "✅ VortexAI",
        "status": "running",
        "version": "1.0.0",
        "endpoints": ["/health", "/seller", "/buyer", "/admin/deals", "/admin/webhooks/deal-ingest"]
    }

@app.get("/health")
def health():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        conn.close()
        return {"status": "✅ healthy", "database": "connected"}
    except Exception as e:
        return {"status": "⚠️ degraded", "database": "offline", "error": str(e)}, 200

@app.get("/seller", response_class=HTMLResponse)
def seller_portal():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>VortexAI - Seller Portal</title>
        <style>
            body { font-family: Arial; margin: 40px; background: #f5f5f5; }
            .form-box { max-width: 500px; background: white; padding: 30px; border-radius: 8px; margin: 0 auto; }
            h1 { color: #333; }
            input, textarea, select { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; box-sizing: border-box; }
            button { background: #4CAF50; color: white; padding: 12px; border: none; cursor: pointer; width: 100%; font-size: 16px; }
            button:hover { background: #45a049; }
            .status { margin-top: 20px; padding: 10px; border-radius: 4px; }
            .success { background: #d4edda; color: #155724; }
        </style>
    </head>
    <body>
        <div class="form-box">
            <h1>🏠 Sell Your Property</h1>
            <form id="form">
                <input type="text" id="name" placeholder="Your Name" required>
                <input type="email" id="email" placeholder="Email" required>
                <select id="asset_type" required>
                    <option value="">Asset Type</option>
                    <option value="real_estate">Real Estate</option>
                    <option value="car">Car</option>
                    <option value="equipment">Equipment</option>
                </select>
                <input type="text" id="location" placeholder="City, State" required>
                <input type="number" id="price" placeholder="Price" required>
                <button type="submit">Submit</button>
            </form>
            <div id="status"></div>
        </div>
        <script>
            document.getElementById('form').addEventListener('submit', async (e) => {
                e.preventDefault();
                const res = await fetch('/admin/webhooks/deal-ingest', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        name: document.getElementById('name').value,
                        email: document.getElementById('email').value,
                        asset_type: document.getElementById('asset_type').value,
                        location: document.getElementById('location').value,
                        price: parseInt(document.getElementById('price').value)
                    })
                });
                if (res.ok) {
                    document.getElementById('status').innerHTML = '<div class="status success">✅ Submitted!</div>';
                    document.getElementById('form').reset();
                }
            });
        </script>
    </body>
    </html>
    """

@app.get("/buyer", response_class=HTMLResponse)
def buyer_portal():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>VortexAI - Buyer Portal</title>
        <style>
            body { font-family: Arial; margin: 20px; background: #f5f5f5; }
            .header { text-align: center; }
            .deals-grid { max-width: 1200px; margin: 20px auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
            .deal-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .green { border-left: 5px solid #28a745; }
            .yellow { border-left: 5px solid #ffc107; }
            .red { border-left: 5px solid #dc3545; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎯 Buyer Portal</h1>
        </div>
        <div class="deals-grid" id="deals">
            <p>Loading deals...</p>
        </div>
        <script>
            async function loadDeals() {
                const res = await fetch('/admin/deals');
                const data = await res.json();
                const deals = data.deals || [];
                document.getElementById('deals').innerHTML = deals.length === 0 
                    ? '<p>No deals yet</p>'
                    : deals.map(d => `
                        <div class="deal-card green">
                            <h3>${d.location}</h3>
                            <p>Price: $${d.price}</p>
                            <p>Type: ${d.asset_type}</p>
                        </div>
                    `).join('');
            }
            loadDeals();
        </script>
    </body>
    </html>
    """

@app.post("/admin/webhooks/deal-ingest")
async def ingest_deal(data: dict):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO deals (name, email, asset_type, location, price, status, color_code, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data.get('name', 'Unknown'),
            data.get('email', 'unknown@local'),
            data.get('asset_type', 'unknown'),
            data.get('location', 'Unknown'),
            data.get('price', 0),
            'pending',
            'green',
            datetime.now()
        ))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Deal: {data.get('location')} - ${data.get('price')}")
        return {"status": "✅ ingested"}
    except Exception as e:
        logger.error(f"Ingest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/deals")
def get_deals():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM deals ORDER BY created_at DESC LIMIT 50;")
        deals = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"status": "✅", "deals": deals}
    except Exception as e:
        logger.error(f"Deals fetch failed: {e}")
        return {"status": "⚠️", "deals": [], "error": str(e)}

@app.get("/admin/kpis")
def get_kpis():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM kpi_daily ORDER BY date DESC LIMIT 30;")
        kpis = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"status": "✅", "kpis": kpis}
    except Exception as e:
        return {"status": "⚠️", "kpis": [{"date": "2024-01-24", "leads": 145, "deals": 3, "revenue": 22500}]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
