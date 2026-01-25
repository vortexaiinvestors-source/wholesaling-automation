require('dotenv').config();
const express = require('express');
const cors = require('cors');
const { Pool } = require('pg');
const cron = require('node-cron');
const axios = require('axios');
const nodemailer = require('nodemailer');
const { v4: uuidv4 } = require('uuid');

const app = express();
app.use(cors());
app.use(express.json());

// Database connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
});

// ============================================
// 50+ DEAL SOURCES CONFIGURATION
// ============================================
const DEAL_SOURCES = [
  // REAL ESTATE (15 sources)
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
  { id: 11, name: 'HomePath (Fannie Mae)', category: 'real_estate', url: 'https://www.homepath.com/', active: true },
  { id: 12, name: 'HomeSteps (Freddie Mac)', category: 'real_estate', url: 'https://www.homesteps.com/', active: true },
  { id: 13, name: 'Xome', category: 'real_estate', url: 'https://www.xome.com/', active: true },
  { id: 14, name: 'RealtyBid', category: 'real_estate', url: 'https://www.realtybid.com/', active: true },
  { id: 15, name: 'PropertyShark', category: 'real_estate', url: 'https://www.propertyshark.com/', active: true },

  // VEHICLES (12 sources)
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

  // MARKETPLACES (10 sources)
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

  // LIQUIDATION & WHOLESALE (10 sources)
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

  // EQUIPMENT & MACHINERY (8 sources)
  { id: 48, name: 'IronPlanet', category: 'equipment', url: 'https://www.ironplanet.com/', active: true },
  { id: 49, name: 'Ritchie Bros', category: 'equipment', url: 'https://www.rbauction.com/', active: true },
  { id: 50, name: 'MachineryTrader', category: 'equipment', url: 'https://www.machinerytrader.com/', active: true },
  { id: 51, name: 'EquipmentTrader', category: 'equipment', url: 'https://www.equipmenttrader.com/', active: true },
  { id: 52, name: 'Mascus', category: 'equipment', url: 'https://www.mascus.com/', active: true },
  { id: 53, name: 'TractorHouse', category: 'equipment', url: 'https://www.tractorhouse.com/', active: true },
  { id: 54, name: 'Rock & Dirt', category: 'equipment', url: 'https://www.rockanddirt.com/', active: true },
  { id: 55, name: 'Truck Paper', category: 'equipment', url: 'https://www.truckpaper.com/', active: true },

  // LUXURY ITEMS (5 sources)
  { id: 56, name: 'Chrono24', category: 'luxury', url: 'https://www.chrono24.com/', active: true },
  { id: 57, name: 'The RealReal', category: 'luxury', url: 'https://www.therealreal.com/', active: true },
  { id: 58, name: 'Vestiaire Collective', category: 'luxury', url: 'https://www.vestiairecollective.com/', active: true },
  { id: 59, name: 'Rebag', category: 'luxury', url: 'https://www.rebag.com/', active: true },
  { id: 60, name: 'StockX', category: 'luxury', url: 'https://stockx.com/', active: true },

  // BUSINESS & COMMERCIAL (5 sources)
  { id: 61, name: 'BizBuySell', category: 'business', url: 'https://www.bizbuysell.com/', active: true },
  { id: 62, name: 'BusinessBroker.net', category: 'business', url: 'https://www.businessbroker.net/', active: true },
  { id: 63, name: 'LoopNet', category: 'business', url: 'https://www.loopnet.com/', active: true },
  { id: 64, name: 'CREXi', category: 'business', url: 'https://www.crexi.com/', active: true }
];

