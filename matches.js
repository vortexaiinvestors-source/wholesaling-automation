const express = require('express');
const router = express.Router();
const { query } = require('../config/database');

/**
 * GET /api/matches - Get all matches
 */
router.get('/', async (req, res) => {
  try {
    const { status, min_score } = req.query;
    
    let queryText = 'SELECT * FROM matches WHERE 1=1';
    const params = [];
    let paramCount = 1;

    if (status) {
      queryText += ` AND status = $${paramCount}`;
      params.push(status);
      paramCount++;
    }

    if (min_score) {
      queryText += ` AND match_score >= $${paramCount}`;
      params.push(parseInt(min_score));
      paramCount++;
    }

    queryText += ' ORDER BY match_score DESC, created_at DESC LIMIT 100';
    
    const result = await query(queryText, params);

    res.json({
      matches: result.rows,
      count: result.rows.length
    });
  } catch (error) {
    console.error('Error fetching matches:', error);
    res.status(500).json({ error: 'Failed to fetch matches' });
  }
});

/**
 * PUT /api/matches/:id - Update match status
 */
router.put('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const { status, notes } = req.body;

    const updates = [];
    const values = [];
    let paramCount = 1;

    if (status) {
      updates.push(`status = $${paramCount}`);
      values.push(status);
      paramCount++;

      // Update timestamp based on status
      if (status === 'viewed') {
        updates.push(`viewed_at = CURRENT_TIMESTAMP`);
      } else if (status === 'interested') {
        updates.push(`interested_at = CURRENT_TIMESTAMP`);
      } else if (status === 'rejected') {
        updates.push(`rejected_at = CURRENT_TIMESTAMP`);
      }
    }

    if (notes) {
      updates.push(`notes = $${paramCount}`);
      values.push(notes);
      paramCount++;
    }

    if (updates.length === 0) {
      return res.status(400).json({ error: 'No fields to update' });
    }

    values.push(id);
    const queryText = `UPDATE matches SET ${updates.join(', ')}, updated_at = CURRENT_TIMESTAMP WHERE id = $${paramCount} RETURNING *`;

    const result = await query(queryText, values);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Match not found' });
    }

    res.json(result.rows[0]);
  } catch (error) {
    console.error('Error updating match:', error);
    res.status(500).json({ error: 'Failed to update match' });
  }
});

/**
 * POST /api/matches/:id/track - Track buyer interaction
 */
router.post('/:id/track', async (req, res) => {
  try {
    const { id } = req.params;
    const { action } = req.body; // 'view', 'click', 'interest', 'reject'

    let updateField = '';
    switch(action) {
      case 'view':
        updateField = 'viewed_at = CURRENT_TIMESTAMP, status = \'viewed\'';
        break;
      case 'interest':
        updateField = 'interested_at = CURRENT_TIMESTAMP, status = \'interested\'';
        break;
      case 'reject':
        updateField = 'rejected_at = CURRENT_TIMESTAMP, status = \'rejected\'';
        break;
      default:
        return res.status(400).json({ error: 'Invalid action' });
    }

    const result = await query(
      `UPDATE matches SET ${updateField} WHERE id = $1 RETURNING *`,
      [id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Match not found' });
    }

    res.json({ 
      message: 'Interaction tracked',
      match: result.rows[0]
    });
  } catch (error) {
    console.error('Error tracking interaction:', error);
    res.status(500).json({ error: 'Failed to track interaction' });
  }
});

module.exports = router;
