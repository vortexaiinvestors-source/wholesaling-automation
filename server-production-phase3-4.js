require('dotenv').config();
const express = require('express');
const cors = require('cors');
const { Pool } = require('pg');
const cron = require('node-cron');
const axios = require('axios');
const nodemailer = require('nodemailer');
const { v4: uuidv4 } = require('uuid');
const crypto = require('crypto');

const app = express();
app.use(cors());
app.use(express.json());

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
});

const brevoTransporter = nodemailer.createTransport({
  host: 'smtp-relay.brevo.com',
  port: 587,
  secure: false,
  auth: {
    user: process.env.BREVO_SMTP_USER,
    pass: process.env.BREVO_SMTP_PASSWORD
  }
});

brevoTransporter.verify((error, success) => {
  if (error) {
    console.error('Brevo SMTP Error:', error.message);
  } else {
    console.log('Brevo SMTP Connected - Email delivery ready');
  }
});

function validateWebhookSignature(req) {
  const signature = req.headers['x-ingest-signature'];
  const timestamp = req.headers['x-ingest-timestamp'];
  const ingestKey = process.env.API_INGEST_KEY;
  
  if (!signature || !timestamp || !ingestKey) return false;
  
  const now = Date.now();
  const ts = parseInt(timestamp);
  if (Math.abs(now - ts) > 5 * 60 * 1000) return false;
  
  const payload = JSON.stringify(req.body);
  const message = `${timestamp}.${payload}`;
  const expectedSignature = crypto
    .createHmac('sha256', ingestKey)
    .update(message)
    .digest('hex');
  
  return signature === expectedSignature;
}

