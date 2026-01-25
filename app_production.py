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
                setInterval(loadDeals, 30000);
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

@app.get("/admin/deals/red")
def get_red_deals():
    """Get weak deals (score < 7)"""
    if not DATABASE_URL or not psycopg2:
        return {"status": "error", "deals": []}
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM deals 
            WHERE score < 7 
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
        
        cur.execute("SELECT COUNT(*) FROM deals")
        total_deals = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM deals WHERE DATE(created_at) = CURRENT_DATE")
        deals_today = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM buyers WHERE active = true")
        active_buyers = cur.fetchone()[0]
        
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

@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard():
    """Real-time admin dashboard with deals and KPIs"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>VortexAI Admin Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
                color: #fff;
                padding: 20px;
                min-height: 100vh;
            }
            .container { max-width: 1400px; margin: 0 auto; }
            .header {
                text-align: center;
                margin-bottom: 30px;
                padding: 20px;
                background: rgba(255,255,255,0.05);
                border-radius: 10px;
            }
            .header h1 { font-size: 2.5em; margin-bottom: 10px; }
            .status { font-size: 1.2em; color: #4ade80; }
            .metrics {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 30px;
            }
            .metric-card {
                background: rgba(255,255,255,0.08);
                padding: 20px;
                border-radius: 10px;
                border-left: 4px solid #3b82f6;
            }
            .metric-card.green { border-left-color: #10b981; }
            .metric-card.yellow { border-left-color: #f59e0b; }
            .metric-card.red { border-left-color: #ef4444; }
            .metric-value { font-size: 2em; font-weight: bold; margin: 10px 0; }
            .metric-label { font-size: 0.9em; color: #aaa; }
            .deals-section { margin-top: 30px; }
            .deals-title { font-size: 1.8em; margin-bottom: 20px; }
            .deals-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
                gap: 15px;
            }
            .deal-card {
                background: rgba(255,255,255,0.08);
                padding: 15px;
                border-radius: 8px;
                border-top: 4px solid #3b82f6;
                display: flex;
                flex-direction: column;
            }
            .deal-card.green { border-top-color: #10b981; background: rgba(16,185,129,0.1); }
            .deal-card.yellow { border-top-color: #f59e0b; background: rgba(245,158,11,0.1); }
            .deal-card.red { border-top-color: #ef4444; background: rgba(239,68,68,0.1); }
            .deal-header { display: flex; justify-content: space-between; margin-bottom: 10px; }
            .deal-price { font-size: 1.5em; font-weight: bold; }
            .deal-location { color: #aaa; font-size: 0.9em; }
            .deal-type { display: inline-block; background: rgba(59,130,246,0.3); padding: 4px 8px; border-radius: 4px; font-size: 0.8em; margin-top: 8px; }
            .deal-contact { color: #888; font-size: 0.85em; margin-top: 10px; }
            .loading { text-align: center; padding: 40px; color: #888; }
            .error { color: #ef4444; padding: 20px; background: rgba(239,68,68,0.1); border-radius: 8px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 VortexAI Admin Dashboard</h1>
                <div class="status">Live Deal Tracking & Analytics</div>
            </div>

            <div class="metrics" id="metrics">
                <div class="loading">Loading metrics...</div>
            </div>

            <div class="deals-section">
                <h2 class="deals-title">📊 Active Deals</h2>
                <div class="deals-grid" id="deals">
                    <div class="loading">Loading deals...</div>
                </div>
            </div>
        </div>

        <script>
            async function loadMetrics() {
                try {
                    const [green, yellow, red, kpi] = await Promise.all([
                        fetch('/admin/deals/green').then(r => r.json()).catch(() => ({ deals: [] })),
                        fetch('/admin/deals/yellow').then(r => r.json()).catch(() => ({ deals: [] })),
                        fetch('/admin/deals/red').then(r => r.json()).catch(() => ({ deals: [] })),
                        fetch('/admin/kpis').then(r => r.json()).catch(() => ({}))
                    ]);

                    const totalDeals = (green.deals?.length || 0) + (yellow.deals?.length || 0) + (red.deals?.length || 0);
                    const totalValue = [...(green.deals || []), ...(yellow.deals || []), ...(red.deals || [])]
                        .reduce((sum, d) => sum + (d.price || 0), 0);

                    document.getElementById('metrics').innerHTML = `
                        <div class="metric-card green">
                            <div class="metric-label">🟢 GREEN (Excellent)</div>
                            <div class="metric-value">${green.deals?.length || 0}</div>
                            <div class="metric-label">$${((green.deals || []).reduce((s, d) => s + (d.price || 0), 0) / 1000).toFixed(1)}K</div>
                        </div>
                        <div class="metric-card yellow">
                            <div class="metric-label">🟡 YELLOW (Good)</div>
                            <div class="metric-value">${yellow.deals?.length || 0}</div>
                            <div class="metric-label">$${((yellow.deals || []).reduce((s, d) => s + (d.price || 0), 0) / 1000).toFixed(1)}K</div>
                        </div>
                        <div class="metric-card red">
                            <div class="metric-label">🔴 RED (Weak)</div>
                            <div class="metric-value">${red.deals?.length || 0}</div>
                            <div class="metric-label">$${((red.deals || []).reduce((s, d) => s + (d.price || 0), 0) / 1000).toFixed(1)}K</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">📈 Total Value</div>
                            <div class="metric-value">$${(totalValue / 1000000).toFixed(1)}M</div>
                            <div class="metric-label">${totalDeals} deals</div>
                        </div>
                    `;
                } catch (e) {
                    console.error('Error loading metrics:', e);
                }
            }

            async function loadDeals() {
                try {
                    const [green, yellow, red] = await Promise.all([
                        fetch('/admin/deals/green').then(r => r.json()).catch(() => ({ deals: [] })),
                        fetch('/admin/deals/yellow').then(r => r.json()).catch(() => ({ deals: [] })),
                        fetch('/admin/deals/red').then(r => r.json()).catch(() => ({ deals: [] }))
                    ]);

                    const allDeals = [
                        ...(green.deals || []).map(d => ({ ...d, type: 'green' })),
                        ...(yellow.deals || []).map(d => ({ ...d, type: 'yellow' })),
                        ...(red.deals || []).map(d => ({ ...d, type: 'red' }))
                    ].sort((a, b) => (b.price || 0) - (a.price || 0)).slice(0, 50);

                    if (allDeals.length === 0) {
                        document.getElementById('deals').innerHTML = '<div class="loading">No deals yet. Scrapers running...</div>';
                        return;
                    }

                    document.getElementById('deals').innerHTML = allDeals.map(deal => `
                        <div class="deal-card ${deal.type}">
                            <div class="deal-header">
                                <span>${deal.asset_type || 'Unknown'}</span>
                                <span class="deal-price">$${(deal.price || 0).toLocaleString()}</span>
                            </div>
                            <div class="deal-location">📍 ${deal.location || 'Unknown'}</div>
                            <span class="deal-type">${deal.type.toUpperCase()}</span>
                            <div class="deal-contact">
                                ${deal.name ? '👤 ' + deal.name : ''}
                                ${deal.email ? '<br>📧 ' + deal.email : ''}
                            </div>
                        </div>
                    `).join('');
                } catch (e) {
                    console.error('Error loading deals:', e);
                    document.getElementById('deals').innerHTML = '<div class="error">Error loading deals. Database may be offline.</div>';
                }
            }

            loadMetrics();
            loadDeals();
            setInterval(() => {
                loadMetrics();
                loadDeals();
            }, 10000);
        </script>
    </body>
    </html>
    """
