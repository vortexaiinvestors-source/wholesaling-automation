"""
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
DB_CONFIG = {
    "dbname": os.getenv("DATABASE_NAME", "postgres"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "mUEkDH0Of0E6Is7i"),
    "host": os.getenv("DB_HOST", "db.ggjgaftekrafsuixmosd.supabase.co"),
    "port": os.getenv("DB_PORT", "5432")
}

def get_db_connection():
    """Get PostgreSQL connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        logger.error(f"Database connection failed: {e}")
        return None

def calculate_profit_tier(assignment_fee: float) -> tuple:
    """Calculate profit tier and color code"""
    if assignment_fee >= 15000:
        return "green", "🟢 EXCELLENT"
    elif assignment_fee >= 7500:
        return "yellow", "🟡 GOOD"
    else:
        return "red", "🔴 SKIP THIS"

# === HEALTH CHECK ===
@app.get("/health")
async def health_check():
    """System health status"""
    db = get_db_connection()
    db_status = "✅ LIVE" if db else "❌ OFFLINE"
    if db:
        db.close()
    
    return JSONResponse({
        "status": "✅ RUNNING",
        "timestamp": datetime.now().isoformat(),
        "service": "VortexAI-API",
        "database": db_status,
        "version": "1.0.0"
    })

# === SELLER INTAKE API ===
@app.post("/api/seller/intake")
async def seller_intake(property_data: dict):
    """Seller submits property info"""
    try:
        conn = get_db_connection()
        if not conn:
            return JSONResponse({"error": "Database unavailable"}, status_code=500)
        
        cur = conn.cursor()
        
        # Calculate ARV
        estimated_arv = property_data.get("estimated_repair_cost", 0) + property_data.get("seller_asking_price", 0) * 1.2
        
        # Calculate MAO using 70% rule
        repair_cost = property_data.get("estimated_repair_cost", 0)
        mao = (estimated_arv * 0.70) - repair_cost
        
        # Calculate assignment fee
        assignment_fee = mao - property_data.get("seller_asking_price", 0)
        
        tier, tier_name = calculate_profit_tier(assignment_fee)
        
        # Store in database
        cur.execute("""
            INSERT INTO properties (
                address, city, state, bedrooms, bathrooms, 
                estimated_repair, asking_price, estimated_arv, mao, assignment_fee,
                profit_tier, seller_name, seller_phone, seller_email, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING id
        """, (
            property_data.get("address"),
            property_data.get("city"),
            property_data.get("state"),
            property_data.get("bedrooms", 0),
            property_data.get("bathrooms", 0),
            repair_cost,
            property_data.get("seller_asking_price"),
            estimated_arv,
            mao,
            assignment_fee,
            tier,
            property_data.get("seller_name"),
            property_data.get("seller_phone"),
            property_data.get("seller_email"),
        ))
        
        property_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return JSONResponse({
            "success": True,
            "property_id": property_id,
            "estimated_arv": round(estimated_arv, 2),
            "mao": round(mao, 2),
            "assignment_fee": round(assignment_fee, 2),
            "profit_tier": tier_name,
            "message": f"Property submitted! {tier_name} deal potential"
        })
    
    except Exception as e:
        logger.error(f"Seller intake error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# === BUYER PORTAL API ===
@app.get("/api/deals/available")
async def get_available_deals():
    """Get all available deals for buyers - GREEN and YELLOW only"""
    try:
        conn = get_db_connection()
        if not conn:
            return JSONResponse({"error": "Database unavailable"}, status_code=500)
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get only profitable deals
        cur.execute("""
            SELECT 
                id, address, city, state, bedrooms, bathrooms,
                estimated_repair, asking_price, estimated_arv, mao, assignment_fee,
                profit_tier, created_at
            FROM properties
            WHERE profit_tier IN ('green', 'yellow')
            AND created_at > NOW() - INTERVAL '30 days'
            ORDER BY assignment_fee DESC
        """)
        
        deals = cur.fetchall()
        cur.close()
        conn.close()
        
        formatted_deals = []
        for deal in deals:
            tier_name = "🟢 EXCELLENT" if deal['profit_tier'] == 'green' else "🟡 GOOD"
            formatted_deals.append({
                **dict(deal),
                "profit_tier_display": tier_name,
                "assignment_fee": float(deal['assignment_fee'] or 0),
                "mao": float(deal['mao'] or 0),
                "estimated_arv": float(deal['estimated_arv'] or 0),
            })
        
        return JSONResponse({
            "total_deals": len(formatted_deals),
            "green_count": sum(1 for d in formatted_deals if d['profit_tier'] == 'green'),
            "yellow_count": sum(1 for d in formatted_deals if d['profit_tier'] == 'yellow'),
            "deals": formatted_deals
        })
    
    except Exception as e:
        logger.error(f"Get deals error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/deals/{deal_id}/purchase")
async def purchase_deal(deal_id: int, buyer_data: dict):
    """Buyer purchases a deal"""
    try:
        conn = get_db_connection()
        if not conn:
            return JSONResponse({"error": "Database unavailable"}, status_code=500)
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get deal
        cur.execute("SELECT * FROM properties WHERE id = %s", (deal_id,))
        deal = cur.fetchone()
        
        if not deal:
            return JSONResponse({"error": "Deal not found"}, status_code=404)
        
        # Update deal status
        cur.execute("""
            UPDATE properties SET deal_status = 'sold', buyer_name = %s, buyer_email = %s, sold_at = NOW()
            WHERE id = %s
        """, (buyer_data.get("buyer_name"), buyer_data.get("buyer_email"), deal_id))
        
        # Log transaction
        cur.execute("""
            INSERT INTO deal_pipeline (property_id, action, details, created_at)
            VALUES (%s, %s, %s, NOW())
        """, (deal_id, 'purchased', json.dumps(buyer_data)))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return JSONResponse({
            "success": True,
            "deal_id": deal_id,
            "message": "Deal purchased! Contracts ready for signing.",
            "assignment_fee": float(deal['assignment_fee'] or 0),
            "next_step": "Download contracts from your buyer portal"
        })
    
    except Exception as e:
        logger.error(f"Purchase deal error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# === KPI TRACKING ===
@app.get("/api/kpi/daily")
async def get_daily_kpi():
    """Get today's KPI metrics"""
    try:
        conn = get_db_connection()
        if not conn:
            return JSONResponse({"error": "Database unavailable"}, status_code=500)
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Today's stats
        cur.execute("""
            SELECT 
                COUNT(*) as total_deals,
                COUNT(CASE WHEN profit_tier = 'green' THEN 1 END) as green_deals,
                COUNT(CASE WHEN profit_tier = 'yellow' THEN 1 END) as yellow_deals,
                COUNT(CASE WHEN deal_status = 'sold' THEN 1 END) as sold_deals,
                COALESCE(SUM(assignment_fee), 0) as total_assignment_fees
            FROM properties
            WHERE created_at::date = CURRENT_DATE
        """)
        
        stats = cur.fetchone()
        cur.close()
        conn.close()
        
        return JSONResponse({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total_deals_found": stats['total_deals'] or 0,
            "green_deals": stats['green_deals'] or 0,
            "yellow_deals": stats['yellow_deals'] or 0,
            "deals_sold": stats['sold_deals'] or 0,
            "total_revenue": float(stats['total_assignment_fees'] or 0),
            "average_fee": float((stats['total_assignment_fees'] or 0) / max(stats['sold_deals'] or 1, 1))
        })
    
    except Exception as e:
        logger.error(f"KPI error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# === HTML SELLER FORM ===
@app.get("/seller", response_class=HTMLResponse)
async def seller_form():
    return """<!DOCTYPE html>
<html>
<head>
    <title>Sell Your Property Fast | VortexAI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
        .container { background: white; border-radius: 15px; box-shadow: 0 10px 40px rgba(0,0,0,0.3); max-width: 600px; width: 100%; padding: 40px; }
        h1 { color: #333; margin-bottom: 10px; font-size: 28px; }
        .subtitle { color: #666; margin-bottom: 30px; font-size: 14px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; color: #333; font-weight: 600; }
        input, select, textarea { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; }
        input:focus, select:focus, textarea:focus { outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1); }
        button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 30px; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; width: 100%; transition: transform 0.2s; }
        button:hover { transform: translateY(-2px); }
        .result { display: none; padding: 20px; background: #f0f9ff; border-left: 4px solid #667eea; border-radius: 8px; margin-top: 20px; }
        .result.success { border-left-color: #10b981; background: #f0fdf4; }
        .result.error { border-left-color: #ef4444; background: #fef2f2; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        @media (max-width: 600px) { .grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <h1>💰 Get Cash for Your House Fast</h1>
        <p class="subtitle">We buy houses in ANY condition. Get an instant offer in 24 hours.</p>
        
        <form id="sellerForm">
            <div class="grid">
                <div class="form-group">
                    <label>Address *</label>
                    <input type="text" name="address" required>
                </div>
                <div class="form-group">
                    <label>City *</label>
                    <input type="text" name="city" required>
                </div>
            </div>
            
            <div class="grid">
                <div class="form-group">
                    <label>State *</label>
                    <input type="text" name="state" required maxlength="2">
                </div>
                <div class="form-group">
                    <label>Your Asking Price *</label>
                    <input type="number" name="seller_asking_price" required>
                </div>
            </div>
            
            <div class="grid">
                <div class="form-group">
                    <label>Bedrooms</label>
                    <input type="number" name="bedrooms" value="3">
                </div>
                <div class="form-group">
                    <label>Bathrooms</label>
                    <input type="number" name="bathrooms" value="2">
                </div>
            </div>
            
            <div class="form-group">
                <label>Property Condition *</label>
                <select name="condition" required>
                    <option value="">-- Select --</option>
                    <option value="excellent">Excellent</option>
                    <option value="good">Good</option>
                    <option value="fair">Fair</option>
                    <option value="poor">Poor / Needs Work</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>Estimated Repair Cost ($)</label>
                <input type="number" name="estimated_repair_cost" value="0">
            </div>
            
            <div class="grid">
                <div class="form-group">
                    <label>Your Name *</label>
                    <input type="text" name="seller_name" required>
                </div>
                <div class="form-group">
                    <label>Phone *</label>
                    <input type="tel" name="seller_phone" required>
                </div>
            </div>
            
            <div class="form-group">
                <label>Email *</label>
                <input type="email" name="seller_email" required>
            </div>
            
            <button type="submit">📨 Get My Instant Offer</button>
        </form>
        
        <div id="result" class="result"></div>
    </div>
    
    <script>
        document.getElementById('sellerForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);
            data.estimated_repair_cost = parseInt(data.estimated_repair_cost || 0);
            data.seller_asking_price = parseInt(data.seller_asking_price || 0);
            data.bedrooms = parseInt(data.bedrooms || 3);
            data.bathrooms = parseInt(data.bathrooms || 2);
            
            try {
                const res = await fetch('/api/seller/intake', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await res.json();
                const resultDiv = document.getElementById('result');
                
                if (result.success) {
                    resultDiv.className = 'result success';
                    resultDiv.innerHTML = `
                        <h3>✅ Offer Submitted!</h3>
                        <p><strong>Property ID:</strong> ${result.property_id}</p>
                        <p><strong>Estimated Value:</strong> $${result.estimated_arv.toLocaleString()}</p>
                        <p><strong>Our Maximum Offer:</strong> $${result.mao.toLocaleString()}</p>
                        <p><strong>Deal Potential:</strong> ${result.profit_tier}</p>
                        <p style="margin-top: 10px; font-size: 12px; color: #666;">A representative will contact you within 24 hours.</p>
                    `;
                } else {
                    resultDiv.className = 'result error';
                    resultDiv.innerHTML = `<h3>❌ Error</h3><p>${result.error}</p>`;
                }
                resultDiv.style.display = 'block';
            } catch (err) {
                document.getElementById('result').className = 'result error';
                document.getElementById('result').innerHTML = `<p>Error: ${err.message}</p>`;
                document.getElementById('result').style.display = 'block';
            }
        });
    </script>
</body>
</html>"""

# === HTML BUYER PORTAL ===
@app.get("/buyer", response_class=HTMLResponse)
async def buyer_portal():
    return """<!DOCTYPE html>
<html>
<head>
    <title>Available Deals | VortexAI Buyer Portal</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; }
        h1 { font-size: 32px; margin-bottom: 10px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-top: 20px; }
        .stat { background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; }
        .stat-number { font-size: 28px; font-weight: bold; }
        .stat-label { font-size: 12px; opacity: 0.9; margin-top: 5px; }
        .deals { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }
        .deal-card { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1); transition: transform 0.3s; }
        .deal-card:hover { transform: translateY(-5px); }
        .deal-header { padding: 20px; background: #f8f9fa; border-bottom: 2px solid #eee; }
        .deal-tier { display: inline-block; padding: 8px 16px; border-radius: 20px; font-weight: bold; font-size: 12px; }
        .tier-green { background: #10b981; color: white; }
        .tier-yellow { background: #f59e0b; color: white; }
        .address { font-size: 20px; font-weight: bold; color: #333; margin-top: 10px; }
        .deal-body { padding: 20px; }
        .detail { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }
        .detail-label { color: #666; font-weight: 600; }
        .detail-value { color: #333; font-weight: bold; }
        button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 24px; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; width: 100%; font-size: 14px; }
        button:hover { opacity: 0.9; }
        .loading { text-align: center; padding: 40px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎯 Available Deals</h1>
            <p>Fresh wholesale deals updated every 5 minutes</p>
            <div class="stats" id="stats" style="display: none;">
                <div class="stat">
                    <div class="stat-number" id="totalDeals">0</div>
                    <div class="stat-label">Total Deals</div>
                </div>
                <div class="stat">
                    <div class="stat-number" id="greenDeals">0</div>
                    <div class="stat-label">🟢 Excellent Deals</div>
                </div>
                <div class="stat">
                    <div class="stat-number" id="yellowDeals">0</div>
                    <div class="stat-label">🟡 Good Deals</div>
                </div>
            </div>
        </header>
        
        <div id="deals" class="deals">
            <div class="loading">Loading deals...</div>
        </div>
    </div>
    
    <script>
        async function loadDeals() {
            try {
                const res = await fetch('/api/deals/available');
                const data = await res.json();
                
                document.getElementById('totalDeals').textContent = data.total_deals;
                document.getElementById('greenDeals').textContent = data.green_count;
                document.getElementById('yellowDeals').textContent = data.yellow_count;
                document.getElementById('stats').style.display = 'grid';
                
                if (data.deals.length === 0) {
                    document.getElementById('deals').innerHTML = '<p style="grid-column: 1/-1; text-align: center; padding: 40px; color: #666;">No deals available yet. Check back soon!</p>';
                    return;
                }
                
                document.getElementById('deals').innerHTML = data.deals.map(deal => `
                    <div class="deal-card">
                        <div class="deal-header">
                            <span class="deal-tier ${deal.profit_tier === 'green' ? 'tier-green' : 'tier-yellow'}">
                                ${deal.profit_tier_display}
                            </span>
                            <div class="address">${deal.address}</div>
                            <div style="font-size: 12px; color: #999; margin-top: 5px;">${deal.city}, ${deal.state}</div>
                        </div>
                        <div class="deal-body">
                            <div class="detail">
                                <span class="detail-label">Our Max Offer:</span>
                                <span class="detail-value">$${deal.mao.toLocaleString()}</span>
                            </div>
                            <div class="detail">
                                <span class="detail-label">Assignment Fee:</span>
                                <span class="detail-value">$${deal.assignment_fee.toLocaleString()}</span>
                            </div>
                            <div class="detail">
                                <span class="detail-label">ARV:</span>
                                <span class="detail-value">$${deal.estimated_arv.toLocaleString()}</span>
                            </div>
                            <div class="detail">
                                <span class="detail-label">Repairs:</span>
                                <span class="detail-value">$${deal.estimated_repair.toLocaleString()}</span>
                            </div>
                            <div class="detail">
                                <span class="detail-label">Bedrooms:</span>
                                <span class="detail-value">${deal.bedrooms} | Bathrooms: ${deal.bathrooms}</span>
                            </div>
                            <button onclick="buyDeal(${deal.id})">📝 Buy This Deal</button>
                        </div>
                    </div>
                `).join('');
            } catch (err) {
                document.getElementById('deals').innerHTML = `<p style="color: red;">Error loading deals: ${err.message}</p>`;
            }
        }
        
        function buyDeal(dealId) {
            const buyerName = prompt('Enter your name:');
            if (!buyerName) return;
            
            const buyerEmail = prompt('Enter your email:');
            if (!buyerEmail) return;
            
            fetch(`/api/deals/${dealId}/purchase`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ buyer_name: buyerName, buyer_email: buyerEmail })
            }).then(res => res.json()).then(data => {
                if (data.success) {
                    alert('✅ Deal purchased! Contracts are ready.\n\n' + data.message);
                    loadDeals();
                } else {
                    alert('Error: ' + data.error);
                }
            });
        }
        
        loadDeals();
        setInterval(loadDeals, 300000);
    </script>
</body>
</html>"""

# === RUN SERVER ===
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