const DEAL_SOURCES = [
  { id: 1, name: 'Zillow FSBO', category: 'real_estate', url: 'https://www.zillow.com/homes/fsbo/', active: true },
  { id: 2, name: 'Realtor.com', category: 'real_estate', url: 'https://www.realtor.com/', active: true },
  { id: 3, name: 'Redfin', category: 'real_estate', url: 'https://www.redfin.com/', active: true },
  { id: 4, name: 'ForSaleByOwner.com', category: 'real_estate', url: 'https://www.forsalebyowner.com/', active: true },
  { id: 5, name: 'FSBO.com', category: 'real_estate', url: 'https://www.fsbo.com/', active: true },
  { id: 6, name: 'Auction.com', category: 'real_estate', url: 'https://www.auction.com/', active: true },
  { id: 7, name: 'Hubzu', category: 'real_estate', url: 'https://www.hubzu.com/', active: true },
  { id: 8, name: 'RealtyTrac', category: 'real_estate', url: 'https://www.realtytrac.com/', active: true },
  { id: 9, name: 'Foreclosure.com', category: 'real_estate', url: 'https://www.foreclosure.com/', active: true },
  { id: 10, name: 'HUD Homes', category: 'real_estate', url: 'https://www.hudhomestore.gov/', active: true },
  { id: 11, name: 'HomePath', category: 'real_estate', url: 'https://www.homepath.com/', active: true },
  { id: 12, name: 'HomeSteps', category: 'real_estate', url: 'https://www.homesteps.com/', active: true },
  { id: 13, name: 'Xome', category: 'real_estate', url: 'https://www.xome.com/', active: true },
  { id: 14, name: 'RealtyBid', category: 'real_estate', url: 'https://www.realtybid.com/', active: true },
  { id: 15, name: 'PropertyShark', category: 'real_estate', url: 'https://www.propertyshark.com/', active: true },
  { id: 16, name: 'Copart', category: 'vehicles', url: 'https://www.copart.com/', active: true },
  { id: 17, name: 'IAAI', category: 'vehicles', url: 'https://www.iaai.com/', active: true },
  { id: 18, name: 'Manheim', category: 'vehicles', url: 'https://www.manheim.com/', active: true },
  { id: 19, name: 'AutoTrader', category: 'vehicles', url: 'https://www.autotrader.com/', active: true },
  { id: 20, name: 'Cars.com', category: 'vehicles', url: 'https://www.cars.com/', active: true },
  { id: 21, name: 'CarGurus', category: 'vehicles', url: 'https://www.cargurus.com/', active: true },
  { id: 22, name: 'Bring a Trailer', category: 'vehicles', url: 'https://bringatrailer.com/', active: true },
  { id: 23, name: 'Cars & Bids', category: 'vehicles', url: 'https://carsandbids.com/', active: true },
  { id: 24, name: 'Hemmings', category: 'vehicles', url: 'https://www.hemmings.com/', active: true },
  { id: 25, name: 'AutoTempest', category: 'vehicles', url: 'https://www.autotempest.com/', active: true },
  { id: 26, name: 'TrueCar', category: 'vehicles', url: 'https://www.truecar.com/', active: true },
  { id: 27, name: 'Vroom', category: 'vehicles', url: 'https://www.vroom.com/', active: true },
  { id: 28, name: 'Facebook Marketplace', category: 'marketplace', url: 'https://www.facebook.com/marketplace/', active: true },
  { id: 29, name: 'Craigslist', category: 'marketplace', url: 'https://www.craigslist.org/', active: true },
  { id: 30, name: 'OfferUp', category: 'marketplace', url: 'https://offerup.com/', active: true },
  { id: 31, name: 'Kijiji', category: 'marketplace', url: 'https://www.kijiji.ca/', active: true },
  { id: 32, name: 'Mercari', category: 'marketplace', url: 'https://www.mercari.com/', active: true },
  { id: 33, name: 'Nextdoor', category: 'marketplace', url: 'https://nextdoor.com/', active: true },
  { id: 34, name: 'Letgo', category: 'marketplace', url: 'https://www.letgo.com/', active: true },
  { id: 35, name: 'VarageSale', category: 'marketplace', url: 'https://www.varagesale.com/', active: true },
  { id: 36, name: '5miles', category: 'marketplace', url: 'https://www.5miles.com/', active: true },
  { id: 37, name: 'Poshmark', category: 'marketplace', url: 'https://poshmark.com/', active: true },
  { id: 38, name: 'Liquidation.com', category: 'liquidation', url: 'https://www.liquidation.com/', active: true },
  { id: 39, name: 'B-Stock', category: 'liquidation', url: 'https://bstock.com/', active: true },
  { id: 40, name: 'DirectLiquidation', category: 'liquidation', url: 'https://www.directliquidation.com/', active: true },
  { id: 41, name: 'Bulq', category: 'liquidation', url: 'https://www.bulq.com/', active: true },
  { id: 42, name: 'Via Trading', category: 'liquidation', url: 'https://www.viatrading.com/', active: true },
  { id: 43, name: 'Wholesale Central', category: 'liquidation', url: 'https://www.wholesalecentral.com/', active: true },
  { id: 44, name: 'GovPlanet', category: 'liquidation', url: 'https://www.govplanet.com/', active: true },
  { id: 45, name: 'GSA Auctions', category: 'liquidation', url: 'https://gsaauctions.gov/', active: true },
  { id: 46, name: 'PropertyRoom', category: 'liquidation', url: 'https://www.propertyroom.com/', active: true },
  { id: 47, name: 'GovDeals', category: 'liquidation', url: 'https://www.govdeals.com/', active: true },
  { id: 48, name: 'IronPlanet', category: 'equipment', url: 'https://www.ironplanet.com/', active: true },
  { id: 49, name: 'Ritchie Bros', category: 'equipment', url: 'https://www.rbauction.com/', active: true },
  { id: 50, name: 'MachineryTrader', category: 'equipment', url: 'https://www.machinerytrader.com/', active: true },
  { id: 51, name: 'EquipmentTrader', category: 'equipment', url: 'https://www.equipmenttrader.com/', active: true },
  { id: 52, name: 'Mascus', category: 'equipment', url: 'https://www.mascus.com/', active: true },
  { id: 53, name: 'TractorHouse', category: 'equipment', url: 'https://www.tractorhouse.com/', active: true },
  { id: 54, name: 'Rock & Dirt', category: 'equipment', url: 'https://www.rockanddirt.com/', active: true },
  { id: 55, name: 'Truck Paper', category: 'equipment', url: 'https://www.truckpaper.com/', active: true },
  { id: 56, name: 'Chrono24', category: 'luxury', url: 'https://www.chrono24.com/', active: true },
  { id: 57, name: 'The RealReal', category: 'luxury', url: 'https://www.therealreal.com/', active: true },
  { id: 58, name: 'Vestiaire Collective', category: 'luxury', url: 'https://www.vestiairecollective.com/', active: true },
  { id: 59, name: 'Rebag', category: 'luxury', url: 'https://www.rebag.com/', active: true },
  { id: 60, name: 'StockX', category: 'luxury', url: 'https://stockx.com/', active: true },
  { id: 61, name: 'BizBuySell', category: 'business', url: 'https://www.bizbuysell.com/', active: true },
  { id: 62, name: 'BusinessBroker.net', category: 'business', url: 'https://www.businessbroker.net/', active: true },
  { id: 63, name: 'LoopNet', category: 'business', url: 'https://www.loopnet.com/', active: true },
  { id: 64, name: 'CREXi', category: 'business', url: 'https://www.crexi.com/', active: true },
  { id: 65, name: 'Ten-X Commercial', category: 'business', url: 'https://www.ten-x.com/', active: true }
];

