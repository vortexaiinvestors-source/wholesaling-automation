const { query } = require('../config/database');

/**
 * Find matching buyers for a deal
 */
const findMatchingBuyers = async (deal) => {
  try {
    // Get all active buyers
    const buyersResult = await query(
      `SELECT * FROM buyers WHERE is_active = true`
    );

    const buyers = buyersResult.rows;
    const matches = [];

    for (const buyer of buyers) {
      const matchScore = calculateMatchScore(deal, buyer);
      
      if (matchScore >= 60) {
        matches.push({
          buyer_id: buyer.id,
          buyer_name: buyer.name,
          buyer_email: buyer.email,
          buyer_phone: buyer.phone,
          match_score: matchScore,
          deal_id: deal.id
        });
      }
    }

    // Sort by match score (highest first)
    matches.sort((a, b) => b.match_score - a.match_score);

    return matches;
  } catch (error) {
    console.error('Error finding matching buyers:', error);
    throw error;
  }
};

/**
 * Calculate match score between deal and buyer (0-100)
 */
const calculateMatchScore = (deal, buyer) => {
  let score = 0;
  const factors = [];

  // 1. CATEGORY MATCH (0-30 points)
  if (buyer.categories && buyer.categories.length > 0) {
    if (buyer.categories.includes(deal.category)) {
      score += 30;
      factors.push('Category match');
    }
  } else {
    // No preference = matches all
    score += 15;
  }

  // 2. BUDGET MATCH (0-30 points)
  if (buyer.budget_min && buyer.budget_max) {
    if (deal.price >= buyer.budget_min && deal.price <= buyer.budget_max) {
      score += 30;
      factors.push('Perfect budget match');
    } else if (deal.price < buyer.budget_min) {
      score += 10;
      factors.push('Below budget');
    } else if (deal.price <= buyer.budget_max * 1.2) {
      score += 15;
      factors.push('Slightly above budget');
    }
  } else {
    score += 15;
  }

  // 3. LOCATION MATCH (0-20 points)
  if (buyer.locations && buyer.locations.length > 0 && deal.location) {
    const locationMatch = buyer.locations.some(loc => 
      deal.location.toLowerCase().includes(loc.toLowerCase()) ||
      loc.toLowerCase().includes(deal.location.toLowerCase())
    );
    
    if (locationMatch) {
      score += 20;
      factors.push('Location match');
    }
  } else {
    score += 10;
  }

  // 4. DEAL QUALITY (0-20 points)
  if (deal.ai_score >= 80) {
    score += 20;
    factors.push('Excellent deal quality');
  } else if (deal.ai_score >= 70) {
    score += 15;
    factors.push('Good deal quality');
  } else if (deal.ai_score >= 60) {
    score += 10;
    factors.push('Average deal quality');
  }

  return Math.min(100, Math.round(score));
};

/**
 * Create matches in database
 */
const createMatches = async (deal, matches) => {
  try {
    const createdMatches = [];

    for (const match of matches) {
      // Check if match already exists
      const existing = await query(
        `SELECT id FROM matches WHERE deal_id = $1 AND buyer_id = $2`,
        [deal.id, match.buyer_id]
      );

      if (existing.rows.length === 0) {
        const result = await query(
          `INSERT INTO matches (deal_id, buyer_id, match_score, status)
           VALUES ($1, $2, $3, 'pending')
           RETURNING *`,
          [deal.id, match.buyer_id, match.match_score]
        );
        
        createdMatches.push(result.rows[0]);
      }
    }

    return createdMatches;
  } catch (error) {
    console.error('Error creating matches:', error);
    throw error;
  }
};

/**
 * Get buyer preferences summary
 */
const getBuyerPreferences = async (buyerId) => {
  try {
    const result = await query(
      `SELECT * FROM buyers WHERE id = $1`,
      [buyerId]
    );

    if (result.rows.length === 0) {
      throw new Error('Buyer not found');
    }

    const buyer = result.rows[0];
    
    return {
      id: buyer.id,
      name: buyer.name,
      categories: buyer.categories || [],
      budget: {
        min: buyer.budget_min,
        max: buyer.budget_max
      },
      locations: buyer.locations || [],
      subscription_tier: buyer.subscription_tier
    };
  } catch (error) {
    console.error('Error getting buyer preferences:', error);
    throw error;
  }
};

module.exports = {
  findMatchingBuyers,
  calculateMatchScore,
  createMatches,
  getBuyerPreferences
};
