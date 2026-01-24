     1→"""
PRODUCTION REAL ESTATE WHOLESALING SYSTEM
Complete API with dashboard, buyer portal, seller form
Tracks deals with color-coded profit tiers: 🟢 GREEN 🟡 YELLOW 🔴 RED
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json
import logging
from datetime import datetime
from typing import Optional, List
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
import asyncio

load_dotenv()

# === LOGGING ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === FASTAPI APP ===
app = FastAPI(
    title="VortexAI Real Estate System",
    description="24/7 Property Wholesaling with AI Deal Analysis",
    version="1.0.0"
)

# === CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === DATABASE CONNECTION ===
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DATABASE_URL = "postgresql://postgres:aySwKqbIHsehSNHnSIHIEmznpaGUDfRD@switchyard.proxy.rlwy.net:23049/railway"
    logger.warning("DATABASE_URL not set, using Railway Postgres fallback")

logger.info(f"Using DATABASE_URL: {DATABASE_URL[:50]}...")

# === HEALTH CHECK ===
@app.get("/health")
def health_check():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        conn.close()
        return {"status": "✅ healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "⚠️ degraded", "database": "offline", "error": str(e)}

# === SELLER PORTAL ===
@app.get("/seller", response_class=HTMLResponse)
def seller_portal():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>VortexAI - Seller Portal</title>
        <style>
            body { font-family: Arial; margin: 40px; background: #f5f5f5; }
            .form-box { max-width: 500px; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; }
            input, textarea, select { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; }
            button { background: #4CAF50; color: white; padding: 12px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
            button:hover { background: #45a049; }
            .status { margin-top: 20px; padding: 10px; border-radius: 4px; }
            .success { background: #d4edda; color: #155724; }
            .error { background: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <div class="form-box">
            <h1>🏠 Seller Submission</h1>
            <form id="sellerForm">
                <input type="text" id="name" placeholder="Your Name" required>
                <input type="email" id="email" placeholder="Your Email" required>
                <select id="assetType" required>
                    <option value="">Select Asset Type</option>
                    <option value="real_estate">Real Estate</option>
                    <option value="car">Car</option>
                    <option value="equipment">Equipment</option>
                    <option value="luxury">Luxury Item</option>
                    <option value="wholesale">Wholesale Product</option>
                </select>
                <input type="text" id="location" placeholder="City, State" required>
                <input type="number" id="price" placeholder="Asking Price" required>
                <textarea id="description" placeholder="Property Description" rows="5"></textarea>
                <button type="submit">Submit Property</button>
            </form>
            <div id="status"></div>
        </div>
        <script>
            document.getElementById('sellerForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const statusDiv = document.getElementById('status');
                try {
                    const response = await fetch('/admin/webhooks/deal-ingest', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            name: document.getElementById('name').value,
                            email: document.getElementById('email').value,
                            asset_type: document.getElementById('assetType').value,
                            location: document.getElementById('location').value,
                            price: parseInt(document.getElementById('price').value)
                        })
                    });
                    if (response.ok) {
                        statusDiv.innerHTML = '<div class="status success">✅ Property submitted successfully!</div>';
                        document.getElementById('sellerForm').reset();
                    } else {
                        statusDiv.innerHTML = '<div class="status error">❌ Failed to submit. Try again.</div>';
                    }
                } catch (error) {
                    statusDiv.innerHTML = '<div class="status error">❌ Error: ' + error.message + '</div>';
                }
            });
        </script>
    </body>
    </html>
    """

