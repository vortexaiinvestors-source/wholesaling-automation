const express = require('express');
const router = express.Router();
const { query } = require('../config/database');

/**
 * GET /api/buyers - Get all buyers
 */
router.get('/', async (req, res) => {
  try {
    const { is_active, subscription_tier } = req.query;
    
    let queryText = 'SELECT * FROM buyers WHERE 1=1';
    const params = [];
    let paramCount = 1;

    if (is_active !== undefined) {
      queryText += ` AND is_active = $${paramCount}`;
      params.push(is_active === 'true');
      paramCount++;
    }

    if (subscription_tier) {
      queryText += ` AND subscription_tier = $${paramCount}`;
      params.push(subscription_tier);
      paramCount++;
    }

    queryText += ' ORDER BY created_at DESC';
    
    const result = await query(queryText, params);

    res.json({
      buyers: result.rows,
      count: result.rows.length
    });
  } catch (error) {
    console.error('Error fetching buyers:', error);
    res.status(500).json({ error: 'Failed to fetch buyers' });
  }
});

/**
 * GET /api/buyers/:id - Get single buyer
 */
router.get('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const result = await query('SELECT * FROM buyers WHERE id = $1', [id]);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Buyer not found' });
    }

    res.json(result.rows[0]);
  } catch (error) {
    console.error('Error fetching buyer:', error);
    res.status(500).json({ error: 'Failed to fetch buyer' });
  }
});

/**
 * POST /api/buyers - Create new buyer (signup)
 */
router.post('/', async (req, res) => {
  try {
    const {
      name,
      email,
      phone,
      preferences,
      budget_min,
      budget_max,
      locations,
      categories,
      subscription_tier = 'free'
    } = req.body;

    // Validate required fields
    if (!name || !email) {
      return res.status(400).json({ 
        error: 'Missing required fields: name, email' 
      });
    }

    // Check if email already exists
    const existing = await query('SELECT id FROM buyers WHERE email = $1', [email]);
    if (existing.rows.length > 0) {
      return res.status(409).json({ 
        error: 'Email already registered',
        buyer_id: existing.rows[0].id
      });
    }

    // Insert buyer
    const result = await query(
      `INSERT INTO buyers (
        name, email, phone, preferences, 
        budget_min, budget_max, locations, categories, subscription_tier
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
      RETURNING *`,
      [
        name,
        email,
        phone,
        preferences ? JSON.stringify(preferences) : null,
        budget_min,
        budget_max,
        locations,
        categories,
        subscription_tier
      ]
    );

    res.status(201).json({
      message: 'Buyer created successfully',
      buyer: result.rows[0]
    });
  } catch (error) {
    console.error('Error creating buyer:', error);
    res.status(500).json({ error: 'Failed to create buyer' });
  }
});

/**
 * PUT /api/buyers/:id - Update buyer preferences
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
        if (key === 'preferences' && typeof updates[key] === 'object') {
          fields.push(`${key} = $${paramCount}`);
          values.push(JSON.stringify(updates[key]));
        } else {
          fields.push(`${key} = $${paramCount}`);
          values.push(updates[key]);
        }
        paramCount++;
      }
    });

    if (fields.length === 0) {
      return res.status(400).json({ error: 'No fields to update' });
    }

    values.push(id);
    const queryText = `UPDATE buyers SET ${fields.join(', ')}, updated_at = CURRENT_TIMESTAMP WHERE id = $${paramCount} RETURNING *`;

    const result = await query(queryText, values);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Buyer not found' });
    }

    res.json(result.rows[0]);
  } catch (error) {
    console.error('Error updating buyer:', error);
    res.status(500).json({ error: 'Failed to update buyer' });
  }
});

/**
 * DELETE /api/buyers/:id - Delete buyer
 */
router.delete('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const result = await query('DELETE FROM buyers WHERE id = $1 RETURNING *', [id]);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Buyer not found' });
    }

    res.json({ message: 'Buyer deleted successfully' });
  } catch (error) {
    console.error('Error deleting buyer:', error);
    res.status(500).json({ error: 'Failed to delete buyer' });
  }
});

/**
 * GET /api/buyers/:id/matches - Get matches for a buyer
 */
router.get('/:id/matches', async (req, res) => {
  try {
    const { id } = req.params;
    const { status, limit = 50 } = req.query;
    
    let queryText = `
      SELECT m.*, d.title, d.price, d.market_value, d.ai_score, d.category, d.location, d.image_url
      FROM matches m
      JOIN deals d ON m.deal_id = d.id
      WHERE m.buyer_id = $1
    `;
    const params = [id];

    if (status) {
      queryText += ` AND m.status = $2`;
      params.push(status);
    }

    queryText += ` ORDER BY m.match_score DESC, m.created_at DESC LIMIT $${params.length + 1}`;
    params.push(parseInt(limit));

    const result = await query(queryText, params);

    res.json({ matches: result.rows });
  } catch (error) {
    console.error('Error fetching buyer matches:', error);
    res.status(500).json({ error: 'Failed to fetch matches' });
  }
});

/**
 * POST /api/buyers/:id/unsubscribe - Unsubscribe buyer
 */
router.post('/:id/unsubscribe', async (req, res) => {
  try {
    const { id } = req.params;
    
    const result = await query(
      'UPDATE buyers SET is_active = false WHERE id = $1 RETURNING *',
      [id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Buyer not found' });
    }

    res.json({ 
      message: 'Successfully unsubscribed',
      buyer: result.rows[0]
    });
  } catch (error) {
    console.error('Error unsubscribing buyer:', error);
    res.status(500).json({ error: 'Failed to unsubscribe' });
  }
});

module.exports = router;
