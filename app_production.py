from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from dotenv import load_dotenv
import json
from datetime import datetime
from pydantic import BaseModel

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

app = FastAPI(title="VortexAI", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "postgresql://postgres.ggjgaftekrafsuixmosd:IVq3iqIEtfnKAtGy@aws-0-us-west-2.pooler.supabase.com:5432/postgres"
logger.info(f"Using DATABASE_URL: {DATABASE_URL[:50]}...")

def get_db_connection():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL not set")
    return psycopg2.connect(DATABASE_URL)

# ==================== MODELS ====================

class DealData(BaseModel):
    name: str
    email: str
    asset_type: str
    location: str
    price: float
    description: str = ""

class BuyerRegister(BaseModel):
    name: str
    email: str
    location: str = ""
    asset_types: str = "real_estate"  # comma-separated
    min_budget: float = 0
    max_budget: float = 1000000

# ==================== HEALTH ====================

@app.get("/")
def root():
    return {"system": "VortexAI", "status": "operational", "version": "3.0.0"}

@app.get("/health")
def health():
    """Health check with database status"""
    if not DATABASE_URL:
        return {"status": "operational", "service": "VortexAI", "version": "3.0.0", "db": "not_configured"}
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM deals")
        deals_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM buyers WHERE active = true")
        buyers_count = cur.fetchone()[0]
        cur.close()
        conn.close()
        
        return {
            "status": "operational",
            "service": "VortexAI",
            "version": "3.0.0",
            "deals_count": deals_count,
            "buyers_count": buyers_count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {"status": "operational", "service": "VortexAI", "version": "3.0.0", "db": "error", "error": str(e)}

# ==================== PORTALS ====================

@app.get("/seller", response_class=HTMLResponse)
def seller_portal():
    """Seller submission form"""
    return """
    <html>
        <head>
            <title>VortexAI - Seller Portal</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
                h1 { color: #333; }
                form { background: #f5f5f5; padding: 20px; border-radius: 8px; }
                label { display: block; margin: 10px 0 5px 0; font-weight: bold; }
                input, textarea, select { width: 100%; padding: 8px; margin-bottom: 15px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
                button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; width: 100%; }
                button:hover { background: #0056b3; }
                .success { color: green; display: none; }
            </style>
        </head>
        <body>
            <h1>🏠 Seller Portal</h1>
            <p>Submit your property for deals</p>
            <form id="sellerForm">
                <label>Name/Contact:</label>
                <input type="text" name="name" required>
                
                <label>Email:</label>
                <input type="email" name="email" required>
                
                <label>Asset Type:</label>
                <select name="asset_type">
                    <option>real_estate</option>
                    <option>car</option>
                    <option>equipment</option>
                    <option>luxury</option>
                </select>
                
                <label>Location:</label>
                <input type="text" name="location" placeholder="City, State" required>
                
                <label>Price:</label>
                <input type="number" name="price" step="1000" required>
                
                <label>Description:</label>
                <textarea name="description" rows="4"></textarea>
                
                <button type="submit">Submit Property</button>
                <p class="success" id="success">✅ Property submitted! Our system will match you with buyers.</p>
            </form>
            <script>
                document.getElementById('sellerForm').onsubmit = async (e) => {
                    e.preventDefault();
                    const data = new FormData(e.target);
                    const payload = Object.fromEntries(data);
                    payload.price = parseFloat(payload.price);
                    
                    const res = await fetch('/admin/webhooks/deal-ingest', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    
                    document.getElementById('success').style.display = 'block';
                    e.target.reset();
                };
            </script>
        </body>
    </html>
    """

@app.get("/buyer", response_class=HTMLResponse)
def buyer_portal():
    """Buyer deal browsing portal"""
    return """
    <html>
        <head>
            <title>VortexAI - Buyer Portal</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 900px; margin: 50px auto; padding: 20px; }
                h1 { color: #333; }
                .filter-box { background: #f5f5f5; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
                .filter-box input, .filter-box select { padding: 8px; margin-right: 10px; border-radius: 4px; border: 1px solid #ddd; }
                .deals-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
                .deal-card { 
                    border-radius: 8px; 
                    padding: 20px; 
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    border-left: 5px solid;
                }
                .deal-card.green { border-left-color: #28a745; background: #f0fff4; }
                .deal-card.yellow { border-left-color: #ffc107; background: #fffef0; }
                .deal-card.red { border-left-color: #dc3545; background: #ffe6e6; }
                .deal-card h3 { margin-top: 0; }
                .score { font-weight: bold; font-size: 18px; }
                .price { color: #007bff; font-size: 20px; font-weight: bold; }
                button { background: #007bff; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; }
                button:hover { background: #0056b3; }
                .loading { text-align: center; color: #666; }
            </style>
        </head>
        <body>
            <h1>💰 Buyer Portal</h1>
            <div class="filter-box">
                <input type="text" id="location" placeholder="Location (City, State)">
                <select id="assetType">
                    <option value="">All Asset Types</option>
                    <option value="real_estate">Real Estate</option>
                    <option value="car">Car</option>
                    <option value="equipment">Equipment</option>
                    <option value="luxury">Luxury</option>
                </select>
                <button onclick="loadDeals()">🔍 Search</button>
            </div>
            <div id="deals" class="deals-grid">
                <p class="loading">Loading deals...</p>
            </div>
            <script>
                async function loadDeals() {
                    const res = await fetch('/admin/deals');
                    const data = await res.json();
                    const deals = data.deals || [];
                    
                    const location = document.getElementById('location').value.toLowerCase();
                    const assetType = document.getElementById('assetType').value;
                    
                    const filtered = deals.filter(d => {
                        const locMatch = !location || (d.location || '').toLowerCase().includes(location);
                        const typeMatch = !assetType || d.asset_type === assetType;
                        return locMatch && typeMatch;
                    });
                    
                    const html = filtered.map(d => {
                        const score = d.score || 50;
                        const color = score >= 15 ? 'green' : score >= 7 ? 'yellow' : 'red';
                        return `
                            <div class="deal-card ${color}">
                                <h3>${d.asset_type.toUpperCase()} - ${d.location}</h3>
                                <p class="price">$${d.price?.toLocaleString() || 0}</p>
                                <p><strong>Score:</strong> <span class="score">${score}/100</span></p>
                                <p>${(d.description || '').substring(0, 100)}...</p>
                                <p style="color: #666; font-size: 12px;">${new Date(d.created_at).toLocaleString()}</p>
                                <button onclick="contactSeller('${d.email}')">💬 Contact Seller</button>
                            </div>
                        `;
                    }).join('');
                    
                    document.getElementById('deals').innerHTML = html || '<p>No deals found</p>';
                }
                
                function contactSeller(email) {
                    alert('Email: ' + email + '\\n\\nIntegration with email system coming soon!');
                }
                
                loadDeals();
                setInterval(loadDeals, 30000); // Refresh every 30 seconds
            </script>
        </body>
    </html>
    """

# ==================== DEAL INGESTION ====================

@app.post("/admin/webhooks/deal-ingest")
def ingest_deal(data: DealData):
    """Ingest new deals from scrapers"""
    if not DATABASE_URL or not psycopg2:
        return {"status": "error", "message": "Database not configured"}
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Calculate AI score (simple version)
        score = 50
        if data.price < 100000:
            score += 15
        if "urgent" in (data.description or "").lower():
            score += 20
        
        cur.execute("""
            INSERT INTO deals (name, email, asset_type, location, price, description, score, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            data.name,
            data.email,
            data.asset_type,
            data.location,
            data.price,
            data.description,
            score
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Deal ingested: {data.asset_type} in {data.location}")
        return {"status": "ok", "message": "Deal ingested"}
    except Exception as e:
        logger.error(f"Error ingesting deal: {e}")
        return {"status": "error", "message": str(e)}

# ==================== DEAL MANAGEMENT ====================

@app.get("/admin/deals")
def get_deals(limit: int = 100):
    """Get all deals with scoring"""
    if not DATABASE_URL or not psycopg2:
        return {"status": "error", "deals": []}
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, name, email, asset_type, location, price, 
                   description, score, created_at, source,
                   (score >= 15) AS is_green,
                   (score >= 7 AND score < 15) AS is_yellow,
                   (score < 7) AS is_red
            FROM deals 
            ORDER BY score DESC, created_at DESC 
            LIMIT %s
        """, (limit,))
        deals = cur.fetchall()
        cur.close()
        conn.close()
        
        return {"status": "success", "count": len(deals), "deals": deals}
    except Exception as e:
        logger.error(f"Error fetching deals: {e}")
        return {"status": "error", "deals": []}

@app.get("/admin/deals/green")
def get_green_deals():
    """Get excellent deals (score >= 15)"""
    if not DATABASE_URL or not psycopg2:
        return {"status": "error", "deals": []}
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM deals 
            WHERE score >= 15 
            ORDER BY score DESC, created_at DESC
            LIMIT 50
        """)
        deals = cur.fetchall()
        cur.close()
        conn.close()
        return {"status": "success", "count": len(deals), "deals": deals}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"status": "error", "deals": []}

@app.get("/admin/deals/yellow")
def get_yellow_deals():
    """Get good deals (score 7-15)"""
    if not DATABASE_URL or not psycopg2:
        return {"status": "error", "deals": []}
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM deals 
            WHERE score >= 7 AND score < 15 
            ORDER BY score DESC, created_at DESC
            LIMIT 50
        """)
        deals = cur.fetchall()
        cur.close()
        conn.close()
        return {"status": "success", "count": len(deals), "deals": deals}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"status": "error", "deals": []}