# === BUYER PORTAL ===
@app.get("/buyer", response_class=HTMLResponse)
def buyer_portal():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>VortexAI - Buyer Portal</title>
        <style>
            body { font-family: Arial; margin: 0; padding: 20px; background: #f5f5f5; }
            .header { text-align: center; color: #333; margin-bottom: 30px; }
            .filters { max-width: 1200px; margin: 0 auto 20px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .filters input, .filters select { padding: 10px; margin-right: 10px; border: 1px solid #ddd; border-radius: 4px; }
            .deals-grid { max-width: 1200px; margin: 0 auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
            .deal-card { padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); cursor: pointer; transition: transform 0.2s; }
            .deal-card:hover { transform: translateY(-5px); }
            .green { background: #d4edda; border-left: 5px solid #28a745; }
            .yellow { background: #fff3cd; border-left: 5px solid #ffc107; }
            .red { background: #f8d7da; border-left: 5px solid #dc3545; }
            .deal-title { font-weight: bold; font-size: 18px; margin-bottom: 10px; }
            .deal-details { font-size: 14px; color: #555; }
            .deal-fee { font-weight: bold; font-size: 16px; margin-top: 10px; }
            .loading { text-align: center; color: #666; padding: 40px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎯 VortexAI Buyer Portal</h1>
            <p>Browse exclusive wholesale deals</p>
        </div>
        <div class="filters">
            <input type="text" id="location" placeholder="Filter by location">
            <select id="assetType">
                <option value="">All Asset Types</option>
                <option value="real_estate">Real Estate</option>
                <option value="car">Car</option>
                <option value="equipment">Equipment</option>
                <option value="luxury">Luxury Item</option>
                <option value="wholesale">Wholesale Product</option>
            </select>
            <button onclick="loadDeals()">Search</button>
        </div>
        <div class="deals-grid" id="dealsContainer">
            <div class="loading">Loading deals...</div>
        </div>
        <script>
            async function loadDeals() {
                try {
                    const response = await fetch('/admin/deals');
                    const data = await response.json();
                    const container = document.getElementById('dealsContainer');
                    if (!data.deals || data.deals.length === 0) {
                        container.innerHTML = '<div class="loading">No deals available yet</div>';
                        return;
                    }
                    container.innerHTML = data.deals.map(deal => {
                        const color = deal.color_code === 'green' ? 'green' : deal.color_code === 'yellow' ? 'yellow' : 'red';
                        return `
                            <div class="deal-card ${color}">
                                <div class="deal-title">${deal.location}</div>
                                <div class="deal-details">
                                    <p><strong>Asset:</strong> ${deal.asset_type}</p>
                                    <p><strong>Price:</strong> \$${deal.price.toLocaleString()}</p>
                                    <p><strong>Status:</strong> ${deal.status}</p>
                                </div>
                                <div class="deal-fee">Assignment Fee: \$${Math.max(7500, (deal.price * 0.3)).toLocaleString()}</div>
                            </div>
                        `;
                    }).join('');
                } catch (error) {
                    document.getElementById('dealsContainer').innerHTML = '<div class="loading">Error loading deals</div>';
                }
            }
            loadDeals();
        </script>
    </body>
    </html>
    """

# === DEAL INGESTION WEBHOOK ===
@app.post("/admin/webhooks/deal-ingest")
async def ingest_deal(data: dict):
    try:
        conn = psycopg2.connect(DATABASE_URL)
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
        
        logger.info(f"Deal ingested: {data.get('location')} - \${data.get('price')}")
        return {"status": "✅ deal ingested", "location": data.get('location')}
    except Exception as e:
        logger.error(f"Deal ingestion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# === ADMIN DEALS ENDPOINT ===
@app.get("/admin/deals")
def get_deals():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM deals ORDER BY created_at DESC LIMIT 50;")
        deals = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"status": "✅ success", "deals": deals}
    except Exception as e:
        logger.error(f"Failed to fetch deals: {str(e)}")
        return {"status": "⚠️ error", "deals": [], "error": str(e)}

# === ADMIN KPI ENDPOINT ===
@app.get("/admin/kpis")
def get_kpis():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM kpi_daily ORDER BY date DESC LIMIT 30;")
        kpis = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"status": "✅ success", "kpis": kpis}
    except Exception as e:
        logger.error(f"KPI fetch failed: {str(e)}")
        return {"status": "⚠️ using demo data", "kpis": [
            {"date": "2024-01-24", "leads_generated": 145, "deals_closed": 3, "revenue": 22500},
            {"date": "2024-01-23", "leads_generated": 132, "deals_closed": 2, "revenue": 15000}
        ]}

# === ROOT ===
@app.get("/")
def root():
    return {"system": "✅ VortexAI Real Estate System", "status": "running", "endpoints": ["seller", "buyer", "health", "admin/deals", "admin/kpis"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
