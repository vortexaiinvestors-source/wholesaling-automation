require('dotenv').config();
const { pool } = require('../config/database');

const createTables = async () => {
  console.log('🔨 Creating database schema...\n');

  try {
    // Create deals table
    await pool.query(`
      CREATE TABLE IF NOT EXISTS deals (
        id SERIAL PRIMARY KEY,
        title VARCHAR(500) NOT NULL,
        description TEXT,
        price DECIMAL(12, 2) NOT NULL,
        market_value DECIMAL(12, 2),
        category VARCHAR(100) NOT NULL,
        location VARCHAR(255),
        source VARCHAR(100) NOT NULL,
        source_url TEXT,
        image_url TEXT,
        contact_info TEXT,
        ai_score INTEGER DEFAULT 0,
        urgency_keywords TEXT[],
        discount_percentage DECIMAL(5, 2),
        profit_potential DECIMAL(12, 2),
        status VARCHAR(50) DEFAULT 'active',
        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    `);
    console.log('✅ Created deals table');

    // Create buyers table
    await pool.query(`
      CREATE TABLE IF NOT EXISTS buyers (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        phone VARCHAR(50),
        preferences JSONB,
        budget_min DECIMAL(12, 2),
        budget_max DECIMAL(12, 2),
        locations TEXT[],
        categories TEXT[],
        subscription_tier VARCHAR(50) DEFAULT 'free',
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    `);
    console.log('✅ Created buyers table');

    // Create matches table
    await pool.query(`
      CREATE TABLE IF NOT EXISTS matches (
        id SERIAL PRIMARY KEY,
        deal_id INTEGER REFERENCES deals(id) ON DELETE CASCADE,
        buyer_id INTEGER REFERENCES buyers(id) ON DELETE CASCADE,
        match_score INTEGER DEFAULT 0,
        status VARCHAR(50) DEFAULT 'pending',
        notified_at TIMESTAMP,
        viewed_at TIMESTAMP,
        interested_at TIMESTAMP,
        rejected_at TIMESTAMP,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    `);
    console.log('✅ Created matches table');

    // Create notifications table
    await pool.query(`
      CREATE TABLE IF NOT EXISTS notifications (
        id SERIAL PRIMARY KEY,
        match_id INTEGER REFERENCES matches(id) ON DELETE CASCADE,
        buyer_id INTEGER REFERENCES buyers(id) ON DELETE CASCADE,
        type VARCHAR(50) NOT NULL,
        channel VARCHAR(50) NOT NULL,
        content TEXT NOT NULL,
        sent_at TIMESTAMP,
        opened_at TIMESTAMP,
        clicked_at TIMESTAMP,
        status VARCHAR(50) DEFAULT 'pending',
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    `);
    console.log('✅ Created notifications table');

    // Create webhook_logs table
    await pool.query(`
      CREATE TABLE IF NOT EXISTS webhook_logs (
        id SERIAL PRIMARY KEY,
        source VARCHAR(100) NOT NULL,
        payload JSONB NOT NULL,
        processed BOOLEAN DEFAULT false,
        deal_id INTEGER REFERENCES deals(id),
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    `);
    console.log('✅ Created webhook_logs table');

    // Create indexes
    await pool.query('CREATE INDEX IF NOT EXISTS idx_deals_category ON deals(category);');
    await pool.query('CREATE INDEX IF NOT EXISTS idx_deals_status ON deals(status);');
    await pool.query('CREATE INDEX IF NOT EXISTS idx_deals_ai_score ON deals(ai_score DESC);');
    await pool.query('CREATE INDEX IF NOT EXISTS idx_buyers_email ON buyers(email);');
    await pool.query('CREATE INDEX IF NOT EXISTS idx_matches_deal_id ON matches(deal_id);');
    await pool.query('CREATE INDEX IF NOT EXISTS idx_matches_buyer_id ON matches(buyer_id);');
    await pool.query('CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);');
    console.log('✅ Created indexes');

    console.log('\n🎉 Database schema created successfully!');
  } catch (error) {
    console.error('❌ Error creating schema:', error);
    throw error;
  } finally {
    await pool.end();
  }
};

createTables();