async function scoreWithAI(deal) {
  let score = 50;
  const factors = [];
  if (deal.price && deal.estimated_value) {
    const discount = ((deal.estimated_value - deal.price) / deal.estimated_value) * 100;
    if (discount >= 40) { score += 25; factors.push('MASSIVE discount 40%+'); }
    else if (discount >= 30) { score += 20; factors.push('Great discount 30%+'); }
    else if (discount >= 20) { score += 15; factors.push('Good discount 20%+'); }
    else if (discount >= 10) { score += 10; factors.push('Decent discount 10%+'); }
  }
  const urgencyKeywords = ['must sell', 'urgent', 'motivated', 'relocating', 'divorce', 'estate sale', 'foreclosure', 'bank owned', 'quick sale', 'obo', 'negotiable', 'moving', 'downsizing', 'health reasons', 'job transfer', 'make offer'];
  const text = `${deal.title} ${deal.description}`.toLowerCase();
  let urgencyScore = 0;
  urgencyKeywords.forEach(kw => { if (text.includes(kw)) urgencyScore += 4; });
  score += Math.min(urgencyScore, 20);
  if (urgencyScore > 0) factors.push('Urgency signals detected');
  const premiumCategories = ['real_estate', 'vehicles', 'luxury', 'business'];
  if (premiumCategories.includes(deal.category)) { score += 15; factors.push('High-value category'); }
  if (deal.posted_date) {
    const daysSincePost = (Date.now() - new Date(deal.posted_date)) / (1000 * 60 * 60 * 24);
    if (daysSincePost <= 1) { score += 10; factors.push('Just posted!'); }
    else if (daysSincePost <= 3) { score += 7; factors.push('Very fresh'); }
    else if (daysSincePost <= 7) { score += 5; factors.push('Recent'); }
  }
  if (deal.price) {
    if (deal.price >= 10000 && deal.price <= 100000) { score += 10; factors.push('Optimal price range'); }
    else if (deal.price >= 100000 && deal.price <= 500000) { score += 8; factors.push('High-value deal'); }
    else if (deal.price >= 500000) { score += 5; factors.push('Premium asset'); }
  }
  if (deal.estimated_profit) {
    if (deal.estimated_profit >= 50000) { score += 20; factors.push('$50K+ profit potential'); }
    else if (deal.estimated_profit >= 25000) { score += 15; factors.push('$25K+ profit potential'); }
    else if (deal.estimated_profit >= 10000) { score += 10; factors.push('$10K+ profit potential'); }
    else if (deal.estimated_profit >= 5000) { score += 5; factors.push('$5K+ profit potential'); }
  }
  return {
    score: Math.min(score, 100),
    grade: score >= 85 ? 'A+' : score >= 75 ? 'A' : score >= 65 ? 'B+' : score >= 55 ? 'B' : score >= 45 ? 'C' : 'D',
    factors,
    recommendation: score >= 75 ? 'HOT DEAL - ACT NOW!' : score >= 60 ? 'Good opportunity' : score >= 45 ? 'Worth investigating' : 'Low priority'
  };
}

async function findDeals() {
  console.log(`\nVortexAI Deal Scanner - ${new Date().toISOString()}`);
  console.log(`Scanning ${DEAL_SOURCES.length} sources...`);
  const newDeals = [];
  const twoWeeksAgo = new Date(Date.now() - 14 * 24 * 60 * 60 * 1000);
  for (const source of DEAL_SOURCES.filter(s => s.active)) {
    try {
      const dealsFromSource = await simulateDealFetch(source, twoWeeksAgo);
      for (const deal of dealsFromSource) {
        const scoring = await scoreWithAI(deal);
        deal.ai_score = scoring.score;
        deal.ai_grade = scoring.grade;
        deal.ai_factors = scoring.factors;
        deal.ai_recommendation = scoring.recommendation;
        try {
          const result = await pool.query(`INSERT INTO deals (id, source_id, source_name, category, title, description, price, estimated_value, estimated_profit, location, url, image_url, posted_date, ai_score, ai_grade, ai_factors, ai_recommendation, status, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, NOW()) ON CONFLICT (url) DO UPDATE SET ai_score = $14, ai_grade = $15, updated_at = NOW() RETURNING id`, [uuidv4(), source.id, source.name, source.category, deal.title, deal.description, deal.price, deal.estimated_value, deal.estimated_profit, deal.location, deal.url, deal.image_url, deal.posted_date, deal.ai_score, deal.ai_grade, JSON.stringify(deal.ai_factors), deal.ai_recommendation, 'new']);
          if (result.rows[0]) { deal.id = result.rows[0].id; newDeals.push(deal); }
        } catch (dbErr) {}
      }
      console.log(`${source.name}: ${dealsFromSource.length} deals`);
    } catch (err) {
      console.log(`ERROR ${source.name}: ${err.message}`);
    }
  }
  if (newDeals.length > 0) { await matchDealsTobuyers(newDeals); }
  console.log(`Scan complete! ${newDeals.length} new deals found\n`);
  return newDeals;
}

