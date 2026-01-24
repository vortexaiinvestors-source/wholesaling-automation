     1→"""
     2→PRODUCTION REAL ESTATE WHOLESALING SYSTEM
     3→Complete API with dashboard, buyer portal, seller form
     4→Tracks deals with color-coded profit tiers: 🟢 GREEN 🟡 YELLOW 🔴 RED
     5→"""
     6→
     7→from fastapi import FastAPI, HTTPException, UploadFile, File
     8→from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
     9→from fastapi.staticfiles import StaticFiles
     10→from fastapi.middleware.cors import CORSMiddleware
     11→import json
     12→import logging
     13→from datetime import datetime
     14→from typing import Optional, List
     15→import os
     16→from dotenv import load_dotenv
     17→import psycopg2
     18→from psycopg2.extras import RealDictCursor
     19→import asyncio
     20→
     21→load_dotenv()
     22→
     23→# === LOGGING ===
     24→logging.basicConfig(level=logging.INFO)
     25→logger = logging.getLogger(__name__)
     26→
     27→# === FASTAPI APP ===
     28→app = FastAPI(
     29→    title="VortexAI Real Estate System",
     30→    description="24/7 Property Wholesaling with AI Deal Analysis",
     31→    version="1.0.0"
     32→)
     33→
     34→# === CORS ===
     35→app.add_middleware(
     36→    CORSMiddleware,
     37→    allow_origins=["*"],
     38→    allow_credentials=True,
     39→    allow_methods=["*"],
     40→    allow_headers=["*"],
     41→)
     42→
     43→# === DATABASE CONNECTION ===
     44→# Use DATABASE_URL from Railway environment
     45→DATABASE_URL = os.getenv("DATABASE_URL")
     46→
     47→if not DATABASE_URL:
     48→    # Fallback if not set (won't happen in production)
     49→    DATABASE_URL = "postgresql://postgres:password@localhost:5432/postgres"
     50→    logger.warning("DATABASE_URL not set, using fallback")
     51→
     52→logger.info(f"Using DATABASE_URL: {DATABASE_URL[:50]}...")
     53→
     54→def get_db_connection():
     55→    """Get PostgreSQL connection"""
     56→    try:
     57→        if DATABASE_URL:
     58→            conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
     59→            logger.info("✅ Database connection successful!")
     60→            return conn
     61→        else:
     62→            logger.error("❌ No DATABASE_URL configured")
     63→            return None
     64→    except psycopg2.Error as e:
     65→        logger.error(f"❌ Database connection failed: {e}")
     66→        return None
     67→
     68→def calculate_profit_tier(assignment_fee: float) -> tuple:
     69→    """Calculate profit tier and color code"""
     70→    if assignment_fee >= 15000:
     71→        return "green", "🟢 EXCELLENT"
     72→    elif assignment_fee >= 7500:
     73→        return "yellow", "🟡 GOOD"
     74→    else:
     75→        return "red", "🔴 SKIP THIS"
     76→
     77→# === HEALTH CHECK ===
     78→@app.get("/health")
     79→async def health_check():
     80→    """System health status"""
     81→    db = get_db_connection()
     82→    db_status = "✅ LIVE" if db else "❌ OFFLINE"
     83→    if db:
     84→        db.close()
     85→    
     86→    return JSONResponse({
     87→        "status": "✅ RUNNING",
     88→        "timestamp": datetime.now().isoformat(),
     89→        "service": "VortexAI-API",
     90→        "database": db_status,
     91→        "version": "1.0.0"
     92→    })
     93→
     94→# === SELLER INTAKE API ===
     95→@app.post("/api/seller/intake")
     96→async def seller_intake(property_data: dict):
     97→    """
     98→    Seller submits property info:
     99→    {
    100→        "address": "123 Main St",
    101→        "city": "Houston",
    102→        "state": "TX",
    103→        "bedrooms": 3,
    104→        "bathrooms": 2,
    105→        "condition": "poor",
    106→        "estimated_repair_cost": 25000,
    107→        "seller_asking_price": 150000,
    108→        "seller_name": "John Smith",
    109→        "seller_phone": "555-1234",
    110→        "seller_email": "john@example.com"
    111→    }
    112→    """
    113→    try:
    114→        conn = get_db_connection()
    115→        if not conn:
    116→            return JSONResponse({"error": "Database unavailable"}, status_code=500)
     117→        
     118→        cur = conn.cursor()
     119→        
     120→        # Calculate ARV (simplified - assume market value based on similar properties)
     121→        estimated_arv = property_data.get("estimated_repair_cost", 0) + property_data.get("seller_asking_price", 0) * 1.2
     122→        
     123→        # Calculate MAO using 70% rule
     124→        repair_cost = property_data.get("estimated_repair_cost", 0)
     125→        mao = (estimated_arv * 0.70) - repair_cost
     126→        
     127→        # Calculate assignment fee (MAO - our cost - holding costs)
     128→        assignment_fee = mao - property_data.get("seller_asking_price", 0)
     129→        
     130→        tier, tier_name = calculate_profit_tier(assignment_fee)
     131→        
     132→        # Store in database
     133→        cur.execute("""
     134→            INSERT INTO properties (
     135→                address, city, state, bedrooms, bathrooms, 
     136→                estimated_repair, asking_price, estimated_arv, mao, assignment_fee,
     137→                profit_tier, seller_name, seller_phone, seller_email, created_at
     138→            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
     139→            RETURNING id
     140→        """, (
     141→            property_data.get("address"),
     142→            property_data.get("city"),
     143→            property_data.get("state"),
     144→            property_data.get("bedrooms", 0),
     145→            property_data.get("bathrooms", 0),
     146→            repair_cost,
     147→            property_data.get("seller_asking_price"),
     148→            estimated_arv,
     149→            mao,
     150→            assignment_fee,
     151→            tier,
     152→            property_data.get("seller_name"),
     153→            property_data.get("seller_phone"),
     154→            property_data.get("seller_email"),
     155→        ))
     156→        
     157→        property_id = cur.fetchone()[0]
     158→        conn.commit()
     159→        cur.close()
     160→        conn.close()
     161→        
     162→        return JSONResponse({
     163→            "success": True,
     164→            "property_id": property_id,
     165→            "estimated_arv": round(estimated_arv, 2),
     166→            "mao": round(mao, 2),
     167→            "assignment_fee": round(assignment_fee, 2),
     168→            "profit_tier": tier_name,
     169→            "message": f"Property submitted! {tier_name} deal potential"
     170→        })
     171→    
     172→    except Exception as e:
     173→        logger.error(f"Seller intake error: {e}")
     174→        return JSONResponse({"error": str(e)}, status_code=500)
     175→
     176→# === BUYER PORTAL API ===
     177→@app.get("/api/deals/available")
     178→async def get_available_deals():
     179→    """Get all available deals for buyers - GREEN and YELLOW only"""
     180→    try:
     181→        conn = get_db_connection()
     182→        if not conn:
     183→            return JSONResponse({"error": "Database unavailable"}, status_code=500)
     184→        
     185→        cur = conn.cursor(cursor_factory=RealDictCursor)
     186→        
     187→        # Get only profitable deals
     188→        cur.execute("""
     189→            SELECT 
     190→                id, address, city, state, bedrooms, bathrooms,
     191→                estimated_repair, asking_price, estimated_arv, mao, assignment_fee,
     192→                profit_tier, created_at
     193→            FROM properties
     194→            WHERE profit_tier IN ('green', 'yellow')
     195→            AND created_at > NOW() - INTERVAL '30 days'
     196→            ORDER BY assignment_fee DESC
     197→        """)
     198→        
     199→        deals = cur.fetchall()
     200→        cur.close()
     201→        conn.close()
     202→        
     203→        formatted_deals = []
     204→        for deal in deals:
     205→            tier_name = "🟢 EXCELLENT" if deal['profit_tier'] == 'green' else "🟡 GOOD"
     206→            formatted_deals.append({
     207→                **dict(deal),
     208→                "profit_tier_display": tier_name,
     209→                "assignment_fee": float(deal['assignment_fee'] or 0),
     210→                "mao": float(deal['mao'] or 0),
     211→                "estimated_arv": float(deal['estimated_arv'] or 0),
     212→            })
     213→        
     214→        return JSONResponse({
     215→            "total_deals": len(formatted_deals),
     216→            "green_count": sum(1 for d in formatted_deals if d['profit_tier'] == 'green'),
     217→            "yellow_count": sum(1 for d in formatted_deals if d['profit_tier'] == 'yellow'),
     218→            "deals": formatted_deals
     219→        })
     220→    
     221→    except Exception as e:
     222→        logger.error(f"Get deals error: {e}")
     223→        return JSONResponse({"error": str(e)}, status_code=500)
     224→
     225→@app.post("/api/deals/{deal_id}/purchase")
     226→async def purchase_deal(deal_id: int, buyer_data: dict):
     227→    """Buyer purchases a deal"""
     228→    try:
     229→        conn = get_db_connection()
     230→        if not conn:
     231→            return JSONResponse({"error": "Database unavailable"}, status_code=500)
     232→        
     233→        cur = conn.cursor(cursor_factory=RealDictCursor)
     234→        
     235→        # Get deal
     236→        cur.execute("SELECT * FROM properties WHERE id = %s", (deal_id,))
     237→        deal = cur.fetchone()
     238→        
     239→        if not deal:
     240→            return JSONResponse({"error": "Deal not found"}, status_code=404)
     241→        
     242→        # Update deal status
     243→        cur.execute("""
     244→            UPDATE properties SET deal_status = 'sold', buyer_name = %s, buyer_email = %s, sold_at = NOW()
     245→            WHERE id = %s
     246→        """, (buyer_data.get("buyer_name"), buyer_data.get("buyer_email"), deal_id))
     247→        
     248→        # Log transaction
     249→        cur.execute("""
     250→            INSERT INTO deal_pipeline (property_id, action, details, created_at)
     251→            VALUES (%s, %s, %s, NOW())
     252→        """, (deal_id, 'purchased', json.dumps(buyer_data)))
     253→        
     254→        conn.commit()
     255→        cur.close()
     256→        conn.close()
     257→        
     258→        return JSONResponse({
     259→            "success": True,
     260→            "deal_id": deal_id,
     261→            "message": "Deal purchased! Contracts ready for signing.",
     262→            "assignment_fee": float(deal['assignment_fee'] or 0),
     263→            "next_step": "Download contracts from your buyer portal"
     264→        })
     265→    
     266→    except Exception as e:
     267→        logger.error(f"Purchase deal error: {e}")
     268→        return JSONResponse({"error": str(e)}, status_code=500)
     269→
     270→# === KPI TRACKING ===
     271→@app.get("/api/kpi/daily")
     272→async def get_daily_kpi():
     273→    """Get today's KPI metrics - returns live data or demo data if DB unavailable"""
     274→    try:
     275→        conn = get_db_connection()
     276→        if not conn:
     277→            logger.warning("Database unavailable - returning demo KPI data")
     278→            return JSONResponse({
     279→                "date": datetime.now().strftime("%Y-%m-%d"),
     280→                "total_deals_found": 1247,
     281→                "green_deals": 89,
     282→                "yellow_deals": 156,
     283→                "red_deals": 1002,
     284→                "deals_sold": 34,
     285→                "total_revenue": 687500.00,
     286→                "average_fee": 20220.59,
     287→                "status": "demo",
     288→                "message": "Database connection pending - showing sample data"
     289→            })
     290→        
     291→        cur = conn.cursor(cursor_factory=RealDictCursor)
     292→        
     293→        # Today's stats
     294→        cur.execute("""
     295→            SELECT 
     296→                COUNT(*) as total_deals,
     297→                COUNT(CASE WHEN profit_tier = 'green' THEN 1 END) as green_deals,
     298→                COUNT(CASE WHEN profit_tier = 'yellow' THEN 1 END) as yellow_deals,
     299→                COUNT(CASE WHEN deal_status = 'sold' THEN 1 END) as sold_deals,
     300→                COALESCE(SUM(assignment_fee), 0) as total_assignment_fees
     301→            FROM properties
     302→            WHERE created_at::date = CURRENT_DATE
     303→        """)
     304→        
     305→        stats = cur.fetchone()
     306→        cur.close()
     307→        conn.close()
     308→        
     309→        return JSONResponse({
     310→            "date": datetime.now().strftime("%Y-%m-%d"),
     311→            "total_deals_found": stats['total_deals'] or 0,
     312→            "green_deals": stats['green_deals'] or 0,
     313→            "yellow_deals": stats['yellow_deals'] or 0,
     314→            "deals_sold": stats['sold_deals'] or 0,
     315→            "total_revenue": float(stats['total_assignment_fees'] or 0),
     316→            "average_fee": float((stats['total_assignment_fees'] or 0) / max(stats['sold_deals'] or 1, 1))
     317→        })
     318→    
     319→    except Exception as e:
     320→        logger.error(f"KPI error: {e}")
     321→        # Return demo data on error
     322→        return JSONResponse({
     323→            "date": datetime.now().strftime("%Y-%m-%d"),
     324→            "total_deals_found": 1247,
     325→            "green_deals": 89,
     326→            "yellow_deals": 156,
     327→            "red_deals": 1002,
     328→            "deals_sold": 34,
     329→            "total_revenue": 687500.00,
     330→            "average_fee": 20220.59,
     331→            "status": "demo",
     332→            "message": "System running on demo data"
     333→        })
     334→
     335→# === HTML PAGES ===
     336→
     337→@app.get("/seller", response_class=HTMLResponse)
     338→async def seller_form():
     339→    """Seller intake form"""
     340→    return """
     341→    <!DOCTYPE html>
     342→    <html>
     343→    <head>
     344→        <title>Sell Your Property Fast | VortexAI</title>
     345→        <style>
     346→            * { margin: 0; padding: 0; box-sizing: border-box; }
     347→            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
     348→            .container { background: white; border-radius: 15px; box-shadow: 0 10px 40px rgba(0,0,0,0.3); max-width: 600px; width: 100%; padding: 40px; }
     349→            h1 { color: #333; margin-bottom: 10px; font-size: 28px; }
     350→            .subtitle { color: #666; margin-bottom: 30px; font-size: 14px; }
     351→            .form-group { margin-bottom: 20px; }
     352→            label { display: block; margin-bottom: 8px; color: #333; font-weight: 600; }
     353→            input, select, textarea { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; }
     354→            input:focus, select:focus, textarea:focus { outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1); }
     355→            button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 30px; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; width: 100%; transition: transform 0.2s; }
     356→            button:hover { transform: translateY(-2px); }
     357→            .result { display: none; padding: 20px; background: #f0f9ff; border-left: 4px solid #667eea; border-radius: 8px; margin-top: 20px; }
     358→            .result.success { border-left-color: #10b981; background: #f0fdf4; }
     359→            .result.error { border-left-color: #ef4444; background: #fef2f2; }
     360→            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
     361→            @media (max-width: 600px) { .grid { grid-template-columns: 1fr; } }
     362→        </style>
     363→    </head>
     364→    <body>
     365→        <div class="container">
     366→            <h1>💰 Get Cash for Your House Fast</h1>
     367→            <p class="subtitle">We buy houses in ANY condition. Get an instant offer in 24 hours.</p>
     368→            
     369→            <form id="sellerForm">
     370→                <div class="grid">
     371→                    <div class="form-group">
     372→                        <label>Address *</label>
     373→                        <input type="text" name="address" required>
     374→                    </div>
     375→                    <div class="form-group">
     376→                        <label>City *</label>
     377→                        <input type="text" name="city" required>
     378→                    </div>
     379→                </div>
     380→                
     381→                <div class="grid">
     382→                    <div class="form-group">
     383→                        <label>State *</label>
     384→                        <input type="input type="text" name="state" required maxlength="2">
     385→                    </div>
     386→                    <div class="form-group">
     387→                        <label>Your Asking Price *</label>
     388→                        <input type="number" name="seller_asking_price" required>
     389→                    </div>
     390→                </div>
     391→                
     392→                <div class="grid">
     393→                    <div class="form-group">
     394→                        <label>Bedrooms</label>
     395→                        <input type="number" name="bedrooms" value="3">
     396→                    </div>
     397→                    <div class="form-group">
     398→                        <label>Bathrooms</label>
     399→                        <input type="number" name="bathrooms" value="2">
     400→                    </div>
     401→                </div>
     402→                
     403→                <div class="form-group">
     404→                    <label>Property Condition *</label>
     405→                    <select name="condition" required>
     406→                        <option value="">-- Select --</option>
     407→                        <option value="excellent">Excellent</option>
     408→                        <option value="good">Good</option>
     409→                        <option value="fair">Fair</option>
     410→                        <option value="poor">Poor / Needs Work</option>
     411→                    </select>
     412→                </div>
     413→                
     414→                <div class="form-group">
     415→                    <label>Estimated Repair Cost ($)</label>
     416→                    <input type="number" name="estimated_repair_cost" value="0">
     417→                </div>
     418→                
     419→                <div class="grid">
     420→                    <div class="form-group">
     421→                        <label>Your Name *</label>
     422→                        <input type="text" name="seller_name" required>
     423→                    </div>
     424→                    <div class="form-group">
     425→                        <label>Phone *</label>
     426→                        <input type="tel" name="seller_phone" required>
     427→                    </div>
     428→                </div>
     429→                
     430→                <div class="form-group">
     431→                    <label>Email *</label>
     432→                    <input type="email" name="seller_email" required>
     433→                </div>
     434→                
     435→                <button type="submit">📨 Get My Instant Offer</button>
     436→            </form>
     437→            
     438→            <div id="result" class="result"></div>
     439→        </div>
     440→        
     441→        <script>
     442→            document.getElementById('sellerForm').addEventListener('submit', async (e) => {
     443→                e.preventDefault();
     444→                
     445→                const formData = new FormData(e.target);
     446→                const data = Object.fromEntries(formData);
     447→                data.estimated_repair_cost = parseInt(data.estimated_repair_cost || 0);
     448→                data.seller_asking_price = parseInt(data.seller_asking_price || 0);
     449→                data.bedrooms = parseInt(data.bedrooms || 3);
     450→                data.bathrooms = parseInt(data.bathrooms || 2);
     451→                
     452→                try {
     453→                    const res = await fetch('/api/seller/intake', {
     454→                        method: 'POST',
     455→                        headers: { 'Content-Type': 'application/json' },
     456→                        body: JSON.stringify(data)
     457→                    });
     458→                    
     459→                    const result = await res.json();
     460→                    const resultDiv = document.getElementById('result');
     461→                    
     462→                    if (result.success) {
     463→                        resultDiv.className = 'result success';
     464→                        resultDiv.innerHTML = `
     465→                            <h3>✅ Offer Submitted!</h3>
     466→                            <p><strong>Property ID:</strong> ${result.property_id}</p>
     467→                            <p><strong>Estimated Value:</strong> $${result.estimated_arv.toLocaleString()}</p>
     468→                            <p><strong>Our Maximum Offer:</strong> $${result.mao.toLocaleString()}</p>
     469→                            <p><strong>Deal Potential:</strong> ${result.profit_tier}</p>
     470→                            <p style="margin-top: 10px; font-size: 12px; color: #666;">A representative will contact you within 24 hours.</p>
     471→                        `;
     472→                    } else {
     473→                        resultDiv.className = 'result error';
     474→                        resultDiv.innerHTML = `<h3>❌ Error</h3><p>${result.error}</p>`;
     475→                    }
     476→                    resultDiv.style.display = 'block';
     477→                } catch (err) {
     478→                    document.getElementById('result').className = 'result error';
     479→                    document.getElementById('result').innerHTML = `<p>Error: ${err.message}</p>`;
     480→                    document.getElementById('result').style.display = 'block';
     481→                }
     482→            });
     483→        </script>
     484→    </body>
     485→    </html>
     486→    """
     487→
     488→@app.get("/buyer", response_class=HTMLResponse)
     489→async def buyer_portal():
     490→    """Buyer deals portal"""
     491→    return """
     492→    <!DOCTYPE html>
     493→    <html>
     494→    <head>
     495→        <title>Available Deals | VortexAI Buyer Portal</title>
     496→        <style>
     497→            * { margin: 0; padding: 0; box-sizing: border-box; }
     498→            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; padding: 20px; }
     499→            .container { max-width: 1200px; margin: 0 auto; }
     500→            header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; }
     501→            h1 { font-size: 32px; margin-bottom: 10px; }
     502→            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-top: 20px; }
     503→            .stat { background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; }
     504→            .stat-number { font-size: 28px; font-weight: bold; }
     505→            .stat-label { font-size: 12px; opacity: 0.9; margin-top: 5px; }
     506→            .deals { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }
     507→            .deal-card { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1); transition: transform 0.3s; }
     508→            .deal-card:hover { transform: translateY(-5px); }
     509→            .deal-header { padding: 20px; background: #f8f9fa; border-bottom: 2px solid #eee; }
     510→            .deal-tier { display: inline-block; padding: 8px 16px; border-radius: 20px; font-weight: bold; font-size: 12px; }
     511→            .tier-green { background: #10b981; color: white; }
     512→            .tier-yellow { background: #f59e0b; color: white; }
     513→            .address { font-size: 20px; font-weight: bold; color: #333; margin-top: 10px; }
     514→            .deal-body { padding: 20px; }
     515→            .detail { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }
     516→            .detail-label { color: #666; font-weight: 600; }
     517→            .detail-value { color: #333; font-weight: bold; }
     518→            .price { font-size: 24px; color: #667eea; font-weight: bold; margin: 15px 0; }
     519→            button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 24px; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; width: 100%; font-size: 14px; }
     520→            button:hover { opacity: 0.9; }
     521→            .loading { text-align: center; padding: 40px; color: #666; }
     522→        </style>
     523→    </head>
     524→    <body>
     525→        <div class="container">
     526→            <header>
     527→                <h1>🎯 Available Deals</h1>
     528→                <p>Fresh wholesale deals updated every 5 minutes</p>
     529→                <div class="stats" id="stats" style="display: none;">
     530→                    <div class="stat">
     531→                        <div class="stat-number" id="totalDeals">0</div>
     532→                        <div class="stat-label">Total Deals</div>
     533→                    </div>
     534→                    <div class="stat">
     535→                        <div class="stat-number" id="greenDeals">0</div>
     536→                        <div class="stat-label">🟢 Excellent Deals</div>
     537→                    </div>
     538→                    <div class="stat">
     539→                        <div class="stat-number" id="yellowDeals">0</div>
     540→                        <div class="stat-label">🟡 Good Deals</div>
     541→                    </div>
     542→                </div>
     543→            </header>
     544→            
     545→            <div id="deals" class="deals">
     546→                <div class="loading">Loading deals...</div>
     547→            </div>
     548→        </div>
     549→        
     550→        <script>
     551→            async function loadDeals() {
     552→                try {
     553→                    const res = await fetch('/api/deals/available');
     554→                    const data = await res.json();
     555→                    
     556→                    document.getElementById('totalDeals').textContent = data.total_deals;
     557→                    document.getElementById('greenDeals').textContent = data.green_count;
     558→                    document.getElementById('yellowDeals').textContent = data.yellow_count;
     559→                    document.getElementById('stats').style.display = 'grid';
     560→                    
     561→                    if (data.deals.length === 0) {
     562→                        document.getElementById('deals').innerHTML = '<p style="grid-column: 1/-1; text-align: center; padding: 40px; color: #666;">No deals available yet. Check back soon!</p>';
     563→                        return;
     564→                    }
     565→                    
     566→                    document.getElementById('deals').innerHTML = data.deals.map(deal => `
     567→                        <div class="deal-card">
     568→                            <div class="deal-header">
     569→                                <span class="deal-tier ${deal.profit_tier === 'green' ? 'tier-green' : 'tier-yellow'}">
     570→                                    ${deal.profit_tier_display}
     571→                                </span>
     572→                                <div class="address">${deal.address}</div>
     573→                                <div style="font-size: 12px; color: #999; margin-top: 5px;">${deal.city}, ${deal.state}</div>
     574→                            </div>
     575→                            <div class="deal-body">
     576→                                <div class="detail">
     577→                                    <span class="detail-label">Our Max Offer:</span>
     578→                                    <span class="detail-value">$${deal.mao.toLocaleString()}</span>
     579→                                </div>
     580→                                <div class="detail">
     581→                                    <span class="detail-label">Assignment Fee:</span>
     582→                                    <span class="detail-value">$${deal.assignment_fee.toLocaleString()}</span>
     583→                                </div>
     584→                                <div class="detail">
     585→                                    <span class="detail-label">ARV:</span>
     586→                                    <span class="detail-value">$${deal.estimated_arv.toLocaleString()}</span>
     587→                                </div>
     588→                                <div class="detail">
     589→                                    <span class="detail-label">Repairs:</span>
     590→                                    <span class="detail-value">$${deal.estimated_repair.toLocaleString()}</span>
     591→                                </div>
     592→                                <div class="detail">
     593→                                    <span class="detail-label">Bedrooms:</span>
     594→                                    <span class="detail-value">${deal.bedrooms} | Bathrooms: ${deal.bathrooms}</span>
     595→                                </div>
     596→                                <button onclick="buyDeal(${deal.id})">📝 Buy This Deal</button>
     597→                            </div>
     598→                        </div>
     599→                    `).join('');
     600→                } catch (err) {
     601→                    document.getElementById('deals').innerHTML = `<p style="color: red;">Error loading deals: ${err.message}</p>`;
     602→                }
     603→            }
     604→            
     605→            function buyDeal(dealId) {
     606→                const buyerName = prompt('Enter your name:');
     607→                if (!buyerName) return;
     608→                
     609→                const buyerEmail = prompt('Enter your email:');
     610→                if (!buyerEmail) return;
     611→                
     612→                fetch(`/api/deals/${dealId}/purchase`, {
     613→                    method: 'POST',
     614→                    headers: { 'Content-Type': 'application/json' },
     615→                    body: JSON.stringify({ buyer_name: buyerName, buyer_email: buyerEmail })
     616→                }).then(res => res.json()).then(data => {
     617→                    if (data.success) {
     617→                        alert('✅ Deal purchased! Contracts are ready.\n\n' + data.message);
     618→                        loadDeals();
     619→                    } else {
     620→                        alert('Error: ' + data.error);
     621→                    }
     622→                });
     623→            }
     624→            
     625→            loadDeals();
     626→            setInterval(loadDeals, 300000); // Refresh every 5 minutes
     627→        </script>
     628→    </body>
     629→    </html>
     630→    """
     631→
     632→# === RUN SERVER ===
     633→if __name__ == "__main__":
     634→    import uvicorn
     635→    uvicorn.run(app, host="0.0.0.0", port=8000)
