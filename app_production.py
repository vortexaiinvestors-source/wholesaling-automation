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
    <!DOCTYPE html>
    <html>
    <head>
        <title>VortexAI - Seller Portal</title>
        <style>
            body { font-family: Arial; max-width: 800px; margin: 50px auto; }
            .form-group { margin: 15px 0; }
            input, select { padding: 10px; width: 100%; box-sizing: border-box; }
            button { padding: 12px 30px; background: #007bff; color: white; border: none; cursor: pointer; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h1>🏠 Seller Portal</h1>
        <form id="sellerForm">
            <div class="form-group">
                <label>Name:</label>
                <input type="text" id="name" required>
            </div>
            <div class="form-group">
                <label>Email:</label>
                <input type="email" id="email" required>
            </div>
            <div class="form-group">
                <label>Asset Type:</label>
                <select id="asset_type" required>
                    <option>real_estate</option>
                    <option>car</option>
                    <option>equipment</option>
                    <option>luxury</option>
                </select>
            </div>
            <div class="form-group">
                <label>Location:</label>
                <input type="text" id="location" required>
            </div>
            <div class="form-group">
                <label>Price ($):</label>
                <input type="number" id="price" required>
            </div>
            <button type="submit">Submit Property</button>
        </form>
        <p id="message"></p>
        <script>
            document.getElementById('sellerForm').onsubmit = async (e) => {
                e.preventDefault();
                const data = {
                    name: document.getElementById('name').value,
                    email: document.getElementById('email').value,
                    asset_type: document.getElementById('asset_type').value,
                    location: document.getElementById('location').value,
                    price: parseFloat(document.getElementById('price').value)
                };
                try {
                    const response = await fetch('/admin/webhooks/deal-ingest', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(data)
                    });
                    document.getElementById('message').textContent = '✅ Property submitted!';
                } catch (err) {
                    document.getElementById('message').textContent = '❌ Error: ' + err.message;
                }
            };
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
            body { font-family: Arial; max-width: 1000px; margin: 20px auto; }
            .filters { margin: 20px 0; padding: 15px; background: #f5f5f5; border-radius: 5px; }
            .deal { margin: 15px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
            .deal.green { border-left: 5px solid green; background: #f0fff0; }
            .deal.yellow { border-left: 5px solid orange; background: #fffaf0; }
            .deal.red { border-left: 5px solid red; background: #fff5f5; }
            input, select { padding: 8px; margin-right: 10px; }
            button { padding: 10px 20px; background: #28a745; color: white; border: none; cursor: pointer; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h1>🛍️ Buyer Portal</h1>
        <div class="filters">
            <input type="text" id="location" placeholder="Location">
            <select id="asset_type">
                <option>all</option>
                <option>real_estate</option>
                <option>car</option>
                <option>equipment</option>
                <option>luxury</option>
            </select>
            <button onclick="loadDeals()">Search Deals</button>
        </div>
        <div id="deals"></div>
        <script>
            async function loadDeals() {
                try {
                    const response = await fetch('/admin/deals');
                    const deals = await response.json();
                    const dealsDiv = document.getElementById('deals');
                    dealsDiv.innerHTML = '';
                    deals.forEach(deal => {
                        const color = deal.fee >= 15000 ? 'green' : deal.fee >= 7500 ? 'yellow' : 'red';
                        dealsDiv.innerHTML += `
                            <div class="deal ${color}">
                                <h3>${deal.location}</h3>
                                <p><strong>Type:</strong> ${deal.asset_type}</p>
                                <p><strong>Price:</strong> $${deal.price}</p>
                                <p><strong>Assignment Fee:</strong> $${deal.fee}</p>
                                <button onclick="purchaseDeal(${deal.id})">Purchase</button>
                            </div>
                        `;
                    });
                } catch (err) {
                    document.getElementById('deals').innerHTML = '❌ Error loading deals';
                }
            }
            function purchaseDeal(id) {
                alert('Deal ' + id + ' purchased! (demo)');
            }
            loadDeals();
        </script>
    </body>
    </html>
    """

@app.post("/admin/webhooks/deal-ingest")
async def deal_ingest(data: dict):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO leads (name, email, asset_type, location, price, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (data.get('name', 'Unknown'), data.get('email', 'unknown@local'), 
               data.get('asset_type', 'real_estate'), data.get('location', 'Unknown'),
               data.get('price', 0), 'new'))
        
        lead_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Lead ingested: {lead_id}")
        return {"status": "success", "lead_id": lead_id}
    except Exception as e:
        logger.error(f"Error ingesting lead: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/admin/deals")
async def get_deals():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(RealDictCursor)
        
        cursor.execute("""
            SELECT id, name, email, asset_type, location, price,
            CASE
                WHEN price < 100000 THEN 7500
                ELSE 15000
            END as fee
            FROM leads
            ORDER BY created_at DESC
            LIMIT 50
        """)
        
        deals = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [dict(d) for d in deals] if deals else []
    except Exception as e:
        logger.error(f"Error fetching deals: {e}")
        return []

@app.get("/admin/kpis")
async def get_kpis():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM leads")
        total_leads = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM leads WHERE created_at >= NOW() - INTERVAL '1 day'")
        leads_today = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(price) FROM leads WHERE created_at >= NOW() - INTERVAL '1 day'")
        volume_today = cursor.fetchone()[0] or 0
        
        cursor.close()
        conn.close()
        
        return {
            "total_leads": total_leads,
            "leads_today": leads_today,
            "volume_today": float(volume_today),
            "avg_deal_value": float(volume_today / leads_today) if leads_today > 0 else 0
        }
    except Exception as e:
        logger.error(f"Error fetching KPIs: {e}")
        return {
            "total_leads": 0,
            "leads_today": 0,
            "volume_today": 0,
            "avg_deal_value": 0
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