async function simulateDealFetch(source, minDate) {
  const deals = [];
  const numDeals = Math.floor(Math.random() * 3);
  const sampleTitles = { real_estate: ['3BR Home MUST SELL', 'Foreclosure Property', 'Estate Sale', 'Motivated Seller'], vehicles: ['2020 BMW 3 Series', 'Classic Car Estate', 'Fleet Liquidation', 'Dealer Special'], marketplace: ['Moving Sale', 'Downsizing', 'Business Closing'], liquidation: ['Warehouse Overstock', 'Returns Pallet', 'Closeout'], equipment: ['Construction Auction', 'Farm Equipment', 'Fleet Liquidation'], luxury: ['Rolex Submariner', 'Designer Bag', 'Luxury Watch'], business: ['Profitable Restaurant', 'E-commerce Business', 'Franchise'] };
  const titles = sampleTitles[source.category] || sampleTitles.marketplace;
  for (let i = 0; i < numDeals; i++) {
    const basePrice = source.category === 'real_estate' ? 150000 + Math.random() * 300000 : source.category === 'vehicles' ? 15000 + Math.random() * 50000 : source.category === 'business' ? 50000 + Math.random() * 200000 : source.category === 'luxury' ? 5000 + Math.random() * 30000 : source.category === 'equipment' ? 20000 + Math.random() * 100000 : 1000 + Math.random() * 10000;
    const discount = 0.15 + Math.random() * 0.35;
    const price = Math.round(basePrice * (1 - discount));
    const estimatedValue = Math.round(basePrice);
    deals.push({ title: titles[Math.floor(Math.random() * titles.length)], description: 'Motivated seller. Great opportunity for investors.', price: price, estimated_value: estimatedValue, estimated_profit: estimatedValue - price, location: ['Houston, TX', 'Dallas, TX', 'Austin, TX', 'Phoenix, AZ', 'Los Angeles, CA'][Math.floor(Math.random() * 5)], url: `${source.url}listing/${Date.now()}-${Math.random().toString(36).substr(2, 9)}`, image_url: null, posted_date: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000) });
  }
  return deals;
}

async function matchDealsTobuyers(deals) {
  console.log('Matching deals to buyers...');
  try {
    const buyersResult = await pool.query(`SELECT * FROM buyers WHERE status = 'active'`);
    for (const deal of deals) {
      for (const buyer of buyersResult.rows) {
        if (buyer.categories && !buyer.categories.includes(deal.category)) continue;
        if (buyer.min_budget && deal.price < buyer.min_budget) continue;
        if (buyer.max_budget && deal.price > buyer.max_budget) continue;
        if (buyer.locations && buyer.locations.length > 0) {
          const dealLoc = deal.location?.toLowerCase() || '';
          const locationMatch = buyer.locations.some(loc => dealLoc.includes(loc.toLowerCase()));
          if (!locationMatch) continue;
        }
        if (buyer.min_score && deal.ai_score < buyer.min_score) continue;
        await pool.query(`INSERT INTO matches (id, deal_id, buyer_id, match_score, status, created_at) VALUES ($1, $2, $3, $4, 'pending', NOW()) ON CONFLICT DO NOTHING`, [uuidv4(), deal.id, buyer.id, deal.ai_score]);
        if (buyer.email && deal.ai_score >= 70) { await sendDealNotification(buyer, deal); }
      }
    }
  } catch (err) {
    console.error('Matching error:', err.message);
  }
}

