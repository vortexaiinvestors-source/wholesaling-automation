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

# Import AI deal scorer
try:
    from ai_deal_scorer import DealScorer
    HAS_DEAL_SCORER = True
except ImportError:
    HAS_DEAL_SCORER = False
    logger.warning("AI deal scorer not available")

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
    name: str = "Unknown"
    email: str = "unknown@local"
    asset_type: str = "real_estate"
    location: str
    price: float
    description: str = None
    source: str = "manual"

class SellerData(BaseModel):
    name: str
    email: str
    phone: str = ""
    property_address: str
    property_price: float
    condition: str = "needs_work"
    description: str = ""

class BuyerProfile(BaseModel):
    name: str
    email: str
    phone: str = ""
    asset_type: str
    min_budget: float
    max_budget: float
    location: str
    investment_type: str

# ==================== HEALTH CHECK ====================

@app.get("/health")
def health_check():
    """Health check endpoint"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.warning(f"Database check failed: {e}")
        return {"status": "degraded", "database": "disconnected"}

# ==================== ADMIN WEBHOOKS ====================

@app.post("/admin/webhooks/deal-ingest")
def ingest_deal(data: DealData):
    """Ingest new deals from scrapers with AI scoring"""
    if not DATABASE_URL or not psycopg2:
        return {"status": "error", "message": "Database not configured"}
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Use AI scorer if available, otherwise use fallback
        if HAS_DEAL_SCORER:
            try:
                scorer = DealScorer(DATABASE_URL)
                score_result = scorer.score_deal({
                    "price": data.price,
                    "location": data.location,
                    "description": data.description,
                    "asset_type": data.asset_type
                })
                score = score_result["score"]
                color = score_result["color"]
                assignment_fee = score_result["assignment_fee"]
                logger.info(f"✅ AI Scored: {color} deal with ${assignment_fee:,.0f} fee")
            except Exception as e:
                logger.warning(f"AI scorer failed, using fallback: {e}")
                score = 50
                color = "YELLOW"
                assignment_fee = 10000
        else:
            # Fallback scoring
            score = 50
            color = "YELLOW"
            assignment_fee = 10000
        
        cur.execute("""
            INSERT INTO deals (name, email, asset_type, location, price, description, 
                             score, color, assignment_fee, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            data.name,
            data.email,
            data.asset_type,
            data.location,
            data.price,
            data.description,
            score,
            color,
            assignment_fee
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Deal ingested: {data.asset_type} in {data.location} | {color} | ${assignment_fee:,.0f}")
        return {
            "status": "ok", 
            "message": "Deal ingested",
            "color": color,
            "assignment_fee": assignment_fee,
            "score": score
        }
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
                   description, score, color, assignment_fee, created_at, source
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
def get_green_deals(limit: int = 50):
    """Get GREEN deals (excellent - $15K+ assignment fees)"""
    if not DATABASE_URL:
        return {"deals": []}
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM deals 
            WHERE color = 'GREEN'
            ORDER BY assignment_fee DESC, created_at DESC 
            LIMIT %s
        """, (limit,))
        deals = cur.fetchall()
        cur.close()
        conn.close()
        return {"deals": deals}
    except:
        return {"deals": []}

@app.get("/admin/deals/yellow")
def get_yellow_deals(limit: int = 50):
    """Get YELLOW deals (good - $7.5K-15K fees)"""
    if not DATABASE_URL:
        return {"deals": []}
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM deals 
            WHERE color = 'YELLOW'
            ORDER BY assignment_fee DESC, created_at DESC 
            LIMIT %s
        """, (limit,))
        deals = cur.fetchall()
        cur.close()
        conn.close()
        return {"deals": deals}
    except:
        return {"deals": []}

