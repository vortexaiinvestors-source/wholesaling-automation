const express = require('express');
const router = express.Router();
const { query } = require('../config/database');
const { calculateDealScore, estimateMarketValue } = require('../services/aiScoring');
const { findMatchingBuyers, createMatches } = require('../services/buyerMatcher');

/**
 * POST /api/webhooks/zapier - Receive deal from Zapier
 */
router.post('/zapier', async (req, res) => {
  try {
    console.log('📥 Zapier webhook received:', req.body);

    const {
      title,
      description,
      price,
      market_value,
      category,
      location,
      source = 'zapier',
      source_url,
      image_url,
      contact_info
    } = req.body;

    // Log webhook
    await query(
      'INSERT INTO webhook_logs (source, payload, processed) VALUES ($1, $2, $3)',
      ['zapier', JSON.stringify(req.body), false]
    );

    // Validate required fields
    if (!title || !price || !category) {
      return res.status(400).json({ 
        error: 'Missing required fields: title, price, category',
        success: false
      });
    }

    // Estimate market value if not provided
    let finalMarketValue = market_value;
    if (!finalMarketValue) {
      finalMarketValue = await estimateMarketValue({ category, price });
    }

    // Calculate AI score
    const scoreResult = await calculateDealScore({
      title,
      description,
      price,
      market_value: finalMarketValue,
      category,
      location,
      source
    });

    // Insert deal
    const dealResult = await query(
      `INSERT INTO deals (
        title, description, price, market_value, category, location,
        source, source_url, image_url, contact_info,
        ai_score, urgency_keywords, discount_percentage, profit_potential
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
      RETURNING *`,
      [
        title,
        description,
        price,
        finalMarketValue,
        category,
        location,
        source,
        source_url,
        image_url,
        contact_info,
        scoreResult.score,
        scoreResult.urgency_keywords,
        scoreResult.discount,
        scoreResult.profit
      ]
    );

    const deal = dealResult.rows[0];

    // Find and create matches
    let matchCount = 0;
    if (scoreResult.score >= 60) {
      const matches = await findMatchingBuyers(deal);
      if (matches.length > 0) {
        await createMatches(deal, matches);
        matchCount = matches.length;
      }
    }

    // Update webhook log
    await query(
      'UPDATE webhook_logs SET processed = true, deal_id = $1 WHERE source = $2 AND payload::text = $3',
      [deal.id, 'zapier', JSON.stringify(req.body)]
    );

    res.status(200).json({
      success: true,
      deal_id: deal.id,
      ai_score: scoreResult.score,
      matches_created: matchCount,
      message: 'Deal processed successfully'
    });
  } catch (error) {
    console.error('❌ Zapier webhook error:', error);
    res.status(500).json({ 
      success: false,
      error: 'Failed to process webhook',
      message: error.message
    });
  }
});

/**
 * POST /api/webhooks/google-forms - Receive buyer signup from Google Forms
 */
router.post('/google-forms', async (req, res) => {
  try {
    console.log('📥 Google Forms webhook received:', req.body);

    const {
      name,
      email,
      phone,
      budget_min,
      budget_max,
      locations,
      categories,
      notes
    } = req.body;

    // Log webhook
    await query(
      'INSERT INTO webhook_logs (source, payload, processed) VALUES ($1, $2, $3)',
      ['google-forms', JSON.stringify(req.body), false]
    );

    // Validate
    if (!name || !email) {
      return res.status(400).json({ 
        error: 'Missing required fields: name, email',
        success: false
      });
    }

    // Check if already exists
    const existing = await query('SELECT id FROM buyers WHERE email = $1', [email]);
    if (existing.rows.length > 0) {
      return res.status(200).json({
        success: true,
        message: 'Email already registered',
        buyer_id: existing.rows[0].id
      });
    }

    // Parse locations and categories
    const locationArray = locations ? locations.split(',').map(l => l.trim()) : [];
    const categoryArray = categories ? categories.split(',').map(c => c.trim()) : [];

    // Create buyer
    const result = await query(
      `INSERT INTO buyers (
        name, email, phone, budget_min, budget_max, locations, categories, preferences
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
      RETURNING *`,
      [
        name,
        email,
        phone,
        budget_min,
        budget_max,
        locationArray,
        categoryArray,
        notes ? JSON.stringify({ notes }) : null
      ]
    );

    res.status(201).json({
      success: true,
      buyer_id: result.rows[0].id,
      message: 'Buyer registered successfully'
    });
  } catch (error) {
    console.error('❌ Google Forms webhook error:', error);
    res.status(500).json({ 
      success: false,
      error: 'Failed to process webhook',
      message: error.message
    });
  }
});

/**
 * GET /api/webhooks/logs - Get webhook logs
 */
router.get('/logs', async (req, res) => {
  try {
    const { limit = 50 } = req.query;
    
    const result = await query(
      'SELECT * FROM webhook_logs ORDER BY created_at DESC LIMIT $1',
      [parseInt(limit)]
    );

    res.json({
      logs: result.rows,
      count: result.rows.length
    });
  } catch (error) {
    console.error('Error fetching webhook logs:', error);
    res.status(500).json({ error: 'Failed to fetch logs' });
  }
});

module.exports = router;
