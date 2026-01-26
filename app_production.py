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
    """Get database connection"""
    if not DATABASE_URL or not psycopg2:
        raise Exception("Database not configured")
    return psycopg2.connect(DATABASE_URL)

class DealCreate(BaseModel):
    name: str
    email: str
    asset_type: str
    location: str
    price: float
    description: str = ""

class BuyerRegister(BaseModel):
    name: str
    email: str
    location: str
    asset_types: list
    min_budget: int
    max_budget: int

@app.get("/health")
def health():
    """Health check endpoint"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM deals")
        deals_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM buyers")
        buyers_count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return {
            "status": "healthy",
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

def portals():
    """Combined buyer/seller/admin portal"""
    try:
        with open('frontend_portals.html', 'r') as f:
            return f.read()
    except:
        return """<html><body><h1>Portal not found</h1></body></html>"""

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
                <input type="text" name="location" required>
                
                <label>Price:</label>
                <input type="number" name="price" required>
                
                <label>Description:</label>
                <textarea name="description" rows="4"></textarea>
                
                <button type="submit">Submit Deal</button>
                <div class="success" id="success">Deal submitted!</div>
            </form>
            <script>
                document.getElementById('sellerForm').onsubmit = async (e) => {
                    e.preventDefault();
                    const formData = new FormData(e.target);
                    const data = Object.fromEntries(formData);
                    const res = await fetch('/admin/webhooks/deal-ingest', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                    if (res.ok) {
                        document.getElementById('success').style.display = 'block';
                        e.target.reset();
                    }
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
                body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
                h1 { color: #333; }
                .filter-box { background: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; display: flex; gap: 10px; flex-wrap: wrap; }
                input, select { padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
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
                            <h3>${d.name || 'Deal'}</h3>
                            <div class="score">Score: ${score}/100</div>
                            <p><strong>${d.asset_type || 'Unknown'}</strong> - ${d.location || 'N/A'}</p>
                            <div class="price">$${d.price ? parseInt(d.price).toLocaleString() : 'N/A'}</div>
                            <p>${d.description || ''}</p>
                            <p><small>Contact: ${d.email || 'N/A'}</small></p>
                            <button onclick="alert('Contact seller at ' + '${d.email}')">💬 Contact Seller</button>
                        </div>
                        `;
                    }).join('');
                    
                    document.getElementById('deals').innerHTML = html || '<p class="loading">No deals match your filters</p>';
                }
                loadDeals();
            </script>
        </body>
    </html>
    """

# ==================== ADMIN WEBHOOKS ====================

@app.post("/admin/webhooks/deal-ingest")
def ingest_deal(data: DealCreate):
    """Ingest a deal from scraper or portal"""
    if not DATABASE_URL or not psycopg2:
        return {"status": "error", "message": "Database not configured"}
    
    try:
        # AI Scoring
        score = 50
        color = "YELLOW"
        assignment_fee = 10000
        
        if HAS_DEAL_SCORER:
            try:
                scorer = DealScorer()
                score_result = scorer.score_deal({
                    "asset_type": data.asset_type,
                    "location": data.location,
                    "price": data.price,
                    "description": data.description
                })
                score = score_result["score"]
                color = score_result["color"]
                assignment_fee = score_result["assignment_fee"]
                logger.info(f"AI Scored: {color} deal with ${assignment_fee:,.0f} fee")
            except Exception as e:
                logger.warning(f"AI scorer failed, using fallback: {e}")
                score = 50
                color = "YELLOW"
                assignment_fee = 10000
        else:
            score = 50
            color = "YELLOW"
            assignment_fee = 10000
        
        conn = get_db_connection()
        cur = conn.cursor()
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