# ==================== BUYER MANAGEMENT ====================

@app.post("/buyers/register")
def register_buyer(buyer: BuyerRegister):
    """Register a new buyer"""
    if not DATABASE_URL or not psycopg2:
        return {"status": "error", "message": "Database not configured"}
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO buyers (name, email, location, asset_types, min_budget, max_budget, active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, true, NOW())
        """, (
            buyer.name,
            buyer.email,
            buyer.location,
            buyer.asset_types,
            buyer.min_budget,
            buyer.max_budget
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Buyer registered: {buyer.email}")
        return {"status": "ok", "message": "Buyer registered successfully"}
    except Exception as e:
        logger.error(f"Error registering buyer: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/buyers")
def get_buyers():
    """Get all active buyers"""
    if not DATABASE_URL or not psycopg2:
        return {"status": "error", "buyers": []}
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, name, email, location, asset_types, min_budget, max_budget, created_at
            FROM buyers
            WHERE active = true
            ORDER BY created_at DESC
        """)
        buyers = cur.fetchall()
        cur.close()
        conn.close()
        
        return {"status": "success", "count": len(buyers), "buyers": buyers}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"status": "error", "buyers": []}

# ==================== TRIGGER ENDPOINTS ====================

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

@app.get("/admin/kpis")
def get_kpis():
    """Get KPI metrics"""
    if not DATABASE_URL or not psycopg2:
        return {
            "status": "error",
            "total_deals": 0,
            "deals_today": 0,
            "active_buyers": 0,
            "avg_deal_value": 0
        }
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Total deals
        cur.execute("SELECT COUNT(*) FROM deals")
        total_deals = cur.fetchone()[0]
        
        # Deals today
        cur.execute("SELECT COUNT(*) FROM deals WHERE DATE(created_at) = CURRENT_DATE")
        deals_today = cur.fetchone()[0]
        
        # Active buyers
        cur.execute("SELECT COUNT(*) FROM buyers WHERE active = true")
        active_buyers = cur.fetchone()[0]
        
        # Average deal value
        cur.execute("SELECT AVG(price) FROM deals")
        avg_value = cur.fetchone()[0] or 0
        
        cur.close()
        conn.close()
        
        return {
            "status": "ok",
            "total_deals": total_deals,
            "deals_today": deals_today,
            "active_buyers": active_buyers,
            "avg_deal_value": round(avg_value, 2),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching KPIs: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard():
    """Admin dashboard"""
    return """
    <html>
        <head>
            <title>VortexAI Admin Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f0f0f0; }
                h1 { color: #333; }
                .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }
                .kpi-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
                .kpi-card h3 { margin: 0 0 10px 0; color: #666; font-size: 14px; }
                .kpi-value { font-size: 32px; font-weight: bold; color: #007bff; }
                .tabs { display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 2px solid #ddd; }
                .tab-btn { padding: 10px 20px; background: none; border: none; cursor: pointer; font-size: 16px; color: #666; border-bottom: 3px solid transparent; }
                .tab-btn.active { color: #007bff; border-bottom-color: #007bff; }
                .tab-content { display: none; }
                .tab-content.active { display: block; }
                table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
                table th { background: #f5f5f5; padding: 12px; text-align: left; font-weight: bold; }
                table td { padding: 12px; border-bottom: 1px solid #eee; }
                table tr:hover { background: #f9f9f9; }
                .green { color: #28a745; font-weight: bold; }
                .yellow { color: #ffc107; font-weight: bold; }
                .red { color: #dc3545; font-weight: bold; }
            </style>
        </head>
        <body>
            <h1>🎯 VortexAI Admin Dashboard</h1>
            
            <div class="kpi-grid" id="kpiGrid">
                <div class="kpi-card">
                    <h3>Total Deals</h3>
                    <div class="kpi-value" id="totalDeals">-</div>
                </div>
                <div class="kpi-card">
                    <h3>Deals Today</h3>
                    <div class="kpi-value" id="dealsToday">-</div>
                </div>
                <div class="kpi-card">
                    <h3>Active Buyers</h3>
                    <div class="kpi-value" id="activeBuyers">-</div>
                </div>
                <div class="kpi-card">
                    <h3>Avg Deal Value</h3>
                    <div class="kpi-value" id="avgValue">-</div>
                </div>
            </div>
            
            <div class="tabs">
                <button class="tab-btn active" onclick="switchTab('green')">🟢 Green Deals ($15K+)</button>
                <button class="tab-btn" onclick="switchTab('yellow')">🟡 Yellow Deals ($7.5K-15K)</button>
                <button class="tab-btn" onclick="switchTab('all')">📊 All Deals</button>
            </div>
            
            <div id="green" class="tab-content active">
                <table id="greenTable">
                    <thead>
                        <tr>
                            <th>Location</th>
                            <th>Price</th>
                            <th>Type</th>
                            <th>Score</th>
                            <th>Submitted</th>
                        </tr>
                    </thead>
                    <tbody id="greenBody">
                        <tr><td colspan="5" style="text-align: center; color: #999;">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
            
            <div id="yellow" class="tab-content">
                <table id="yellowTable">
                    <thead>
                        <tr>
                            <th>Location</th>
                            <th>Price</th>
                            <th>Type</th>
                            <th>Score</th>
                            <th>Submitted</th>
                        </tr>
                    </thead>
                    <tbody id="yellowBody">
                        <tr><td colspan="5" style="text-align: center; color: #999;">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
            
            <div id="all" class="tab-content">
                <table id="allTable">
                    <thead>
                        <tr>
                            <th>Location</th>
                            <th>Price</th>
                            <th>Type</th>
                            <th>Score</th>
                            <th>Contact</th>
                            <th>Submitted</th>
                        </tr>
                    </thead>
                    <tbody id="allBody">
                        <tr><td colspan="6" style="text-align: center; color: #999;">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
            
            <script>
                async function loadKPIs() {
                    const res = await fetch('/admin/kpis');
                    const data = await res.json();
                    document.getElementById('totalDeals').textContent = data.total_deals || 0;
                    document.getElementById('dealsToday').textContent = data.deals_today || 0;
                    document.getElementById('activeBuyers').textContent = data.active_buyers || 0;
                    document.getElementById('avgValue').textContent = '$' + (data.avg_deal_value || 0).toLocaleString();
                }
                
                async function loadDeals() {
                    const greenRes = await fetch('/admin/deals/green');
                    const greenData = await greenRes.json();
                    const greenDeals = greenData.deals || [];
                    
                    const yellowRes = await fetch('/admin/deals/yellow');
                    const yellowData = await yellowRes.json();
                    const yellowDeals = yellowData.deals || [];
                    
                    const allRes = await fetch('/admin/deals?limit=200');
                    const allData = await allRes.json();
                    const allDeals = allData.deals || [];
                    
                    // Green deals
                    document.getElementById('greenBody').innerHTML = greenDeals.slice(0, 10).map(d => `
                        <tr>
                            <td><strong>${d.location}</strong></td>
                            <td><strong>$${(d.price || 0).toLocaleString()}</strong></td>
                            <td>${d.asset_type}</td>
                            <td><span class="green">${d.score}/100</span></td>
                            <td>${new Date(d.created_at).toLocaleDateString()}</td>
                        </tr>
                    `).join('') || '<tr><td colspan="5" style="text-align: center; color: #999;">No green deals yet</td></tr>';
                    
                    // Yellow deals
                    document.getElementById('yellowBody').innerHTML = yellowDeals.slice(0, 10).map(d => `
                        <tr>
                            <td><strong>${d.location}</strong></td>
                            <td>$${(d.price || 0).toLocaleString()}</td>
                            <td>${d.asset_type}</td>
                            <td><span class="yellow">${d.score}/100</span></td>
                            <td>${new Date(d.created_at).toLocaleDateString()}</td>
                        </tr>
                    `).join('') || '<tr><td colspan="5" style="text-align: center; color: #999;">No yellow deals yet</td></tr>';
                    
                    // All deals
                    document.getElementById('allBody').innerHTML = allDeals.slice(0, 20).map(d => `
                        <tr>
                            <td><strong>${d.location}</strong></td>
                            <td>$${(d.price || 0).toLocaleString()}</td>
                            <td>${d.asset_type}</td>
                            <td>${d.score}/100</td>
                            <td><a href="mailto:${d.email}">${d.email}</a></td>
                            <td>${new Date(d.created_at).toLocaleDateString()}</td>
                        </tr>
                    `).join('') || '<tr><td colspan="6" style="text-align: center; color: #999;">No deals</td></tr>';
                }
                
                function switchTab(tab) {
                    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
                    document.getElementById(tab).classList.add('active');
                    
                    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                    event.target.classList.add('active');
                }
                
                loadKPIs();
                loadDeals();
                setInterval(() => { loadKPIs(); loadDeals(); }, 30000);
            </script>
        </body>
    </html>
    """
