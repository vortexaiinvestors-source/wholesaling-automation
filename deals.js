const express = require('express');
const router = express.Router();
const { query } = require('../config/database');
const { calculateDealScore, estimateMarketValue } = require('../services/aiScoring');
const { findMatchingBuyers, createMatches } = require('../services/buyerMatcher');
const { notifyBuyer } = require('../services/notifications');

/**
 * GET /api/deals - Get all deals
 */
router.get('/', async (req, res) => {
  try {
    const { category, min_score, status, limit = 50, offset = 0 } = req.query;
    
    let queryText = 'SELECT * FROM deals WHERE 1=1';
    const params = [];
    let paramCount = 1;

    if (category) {
      queryText += ` AND category = $${paramCount}`;
      params.push(category);
      paramCount++;
    }

    if (min_score) {
      queryText += ` AND ai_score >= $${paramCount}`;
      params.push(parseInt(min_score));
      paramCount++;
    }

    if (status) {
      queryText += ` AND status = $${paramCount}`;
      params.push(status);
      paramCount++;
    }

    queryText += ` ORDER BY ai_score DESC, created_at DESC LIMIT $${paramCount} OFFSET $${paramCount + 1}`;
    params.push(parseInt(limit), parseInt(offset));

    const result = await query(queryText, params);

    res.json({
      deals: result.rows,
      count: result.rows.length,
      limit: parseInt(limit),
      offset: parseInt(offset)
    });
  } catch (error) {
    console.error('Error fetching deals:', error);
    res.status(500).json({ error: 'Failed to fetch deals' });
  }
});

/**
 * GET /api/deals/:id - Get single deal
 */
router.get('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const result = await query('SELECT * FROM deals WHERE id = $1', [id]);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Deal not found' });
    }

    res.json(result.rows[0]);
  } catch (error) {
    console.error('Error fetching deal:', error);
    res.status(500).json({ error: 'Failed to fetch deal' });
  }
});

/**
 * POST /api/deals - Create new deal
 */
router.post('/', async (req, res) => {
  try {
    const {
      title,
      description,
      price,
      market_value,
      category,
      location,
      source,
      source_url,
      image_url,
      contact_info
    } = req.body;

    // Validate required fields
    if (!title || !price || !category || !source) {
      return res.status(400).json({ 
        error: 'Missing required fields: title, price, category, source' 
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
    const result = await query(
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

    const deal = result.rows[0];

    // Find and create matches
    if (scoreResult.score >= 60) {
      const matches = await findMatchingBuyers(deal);
      if (matches.length > 0) {
        await createMatches(deal, matches);
        
        // Notify top matches
        for (const match of matches.slice(0, 10)) {
          try {
            const buyerResult = await query('SELECT * FROM buyers WHERE id = $1', [match.buyer_id]);
            if (buyerResult.rows.length > 0) {
              await notifyBuyer(match, deal, buyerResult.rows[0]);
            }
          } catch (notifyError) {
            console.error('Error notifying buyer:', notifyError);
          }
        }
      }
    }

    res.status(201).json({
      deal,
      score: scoreResult.score,
      matches_found: 0
    });
  } catch (error) {
    console.error('Error creating deal:', error);
    res.status(500).json({ error: 'Failed to create deal' });
  }
});

/**
 * PUT /api/deals/:id - Update deal
 */
router.put('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const updates = req.body;

    // Build dynamic update query
    const fields = [];
    const values = [];
    let paramCount = 1;

    Object.keys(updates).forEach(key => {
      if (updates[key] !== undefined) {
        fields.push(`${key} = $${paramCount}`);
        values.push(updates[key]);
        paramCount++;
      }
    });

    if (fields.length === 0) {
      return res.status(400).json({ error: 'No fields to update' });
    }

    values.push(id);
    const queryText = `UPDATE deals SET ${fields.join(', ')}, updated_at = CURRENT_TIMESTAMP WHERE id = $${paramCount} RETURNING *`;

    const result = await query(queryText, values);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Deal not found' });
    }

    res.json(result.rows[0]);
  } catch (error) {
    console.error('Error updating deal:', error);
    res.status(500).json({ error: 'Failed to update deal' });
  }
});

/**
 * DELETE /api/deals/:id - Delete deal
 */
router.delete('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const result = await query('DELETE FROM deals WHERE id = $1 RETURNING *', [id]);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Deal not found' });
    }

    res.json({ message: 'Deal deleted successfully' });
  } catch (error) {
    console.error('Error deleting deal:', error);
    res.status(500).json({ error: 'Failed to delete deal' });
  }
});

/**
 * GET /api/deals/:id/matches - Get matches for a deal
 */
router.get('/:id/matches', async (req, res) => {
  try {
    const { id } = req.params;
    
    const result = await query(
      `SELECT m.*, b.name as buyer_name, b.email as buyer_email 
       FROM matches m
       JOIN buyers b ON m.buyer_id = b.id
       WHERE m.deal_id = $1
       ORDER BY m.match_score DESC`,
      [id]
    );

    res.json({ matches: result.rows });
  } catch (error) {
    console.error('Error fetching matches:', error);
    res.status(500).json({ error: 'Failed to fetch matches' });
  }
});

module.exports = router;