// ============================================
// AI SCORING ENGINE
// ============================================
async function scoreWithAI(deal) {
  let score = 55; // Base score (increased from 50)
  const factors = [];

  // Price Analysis (0-35 points) - INCREASED
  if (deal.price && deal.estimated_value) {
    const discount = ((deal.estimated_value - deal.price) / deal.estimated_value) * 100;
    if (discount >= 40) { score += 35; factors.push('MASSIVE discount 40%+'); }
    else if (discount >= 30) { score += 28; factors.push('Great discount 30%+'); }
    else if (discount >= 20) { score += 20; factors.push('Good discount 20%+'); }
    else if (discount >= 10) { score += 12; factors.push('Decent discount 10%+'); }
    else { score += 5; factors.push('Listed price'); } // Give points even for no discount
  }

  // Urgency Keywords (0-25 points) - INCREASED
  const urgencyKeywords = ['must sell', 'urgent', 'motivated', 'relocating', 'divorce', 
    'estate sale', 'foreclosure', 'bank owned', 'quick sale', 'obo', 'negotiable',
    'moving', 'downsizing', 'health reasons', 'job transfer', 'make offer', 'investment', 
    'opportunity', 'great deal', 'hot deal'];
  const text = `${deal.title} ${deal.description}`.toLowerCase();
  let urgencyScore = 0;
  urgencyKeywords.forEach(kw => {
    if (text.includes(kw)) urgencyScore += 3;
  });
  score += Math.min(urgencyScore, 25); // Increased max from 20 to 25
  if (urgencyScore > 0) factors.push('Urgency signals detected');
  else { score += 8; factors.push('Standard deal opportunity'); } // Give points even if no urgency keywords

  // Category Premium (0-20 points) - INCREASED
  const premiumCategories = ['real_estate', 'vehicles', 'luxury', 'business'];
  if (premiumCategories.includes(deal.category)) {
    score += 20;
    factors.push('High-value category');
  } else {
    score += 10; // Bonus for other categories too
    factors.push('Quality marketplace deal');
  }

  // Recency (0-15 points) - INCREASED
  if (deal.posted_date) {
    const daysSincePost = (Date.now() - new Date(deal.posted_date)) / (1000 * 60 * 60 * 24);
    if (daysSincePost <= 1) { score += 15; factors.push('Just posted!'); }
    else if (daysSincePost <= 3) { score += 10; factors.push('Very fresh'); }
    else if (daysSincePost <= 7) { score += 8; factors.push('Recent'); }
  } else {
    score += 5; // Give points if no date (assume recent)
  }

  // Price Sweet Spots (0-15 points) - INCREASED
  if (deal.price) {
    if (deal.price >= 10000 && deal.price <= 100000) { score += 15; factors.push('Optimal price range'); }
    else if (deal.price >= 100000 && deal.price <= 500000) { score += 12; factors.push('High-value deal'); }
    else if (deal.price >= 500000) { score += 8; factors.push('Premium asset'); }
    else { score += 5; factors.push('Attractive price point'); } // Bonus even for lower prices
  }

  // Profit Potential (0-25 points) - INCREASED
  if (deal.estimated_profit) {
    if (deal.estimated_profit >= 50000) { score += 25; factors.push('$50K+ profit potential'); }
    else if (deal.estimated_profit >= 25000) { score += 20; factors.push('$25K+ profit potential'); }
    else if (deal.estimated_profit >= 10000) { score += 15; factors.push('$10K+ profit potential'); }
    else if (deal.estimated_profit >= 5000) { score += 10; factors.push('$5K+ profit potential'); }
    else if (deal.estimated_profit > 0) { score += 5; factors.push('Has profit margin'); }
  }

  return {
    score: Math.min(score, 100),
    grade: score >= 85 ? 'A+' : score >= 75 ? 'A' : score >= 65 ? 'B+' : score >= 55 ? 'B' : score >= 45 ? 'C' : 'D',
    factors,
    recommendation: score >= 75 ? 'HOT DEAL - ACT NOW!' : score >= 60 ? 'Good opportunity' : score >= 45 ? 'Worth investigating' : 'Low priority'
  };
}

// Continue with rest of server code...
