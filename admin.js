const express = require('express');
const router = express.Router();
const { query } = require('../config/database');

/**
 * GET /api/admin/stats - Get dashboard statistics
 */
router.get('/stats', async (req, res) => {
  try {
    // Get counts
    const dealsCount = await query('SELECT COUNT(*) as count FROM deals');
    const buyersCount = await query('SELECT COUNT(*) as count FROM buyers WHERE is_active = true');
    const matchesCount = await query('SELECT COUNT(*) as count FROM matches');
    const interestedCount = await query('SELECT COUNT(*) as count FROM matches WHERE status = \'interested\'');

    // Get average AI score
    const avgScore = await query('SELECT AVG(ai_score) as avg FROM deals');

    // Get deals by category
    const dealsByCategory = await query(
      'SELECT category, COUNT(*) as count FROM deals GROUP BY category ORDER BY count DESC'
    );

    // Get top deals
    const topDeals = await query(
      'SELECT * FROM deals ORDER BY ai_score DESC LIMIT 10'
    );

    // Get recent activity
    const recentMatches = await query(
      `SELECT m.*, d.title, b.name as buyer_name
       FROM matches m
       JOIN deals d ON m.deal_id = d.id
       JOIN buyers b ON m.buyer_id = b.id
       ORDER BY m.created_at DESC
       LIMIT 20`
    );

    // Calculate revenue metrics (placeholder)
    const revenueMetrics = {
      total_deals_closed: 0,
      total_revenue: 0,
      average_deal_value: 0,
      monthly_recurring_revenue: buyersCount.rows[0].count * 49 // Assuming $49/month
    };

    res.json({
      stats: {
        total_deals: parseInt(dealsCount.rows[0].count),
        total_buyers: parseInt(buyersCount.rows[0].count),
        total_matches: parseInt(matchesCount.rows[0].count),
        interested_matches: parseInt(interestedCount.rows[0].count),
        average_ai_score: parseFloat(avgScore.rows[0].avg || 0).toFixed(1),
      },
      deals_by_category: dealsByCategory.rows,
      top_deals: topDeals.rows,
      recent_activity: recentMatches.rows,
      revenue: revenueMetrics
    });
  } catch (error) {
    console.error('Error fetching admin stats:', error);
    res.status(500).json({ error: 'Failed to fetch statistics' });
  }
});

/**
 * GET /api/admin/performance - Get performance metrics
 */
router.get('/performance', async (req, res) => {
  try {
    // Deals added over time (last 30 days)
    const dealsOverTime = await query(`
      SELECT DATE(created_at) as date, COUNT(*) as count
      FROM deals
      WHERE created_at >= NOW() - INTERVAL '30 days'
      GROUP BY DATE(created_at)
      ORDER BY date ASC
    `);

    // Match rate by AI score
    const matchRateByScore = await query(`
      SELECT 
        CASE 
          WHEN ai_score >= 80 THEN '80-100'
          WHEN ai_score >= 60 THEN '60-79'
          WHEN ai_score >= 40 THEN '40-59'
          ELSE '0-39'
        END as score_range,
        COUNT(DISTINCT d.id) as deals,
        COUNT(m.id) as matches
      FROM deals d
      LEFT JOIN matches m ON d.id = m.deal_id
      GROUP BY score_range
      ORDER BY score_range DESC
    `);

    // Notification success rate
    const notificationStats = await query(`
      SELECT 
        channel,
        COUNT(*) as total,
        COUNT(CASE WHEN status = 'sent' THEN 1 END) as sent,
        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed
      FROM notifications
      GROUP BY channel
    `);

    res.json({
      deals_over_time: dealsOverTime.rows,
      match_rate_by_score: matchRateByScore.rows,
      notification_stats: notificationStats.rows
    });
  } catch (error) {
    console.error('Error fetching performance metrics:', error);
    res.status(500).json({ error: 'Failed to fetch metrics' });
  }
});

/**
 * POST /api/admin/cleanup - Clean up old data
 */
router.post('/cleanup', async (req, res) => {
  try {
    const { days = 90 } = req.body;

    // Delete old rejected matches
    const deletedMatches = await query(
      `DELETE FROM matches 
       WHERE status = 'rejected' 
       AND updated_at < NOW() - INTERVAL '${days} days'
       RETURNING id`
    );

    // Delete old inactive deals
    const deletedDeals = await query(
      `DELETE FROM deals 
       WHERE status = 'inactive' 
       AND updated_at < NOW() - INTERVAL '${days} days'
       RETURNING id`
    );

    res.json({
      message: 'Cleanup completed',
      deleted_matches: deletedMatches.rows.length,
      deleted_deals: deletedDeals.rows.length
    });
  } catch (error) {
    console.error('Error during cleanup:', error);
    res.status(500).json({ error: 'Cleanup failed' });
  }
});

module.exports = router;
