import express from 'express';
import { Pool } from 'pg';

const router = express.Router();
const pool = new Pool({ connectionString: process.env.DATABASE_URL });

// Get all categories
router.get('/', async (req, res) => {
  try {
    const result = await pool.query(
      'SELECT * FROM asset_categories ORDER BY name'
    );
    res.json({
      success: true,
      count: result.rowCount,
      categories: result.rows,
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Get category by ID
router.get('/:id', async (req, res) => {
  try {
    const result = await pool.query(
      'SELECT * FROM asset_categories WHERE id = $1',
      [req.params.id]
    );
    if (result.rowCount === 0) {
      return res.status(404).json({ success: false, error: 'Category not found' });
    }
    res.json({ success: true, category: result.rows[0] });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Create new category (admin only)
router.post('/', async (req, res) => {
  const { name, description, icon } = req.body;
  
  if (!name) {
    return res.status(400).json({ success: false, error: 'Category name required' });
  }

  try {
    const result = await pool.query(
      'INSERT INTO asset_categories (name, description, icon) VALUES ($1, $2, $3) RETURNING *',
      [name, description || null, icon || null]
    );
    res.status(201).json({
      success: true,
      category: result.rows[0],
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Update category (admin only)
router.patch('/:id', async (req, res) => {
  const { name, description, icon } = req.body;

  try {
    const result = await pool.query(
      'UPDATE asset_categories SET name = COALESCE($1, name), description = COALESCE($2, description), icon = COALESCE($3, icon) WHERE id = $4 RETURNING *',
      [name, description, icon, req.params.id]
    );
    if (result.rowCount === 0) {
      return res.status(404).json({ success: false, error: 'Category not found' });
    }
    res.json({ success: true, category: result.rows[0] });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Delete category (admin only)
router.delete('/:id', async (req, res) => {
  try {
    const result = await pool.query(
      'DELETE FROM asset_categories WHERE id = $1 RETURNING *',
      [req.params.id]
    );
    if (result.rowCount === 0) {
      return res.status(404).json({ success: false, error: 'Category not found' });
    }
    res.json({ success: true, message: 'Category deleted' });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Get category statistics
router.get('/:id/stats', async (req, res) => {
  try {
    const result = await pool.query(
      `SELECT 
        ac.id, ac.name,
        COUNT(d.id) as total_deals,
        COUNT(CASE WHEN d.deal_status = 'matched' THEN 1 END) as matched_deals,
        AVG(d.ai_score) as avg_score,
        MIN(d.asking_price) as min_price,
        MAX(d.asking_price) as max_price
      FROM asset_categories ac
      LEFT JOIN deals d ON ac.id = d.asset_category_id
      WHERE ac.id = $1
      GROUP BY ac.id, ac.name`,
      [req.params.id]
    );
    if (result.rowCount === 0) {
      return res.status(404).json({ success: false, error: 'Category not found' });
    }
    res.json({ success: true, stats: result.rows[0] });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

export default router;