@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard():
    """Real-time admin dashboard with all deals"""
    if not DATABASE_URL or not psycopg2:
        return """<html><body><h1>Database not configured</h1></body></html>"""
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, name, email, asset_type, location, price, 
                   description, score, created_at, source
            FROM deals 
            ORDER BY score DESC, created_at DESC 
            LIMIT 200
        """)
        deals = cur.fetchall()
        cur.close()
        conn.close()
        
        deals_list = [dict(d) for d in deals]
        green = [d for d in deals_list if d.get('score', 0) >= 75]
        yellow = [d for d in deals_list if 50 <= d.get('score', 0) < 75]
        red = [d for d in deals_list if d.get('score', 0) < 50]
        
        total_value = sum(d.get('price', 0) for d in deals_list)
        avg_price = total_value / len(deals_list) if deals_list else 0
        
        green_html = _render_dashboard_deals(green, 'green')
        yellow_html = _render_dashboard_deals(yellow[:12], 'yellow')
        red_html = _render_dashboard_deals(red[:6], 'red')
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>VortexAI Admin Dashboard</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 40px 20px; }}
                .container {{ max-width: 1400px; margin: 0 auto; }}
                h1 {{ color: white; margin-bottom: 30px; font-size: 32px; text-shadow: 0 2px 10px rgba(0,0,0,0.2); }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 40px; }}
                .stat-card {{ background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
                .stat-card h3 {{ color: #667eea; font-size: 14px; text-transform: uppercase; margin-bottom: 10px; }}
                .stat-card .value {{ font-size: 32px; font-weight: bold; color: #333; }}
                .deals-section {{ margin-top: 40px; }}
                .section-title {{ color: white; font-size: 20px; margin-bottom: 20px; }}
                .deals-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; margin-bottom: 40px; }}
                .deal-card {{ background: white; padding: 20px; border-radius: 10px; border-left: 5px solid; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .deal-card.green {{ border-left-color: #10b981; background: #f0fdf4; }}
                .deal-card.yellow {{ border-left-color: #f59e0b; background: #fffbeb; }}
                .deal-card.red {{ border-left-color: #ef4444; background: #fef2f2; }}
                .deal-header {{ display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px; }}
                .deal-name {{ font-weight: 600; color: #333; font-size: 16px; }}
                .ai-score {{ padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 14px; }}
                .ai-score.green {{ background: #d1fae5; color: #065f46; }}
                .ai-score.yellow {{ background: #fef3c7; color: #92400e; }}
                .ai-score.red {{ background: #fee2e2; color: #991b1b; }}
                .deal-details {{ display: grid; gap: 10px; font-size: 14px; color: #666; }}
                .detail {{ display: flex; justify-content: space-between; }}
                .detail-label {{ font-weight: 500; }}
                .detail-value {{ color: #333; }}
                .asset-type {{ display: inline-block; background: #e5e7eb; padding: 4px 8px; border-radius: 4px; font-size: 12px; }}
                .footer {{ color: white; text-align: center; margin-top: 40px; font-size: 12px; opacity: 0.8; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 VortexAI Admin Dashboard</h1>
                <div class="stats-grid">
                    <div class="stat-card"><h3>Total Deals</h3><div class="value">{len(deals_list)}</div></div>
                    <div class="stat-card"><h3>Portfolio Value</h3><div class="value">${total_value:,.0f}</div></div>
                    <div class="stat-card"><h3>Average Deal</h3><div class="value">${avg_price:,.0f}</div></div>
                    <div class="stat-card"><h3>🟢 Green</h3><div class="value" style="color: #10b981;">{len(green)}</div></div>
                    <div class="stat-card"><h3>🟡 Yellow</h3><div class="value" style="color: #f59e0b;">{len(yellow)}</div></div>
                    <div class="stat-card"><h3>🔴 Red</h3><div class="value" style="color: #ef4444;">{len(red)}</div></div>
                </div>
                <div class="deals-section">
                    <div class="section-title">🟢 Excellent Deals ({len(green)})</div>
                    <div class="deals-grid">{green_html}</div>
                </div>
                <div class="deals-section">
                    <div class="section-title">🟡 Good Deals ({len(yellow)})</div>
                    <div class="deals-grid">{yellow_html}</div>
                </div>
                <div class="deals-section">
                    <div class="section-title">🔴 Weak Deals ({len(red)})</div>
                    <div class="deals-grid">{red_html}</div>
                </div>
                <div class="footer">
                    Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} | VortexAI v3.0.0
                </div>
            </div>
        </body>
        </html>
        """
        return html
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return f"""<html><body><h1>Error</h1><p>{e}</p></body></html>"""


def _render_dashboard_deals(deals: list, color: str) -> str:
    """Render deal cards"""
    if not deals:
        return '<div style="color: #999; text-align: center; padding: 40px;">No deals yet</div>'
    
    html = ""
    for deal in deals[:12]:
        asset = deal.get('asset_type', 'unknown').replace('_', ' ').title()
        price = deal.get('price', 0)
        score = deal.get('score', 0)
        created = deal.get('created_at', '')
        try:
            dt = created if isinstance(created, datetime) else datetime.fromisoformat(str(created).replace('Z', '+00:00'))
            time_str = dt.strftime('%m/%d %H:%M')
        except:
            time_str = "N/A"
        
        name = deal.get('name', 'Unknown')
        email = deal.get('email', 'N/A')
        location = deal.get('location', 'N/A')
        html += f'<div class="deal-card {color}"><div class="deal-header"><div class="deal-name">{name}</div><div class="ai-score {color}">⭐ {score}</div></div><div class="deal-details"><div class="detail"><span class="detail-label">Asset:</span><span class="detail-value"><span class="asset-type">{asset}</span></span></div><div class="detail"><span class="detail-label">Location:</span><span class="detail-value">{location}</span></div><div class="detail"><span class="detail-label">Price:</span><span class="detail-value"><strong>${price:,.0f}</strong></span></div><div class="detail"><span class="detail-label">Ingested:</span><span class="detail-value">{time_str}</span></div><div class="detail"><span class="detail-label">Email:</span><span class="detail-value" style="font-size: 12px;">{email}</span></div></div></div>'
    
    return html

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
        
        return {"status": "ok", "message": "Buyer registered"}
    except Exception as e:
        logger.error(f"Error registering buyer: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