@app.get("/admin/deals/red")
def get_red_deals(limit: int = 50):
    """Get RED deals (skip - <$7.5K fees)"""
    if not DATABASE_URL:
        return {"deals": []}
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM deals 
            WHERE color = 'RED'
            ORDER BY created_at DESC 
            LIMIT %s
        """, (limit,))
        deals = cur.fetchall()
        cur.close()
        conn.close()
        return {"deals": deals}
    except:
        return {"deals": []}

# ==================== SELLER PORTAL ====================

@app.get("/seller")
def seller_portal():
    """Seller form portal"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>VortexAI - Sell Your Property</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
            .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); padding: 40px; }
            h1 { color: #667eea; margin-bottom: 10px; }
            .subtitle { color: #999; margin-bottom: 30px; font-size: 14px; }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 5px; font-weight: 500; color: #333; }
            input, textarea { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
            textarea { resize: vertical; }
            button { width: 100%; padding: 14px; background: #667eea; color: white; border: none; border-radius: 6px; font-size: 16px; font-weight: 600; cursor: pointer; margin-top: 20px; }
            button:hover { background: #5568d3; }
            .success { color: #27ae60; font-size: 14px; margin-top: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏠 VortexAI</h1>
            <div class="subtitle">Sell Your Property Quickly</div>
            <form onsubmit="submitForm(event)">
                <div class="form-group">
                    <label>Your Name</label>
                    <input type="text" id="name" required>
                </div>
                <div class="form-group">
                    <label>Email</label>
                    <input type="email" id="email" required>
                </div>
                <div class="form-group">
                    <label>Phone</label>
                    <input type="tel" id="phone">
                </div>
                <div class="form-group">
                    <label>Property Address</label>
                    <input type="text" id="address" required>
                </div>
                <div class="form-group">
                    <label>Property Value</label>
                    <input type="number" id="price" required>
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea id="description" rows="4"></textarea>
                </div>
                <button type="submit">Submit Property</button>
                <div class="success" id="message"></div>
            </form>
        </div>
        <script>
            function submitForm(e) {
                e.preventDefault();
                const data = {
                    name: document.getElementById('name').value,
                    email: document.getElementById('email').value,
                    asset_type: 'real_estate',
                    location: document.getElementById('address').value,
                    price: parseFloat(document.getElementById('price').value),
                    description: document.getElementById('description').value
                };
                fetch('/admin/webhooks/deal-ingest', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                }).then(r => r.json()).then(d => {
                    document.getElementById('message').textContent = '✅ Property submitted! We will contact you soon.';
                    document.querySelector('form').reset();
                }).catch(e => {
                    document.getElementById('message').textContent = '❌ Error: ' + e;
                    document.getElementById('message').style.color = 'red';
                });
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)

# ==================== BUYER PORTAL ====================

@app.get("/buyer")
def buyer_portal():
    """Buyer browsing portal"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>VortexAI - Find Investment Deals</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; padding: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            h1 { color: #667eea; margin-bottom: 30px; text-align: center; }
            .filters { background: white; padding: 20px; border-radius: 12px; margin-bottom: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .filter-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }
            select { padding: 10px; border: 1px solid #ddd; border-radius: 6px; }
            .deals-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
            .deal-card { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); transition: transform 0.2s; }
            .deal-card:hover { transform: translateY(-5px); }
            .badge { display: inline-block; padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-bottom: 10px; }
            .badge-green { background: #d4edda; color: #155724; }
            .badge-yellow { background: #fff3cd; color: #856404; }
            .badge-red { background: #f8d7da; color: #721c24; }
            .price { font-size: 24px; font-weight: 700; color: #667eea; margin: 10px 0; }
            .fee { color: #27ae60; font-weight: 600; }
            button { padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; width: 100%; margin-top: 10px; }
            button:hover { background: #5568d3; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>💰 VortexAI - Investment Deals</h1>
            
            <div class="filters">
                <div class="filter-row">
                    <select id="color">
                        <option value="">All Deals</option>
                        <option value="GREEN">🟢 Green Deals</option>
                        <option value="YELLOW">🟡 Yellow Deals</option>
                        <option value="RED">🔴 Red Deals</option>
                    </select>
                    <select id="type">
                        <option value="">All Types</option>
                        <option value="real_estate">Real Estate</option>
                        <option value="car">Cars</option>
                        <option value="equipment">Equipment</option>
                    </select>
                </div>
            </div>
            
            <div class="deals-grid" id="deals"></div>
        </div>
        
        <script>
            function loadDeals() {
                const color = document.getElementById('color').value;
                const url = color ? `/admin/deals/${color.toLowerCase()}` : '/admin/deals';
                
                fetch(url).then(r => r.json()).then(d => {
                    const deals = d.deals || [];
                    const html = deals.map(deal => `
                        <div class="deal-card">
                            <span class="badge badge-${deal.color?.toLowerCase() || 'yellow'}">${deal.color || 'YELLOW'}</span>
                            <h3>${deal.location}</h3>
                            <div class="price">$${deal.price?.toLocaleString()}</div>
                            <div class="fee">💰 Commission: $${deal.assignment_fee?.toLocaleString() || 'TBD'}</div>
                            <p>${deal.description || 'Investment property'}</p>
                            <button onclick="alert('Contact us at info@vortexai.com')">Inquire Now</button>
                        </div>
                    `).join('');
                    document.getElementById('deals').innerHTML = html || '<p>No deals found</p>';
                });
            }
            
            document.getElementById('color').addEventListener('change', loadDeals);
            loadDeals();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)

# ==================== ADMIN DASHBOARD ====================

@app.get("/admin")
def admin_dashboard():
    """Admin dashboard with KPIs and deal management"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>VortexAI Admin Dashboard</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; }
            .dashboard { display: grid; grid-template-columns: 250px 1fr; height: 100vh; }
            .sidebar { background: #1a1a1a; color: white; padding: 20px; overflow-y: auto; }
            .sidebar h2 { margin-bottom: 20px; font-size: 18px; }
            .nav-item { padding: 10px 15px; margin-bottom: 5px; border-radius: 6px; cursor: pointer; }
            .nav-item:hover { background: #333; }
            .nav-item.active { background: #667eea; }
            .main { overflow-y: auto; padding: 30px; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px; margin-bottom: 30px; }
            .stat-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .stat-value { font-size: 28px; font-weight: 700; color: #667eea; }
            .stat-label { color: #999; margin-top: 5px; font-size: 14px; }
            .deals-table { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow-x: auto; }
            table { width: 100%; border-collapse: collapse; }
            thead { background: #f5f5f5; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
            .badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
            .badge-green { background: #d4edda; color: #155724; }
            .badge-yellow { background: #fff3cd; color: #856404; }
            .badge-red { background: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <div class="dashboard">
            <div class="sidebar">
                <h2>🔧 Admin</h2>
                <div class="nav-item active" onclick="switchView('overview')">📊 Overview</div>
                <div class="nav-item" onclick="switchView('green')">🟢 Green Deals</div>
                <div class="nav-item" onclick="switchView('yellow')">🟡 Yellow Deals</div>
                <div class="nav-item" onclick="switchView('red')">🔴 Red Deals</div>
            </div>
            
            <div class="main">
                <div id="overview" class="view">
                    <h1>Dashboard Overview</h1>
                    <div class="stats">
                        <div class="stat-card">
                            <div class="stat-value" id="total-deals">0</div>
                            <div class="stat-label">Total Deals</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value" id="green-count">0</div>
                            <div class="stat-label">Green Deals</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value" id="total-fees">$0</div>
                            <div class="stat-label">Total Commissions</div>
                        </div>
                    </div>
                    <div class="deals-table">
                        <h3 style="margin-bottom: 15px;">Recent Deals</h3>
                        <table id="deals-table">
                            <thead>
                                <tr>
                                    <th>Location</th>
                                    <th>Price</th>
                                    <th>Commission</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody></tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            async function switchView(view) {
                document.querySelectorAll('.nav-item').forEach(e => e.classList.remove('active'));
                event.target.classList.add('active');
                loadDeals(view);
            }
            
            async function loadDashboard() {
                const allRes = await fetch('/admin/deals?limit=200').then(r => r.json()).catch(() => ({ deals: [] }));
                const greenRes = await fetch('/admin/deals/green').then(r => r.json()).catch(() => ({ deals: [] }));
                
                const deals = allRes.deals || [];
                const greenDeals = greenRes.deals || [];
                const totalFees = deals.reduce((sum, d) => sum + (d.assignment_fee || 0), 0);
                
                document.getElementById('total-deals').textContent = deals.length;
                document.getElementById('green-count').textContent = greenDeals.length;
                document.getElementById('total-fees').textContent = '$' + totalFees.toLocaleString();
                
                const tbody = document.querySelector('#deals-table tbody');
                tbody.innerHTML = deals.slice(0, 10).map(d => `
                    <tr>
                        <td>${d.location}</td>
                        <td>$${d.price?.toLocaleString()}</td>
                        <td>$${d.assignment_fee?.toLocaleString() || '0'}</td>
                        <td><span class="badge badge-${d.color?.toLowerCase() || 'yellow'}">${d.color || 'YELLOW'}</span></td>
                    </tr>
                `).join('');
            }
            
            async function loadDeals(color) {
                const url = color && color !== 'overview' ? `/admin/deals/${color}` : '/admin/deals';
                const data = await fetch(url).then(r => r.json()).catch(() => ({ deals: [] }));
                const deals = data.deals || [];
                
                const tbody = document.querySelector('#deals-table tbody');
                tbody.innerHTML = deals.map(d => `
                    <tr>
                        <td>${d.location}</td>
                        <td>$${d.price?.toLocaleString()}</td>
                        <td>$${d.assignment_fee?.toLocaleString() || '0'}</td>
                        <td><span class="badge badge-${d.color?.toLowerCase() || 'yellow'}">${d.color || 'YELLOW'}</span></td>
                    </tr>
                `).join('');
            }
            
            loadDashboard();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)

# ==================== STARTUP ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