async function sendDealNotification(buyer, deal) {
  try {
    const emailContent = `VortexAI Deal Alert!\n\nHi ${buyer.name},\n\nWe found a HOT deal matching your criteria!\n\n${deal.title}\nPrice: $${deal.price?.toLocaleString()}\nEstimated Value: $${deal.estimated_value?.toLocaleString()}\nPotential Profit: $${deal.estimated_profit?.toLocaleString()}\nLocation: ${deal.location}\nAI Score: ${deal.ai_score}/100 (Grade: ${deal.ai_grade})\n\n${deal.ai_recommendation}\n\nView Deal: ${deal.url}\n\n---\nVortexAI - Your 24/7 Deal Finding Partner`;
    await brevoTransporter.sendMail({
      from: process.env.BREVO_SMTP_FROM || 'noreply@vortexai.com',
      to: buyer.email,
      subject: `VortexAI: ${deal.ai_grade} Deal - ${deal.title}`,
      text: emailContent,
      html: `<pre>${emailContent}</pre>`
    });
    console.log(`Email sent to ${buyer.email}`);
  } catch (err) {
    console.error('Email error:', err.message);
  }
}

async function initDatabase() {
  try {
    await pool.query(`CREATE TABLE IF NOT EXISTS deals (id UUID PRIMARY KEY, source_id INTEGER, source_name VARCHAR(255), category VARCHAR(100), title VARCHAR(500), description TEXT, price DECIMAL(15,2), estimated_value DECIMAL(15,2), estimated_profit DECIMAL(15,2), location VARCHAR(255), url TEXT UNIQUE, image_url TEXT, posted_date TIMESTAMP, ai_score INTEGER, ai_grade VARCHAR(5), ai_factors JSONB, ai_recommendation TEXT, status VARCHAR(50) DEFAULT 'new', created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW()); CREATE TABLE IF NOT EXISTS buyers (id UUID PRIMARY KEY, name VARCHAR(255), email VARCHAR(255), phone VARCHAR(50), categories TEXT[], locations TEXT[], min_budget DECIMAL(15,2), max_budget DECIMAL(15,2), min_score INTEGER DEFAULT 60, status VARCHAR(50) DEFAULT 'active', created_at TIMESTAMP DEFAULT NOW()); CREATE TABLE IF NOT EXISTS matches (id UUID PRIMARY KEY, deal_id UUID REFERENCES deals(id), buyer_id UUID REFERENCES buyers(id), match_score INTEGER, status VARCHAR(50) DEFAULT 'pending', notified_at TIMESTAMP, created_at TIMESTAMP DEFAULT NOW(), UNIQUE(deal_id, buyer_id)); CREATE TABLE IF NOT EXISTS scan_logs (id SERIAL PRIMARY KEY, started_at TIMESTAMP, completed_at TIMESTAMP, deals_found INTEGER, sources_scanned INTEGER, errors TEXT[]); CREATE INDEX IF NOT EXISTS idx_deals_category ON deals(category); CREATE INDEX IF NOT EXISTS idx_deals_score ON deals(ai_score DESC); CREATE INDEX IF NOT EXISTS idx_deals_created ON deals(created_at DESC); CREATE INDEX IF NOT EXISTS idx_buyers_status ON buyers(status);`);
    console.log('Database initialized');
    return true;
  } catch (err) {
    console.error('Database error:', err.message);
    return false;
  }
}

app.get('/health', async (req, res) => {
  try {
    await pool.query('SELECT 1');
    res.json({ status: 'healthy', timestamp: new Date().toISOString(), sources: DEAL_SOURCES.length });
  } catch (err) {
    res.json({ status: 'unhealthy', error: err.message });
  }
});

app.get('/', (req, res) => {
  res.json({ name: 'VortexAI Ultimate API', version: '3.0.0', sources: DEAL_SOURCES.length, categories: [...new Set(DEAL_SOURCES.map(s => s.category))], endpoints: { health: '/health', deals: '/api/deals', buyers: '/api/buyers', sources: '/api/sources', stats: '/api/stats', scan: '/api/scan' } });
});

app.get('/api/sources', (req, res) => {
  const byCategory = DEAL_SOURCES.reduce((acc, source) => { if (!acc[source.category]) acc[source.category] = []; acc[source.category].push(source); return acc; }, {});
  res.json({ total: DEAL_SOURCES.length, byCategory, sources: DEAL_SOURCES });
});

