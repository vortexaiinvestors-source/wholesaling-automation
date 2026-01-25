"""
Initialize VortexAI database tables
Run once to set up the schema
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    exit(1)

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Deals table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS deals (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255),
            email VARCHAR(255),
            asset_type VARCHAR(50),
            location VARCHAR(255),
            price DECIMAL(12,2),
            description TEXT,
            score INTEGER DEFAULT 5,
            created_at TIMESTAMP DEFAULT NOW(),
            sent_to_buyers BOOLEAN DEFAULT false,
            sent_at TIMESTAMP,
            CONSTRAINT positive_price CHECK (price >= 0),
            CONSTRAINT valid_score CHECK (score >= 0 AND score <= 100)
        );
    """)
    
    # Buyers table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS buyers (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            location VARCHAR(255),
            asset_types VARCHAR(255),
            min_budget DECIMAL(12,2) DEFAULT 0,
            max_budget DECIMAL(12,2) DEFAULT 1000000,
            active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    
    # Sellers table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sellers (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            phone VARCHAR(20),
            location VARCHAR(255),
            active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    
    # Assignments table (deals assigned to buyers)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id SERIAL PRIMARY KEY,
            deal_id INTEGER REFERENCES deals(id),
            buyer_id INTEGER REFERENCES buyers(id),
            seller_id INTEGER REFERENCES sellers(id),
            assignment_fee DECIMAL(12,2),
            status VARCHAR(50) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT NOW(),
            closed_at TIMESTAMP
        );
    """)
    
    # KPI tracking table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kpi_daily (
            id SERIAL PRIMARY KEY,
            date DATE DEFAULT CURRENT_DATE,
            deals_found INTEGER DEFAULT 0,
            deals_scored INTEGER DEFAULT 0,
            deals_sent INTEGER DEFAULT 0,
            assignments INTEGER DEFAULT 0,
            revenue_total DECIMAL(12,2) DEFAULT 0,
            UNIQUE(date)
        );
    """)
    
    # Create indexes for better performance
    cur.execute("CREATE INDEX IF NOT EXISTS idx_deals_created ON deals(created_at);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_deals_sent ON deals(sent_to_buyers);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_deals_score ON deals(score);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_buyers_email ON buyers(email);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_assignments_deal ON assignments(deal_id);")
    
    conn.commit()
    cur.close()
    conn.close()
    
    print("✅ Database initialized successfully!")
    print("Tables created:")
    print("  - deals")
    print("  - buyers")
    print("  - sellers")
    print("  - assignments")
    print("  - kpi_daily")
    
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
