const OpenAI = require('openai');

// Initialize OpenAI (optional - can work without it)
const openai = process.env.OPENAI_API_KEY ? new OpenAI({
  apiKey: process.env.OPENAI_API_KEY
}) : null;

// Urgency keywords that indicate motivated sellers
const URGENCY_KEYWORDS = [
  'must sell', 'motivated', 'urgent', 'divorce', 'relocating', 'moving',
  'job loss', 'foreclosure', 'short sale', 'quick sale', 'asap', 'obo',
  'best offer', 'make offer', 'need gone', 'priced to sell', 'reduced',
  'price drop', 'estate sale', 'bankruptcy', 'liquidation', 'cash only',
  'investor special', 'handyman', 'fixer', 'as-is', 'no reasonable offer refused'
];

/**
 * Calculate AI score for a deal (0-100)
 */
const calculateDealScore = async (deal) => {
  try {
    let score = 50; // Base score
    const factors = [];

    // 1. DISCOUNT PERCENTAGE (0-30 points)
    if (deal.market_value && deal.price) {
      const discount = ((deal.market_value - deal.price) / deal.market_value) * 100;
      deal.discount_percentage = discount;
      
      if (discount >= 40) {
        score += 30;
        factors.push(`Excellent discount: ${discount.toFixed(1)}%`);
      } else if (discount >= 25) {
        score += 20;
        factors.push(`Good discount: ${discount.toFixed(1)}%`);
      } else if (discount >= 15) {
        score += 10;
        factors.push(`Moderate discount: ${discount.toFixed(1)}%`);
      } else if (discount < 0) {
        score -= 20;
        factors.push(`Overpriced by ${Math.abs(discount).toFixed(1)}%`);
      }

      // Calculate profit potential
      deal.profit_potential = deal.market_value - deal.price;
    }

    // 2. URGENCY KEYWORDS (0-25 points)
    const foundKeywords = findUrgencyKeywords(deal.title, deal.description);
    deal.urgency_keywords = foundKeywords;
    
    if (foundKeywords.length >= 3) {
      score += 25;
      factors.push(`High urgency: ${foundKeywords.length} keywords`);
    } else if (foundKeywords.length >= 2) {
      score += 15;
      factors.push(`Medium urgency: ${foundKeywords.length} keywords`);
    } else if (foundKeywords.length >= 1) {
      score += 8;
      factors.push(`Low urgency: ${foundKeywords.length} keyword`);
    }

    // 3. PRICE RANGE (0-15 points)
    if (deal.price >= 10000 && deal.price <= 500000) {
      score += 15;
      factors.push('Ideal price range');
    } else if (deal.price >= 5000 && deal.price <= 1000000) {
      score += 10;
      factors.push('Good price range');
    } else if (deal.price < 1000) {
      score -= 10;
      factors.push('Too cheap - possible scam');
    }

    // 4. CATEGORY MULTIPLIER (0-10 points)
    const categoryScores = {
      'real-estate': 10,
      'vehicles': 8,
      'heavy-equipment': 9,
      'luxury-items': 7,
      'business-assets': 8,
      'wholesale': 6
    };
    const categoryScore = categoryScores[deal.category] || 5;
    score += categoryScore;
    factors.push(`Category: ${deal.category}`);

    // 5. SOURCE RELIABILITY (0-10 points)
    const sourceScores = {
      'facebook-marketplace': 8,
      'craigslist': 6,
      'autotrader': 9,
      'fsbo': 8,
      'auction': 7,
      'dealer': 5
    };
    const sourceScore = sourceScores[deal.source] || 5;
    score += sourceScore;

    // 6. USE AI FOR ADVANCED SCORING (optional)
    if (openai && process.env.USE_AI_SCORING === 'true') {
      try {
        const aiAdjustment = await getAIScoreAdjustment(deal);
        score += aiAdjustment;
        if (aiAdjustment !== 0) {
          factors.push(`AI adjustment: ${aiAdjustment > 0 ? '+' : ''}${aiAdjustment}`);
        }
      } catch (error) {
        console.error('AI scoring failed:', error.message);
      }
    }

    // Normalize score to 0-100
    score = Math.max(0, Math.min(100, Math.round(score)));

    return {
      score,
      factors,
      discount: deal.discount_percentage,
      profit: deal.profit_potential,
      urgency_keywords: foundKeywords
    };
  } catch (error) {
    console.error('Error calculating deal score:', error);
    return {
      score: 50,
      factors: ['Error calculating score'],
      error: error.message
    };
  }
};

/**
 * Find urgency keywords in text
 */
const findUrgencyKeywords = (title = '', description = '') => {
  const text = `${title} ${description}`.toLowerCase();
  const found = [];
  
  URGENCY_KEYWORDS.forEach(keyword => {
    if (text.includes(keyword.toLowerCase())) {
      found.push(keyword);
    }
  });
  
  return found;
};

/**
 * Get AI-based score adjustment (-10 to +10)
 */
const getAIScoreAdjustment = async (deal) => {
  if (!openai) return 0;

  try {
    const prompt = `Analyze this deal and rate it from -10 to +10 based on investment potential:

Title: ${deal.title}
Price: $${deal.price}
Market Value: $${deal.market_value || 'unknown'}
Category: ${deal.category}
Description: ${deal.description?.substring(0, 500) || 'N/A'}

Return ONLY a number from -10 to +10. Positive for good deals, negative for bad/risky deals.`;

    const response = await openai.chat.completions.create({
      model: 'gpt-3.5-turbo',
      messages: [{ role: 'user', content: prompt }],
      max_tokens: 10,
      temperature: 0.3
    });

    const adjustment = parseInt(response.choices[0].message.content.trim());
    return isNaN(adjustment) ? 0 : Math.max(-10, Math.min(10, adjustment));
  } catch (error) {
    console.error('AI scoring error:', error);
    return 0;
  }
};

/**
 * Estimate market value if not provided
 */
const estimateMarketValue = async (deal) => {
  // Simple estimation based on category and price
  // In production, you'd use external APIs or AI
  const estimationRules = {
    'real-estate': deal.price * 1.3,
    'vehicles': deal.price * 1.2,
    'heavy-equipment': deal.price * 1.25,
    'luxury-items': deal.price * 1.4,
    'business-assets': deal.price * 1.3,
    'wholesale': deal.price * 1.15
  };

  return estimationRules[deal.category] || deal.price * 1.2;
};

module.exports = {
  calculateDealScore,
  findUrgencyKeywords,
  estimateMarketValue
};