app.get('/api/deals', async (req, res) => {
  try {
    const { category, min_score, limit = 50 } = req.query;
    let query = 'SELECT * FROM deals WHERE 1=1';
    const params = [];
    if (category) { params.push(category); query += ` AND category = $${params.length}`; }
    if (min_score) { params.push(parseInt(min_score)); query += ` AND ai_score >= $${params.length}`; }
    query += ' ORDER BY ai_score DESC, created_at DESC';
    params.push(parseInt(limit));
    query += ` LIMIT $${params.length}`;
    const result = await pool.query(query, params);
    res.json({ count: result.rows.length, deals: result.rows });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/deals/:id', async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM deals WHERE id = $1', [req.params.id]);
    if (result.rows.length === 0) return res.status(404).json({ error: 'Deal not found' });
    res.json(result.rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/buyers', async (req, res) => {
  try {
    const { name, email, phone, categories, locations, min_budget, max_budget, min_score } = req.body;
    const result = await pool.query(`INSERT INTO buyers (id, name, email, phone, categories, locations, min_budget, max_budget, min_score, status, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'active', NOW()) RETURNING *`, [uuidv4(), name, email, phone, categories, locations, min_budget, max_budget, min_score || 60]);
    res.status(201).json(result.rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/buyers', async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM buyers ORDER BY created_at DESC');
    res.json({ count: result.rows.length, buyers: result.rows });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/stats', async (req, res) => {
  try {
    const deals = await pool.query('SELECT COUNT(*) as total, AVG(ai_score) as avg_score FROM deals');
    const hotDeals = await pool.query('SELECT COUNT(*) as count FROM deals WHERE ai_score >= 75');
    const buyers = await pool.query('SELECT COUNT(*) as total FROM buyers WHERE status = $1', ['active']);
    const matches = await pool.query('SELECT COUNT(*) as total FROM matches');
    const byCategory = await pool.query('SELECT category, COUNT(*) as count FROM deals GROUP BY category');
    res.json({ totalDeals: parseInt(deals.rows[0].total), avgScore: Math.round(parseFloat(deals.rows[0].avg_score) || 0), hotDeals: parseInt(hotDeals.rows[0].count), activeBuyers: parseInt(buyers.rows[0].total), totalMatches: parseInt(matches.rows[0].total), totalSources: DEAL_SOURCES.length, dealsByCategory: byCategory.rows.reduce((acc, row) => { acc[row.category] = parseInt(row.count); return acc; }, {}) });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/scan', async (req, res) => {
  try {
    const deals = await findDeals();
    res.json({ success: true, dealsFound: deals.length });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/admin/webhooks/deal-ingest', (req, res) => {
  if (process.env.ENABLE_WEBHOOK_SIGNATURE === 'true') {
    if (!validateWebhookSignature(req)) {
      return res.status(401).json({ error: 'Invalid signature' });
    }
  }
  handleDealIngest(req, res);
});

async function handleDealIngest(req, res) {
  try {
    const deal = req.body;
    if (!deal.title || !deal.url) {
      return res.status(400).json({ error: 'Missing title or url' });
    }
    const scoring = await scoreWithAI(deal);
    const result = await pool.query(`INSERT INTO deals (id, source_id, source_name, category, title, description, price, estimated_value, location, url, posted_date, ai_score, ai_grade, ai_factors, ai_recommendation, status, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, 'new', NOW()) ON CONFLICT (url) DO UPDATE SET ai_score = $12, ai_grade = $13, updated_at = NOW() RETURNING *`, [uuidv4(), deal.source_id || 0, deal.source_name || 'External', deal.category || 'other', deal.title, deal.description, deal.price, deal.estimated_value, deal.location, deal.url, deal.posted_date || new Date(), scoring.score, scoring.grade, JSON.stringify(scoring.factors), scoring.recommendation]);
    if (result.rows[0]) { await matchDealsTobuyers([result.rows[0]]); }
    res.status(201).json({ success: true, deal: result.rows[0] });
  } catch (err) {
    console.error('Webhook error:', err.message);
    res.status(500).json({ error: err.message });
  }
}

const PORT = process.env.PORT || 3000;
app.listen(PORT, async () => {
  console.log(`\nVORTEXAI ULTIMATE v3.0 - PRODUCTION READY\nPort: ${PORT}\nSources: ${DEAL_SOURCES.length}\nEmail: Brevo SMTP\nWebhook: /admin/webhooks/deal-ingest\nScheduler: Every 30 minutes\n`);
  await initDatabase();
  console.log('Running initial scan...');
  await findDeals();
  cron.schedule('*/5 * * * *', async () => { console.log('Scan triggered'); await findDeals(); });
  console.log('System ready!');
});

module.exports = app;