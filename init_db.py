"""
Initialize VortexAI database tables (v4)
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    exit(1)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Deals
cur.execute("""
CREATE TABLE IF NOT EXISTS deals (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    asset_type VARCHAR(50),
    location VARCHAR(255),
    price DECIMAL(12,2),
    description TEXT,
    profit_score INTEGER,
    urgency_score INTEGER,
    risk_score INTEGER,
    score INTEGER,
    url TEXT,
    source TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
""")

# Buyers
cur.execute("""
CREATE TABLE IF NOT EXISTS buyers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255) UNIQUE,
    location VARCHAR(255),
    asset_types VARCHAR(255),
    min_budget DECIMAL(12,2),
    max_budget DECIMAL(12,2),
    phone VARCHAR(50),
    role VARCHAR(50) DEFAULT 'buyer_free',
    stripe_customer_id VARCHAR(255),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);
""")

# Deal matches
cur.execute("""
CREATE TABLE IF NOT EXISTS deal_matches (
    id SERIAL PRIMARY KEY,
    deal_id INTEGER REFERENCES deals(id),
    buyer_id INTEGER REFERENCES buyers(id),
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);
""")

# AI insights
cur.execute("""
CREATE TABLE IF NOT EXISTS deal_ai_insights (
    deal_id INTEGER PRIMARY KEY REFERENCES deals(id),
    summary TEXT,
    recommendation TEXT,
    tags TEXT,
    buyer_message TEXT,
    seller_message TEXT,
    confidence INTEGER,
    created_at TIMESTAMP
);
""")

conn.commit()
cur.close()
conn.close()

print("✅ Database schema upgraded successfully")
