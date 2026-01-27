import express from 'express';
import { Pool } from 'pg';
import Stripe from 'stripe';

const router = express.Router();
const pool = new Pool({ connectionString: process.env.DATABASE_URL });
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

// Subscription plans
const PLANS = {
  free: { stripe_id: 'price_free', name: 'Free', price: 0, deals_per_month: 5 },
  pro: { stripe_id: process.env.STRIPE_PRO_PRICE_ID, name: 'Pro', price: 4900, deals_per_month: 500 },
  enterprise: { stripe_id: process.env.STRIPE_ENTERPRISE_PRICE_ID, name: 'Enterprise', price: 29900, deals_per_month: 10000 },
};

// Get all subscriptions for a buyer
router.get('/buyer/:buyer_id', async (req, res) => {
  try {
    const result = await pool.query(
      'SELECT * FROM subscriptions WHERE buyer_id = $1 ORDER BY created_at DESC',
      [req.params.buyer_id]
    );
    res.json({
      success: true,
      count: result.rowCount,
      subscriptions: result.rows,
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Get subscription details
router.get('/:subscription_id', async (req, res) => {
  try {
    const result = await pool.query(
      'SELECT * FROM subscriptions WHERE id = $1',
      [req.params.subscription_id]
    );
    if (result.rowCount === 0) {
      return res.status(404).json({ success: false, error: 'Subscription not found' });
    }
    res.json({ success: true, subscription: result.rows[0] });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Create subscription (upgrade plan)
router.post('/buyer/:buyer_id/upgrade', async (req, res) => {
  const { plan_type } = req.body;

  if (!PLANS[plan_type]) {
    return res.status(400).json({ success: false, error: 'Invalid plan type' });
  }

  if (plan_type === 'free') {
    return res.status(400).json({ success: false, error: 'Use cancel to downgrade to free' });
  }

  try {
    // Get buyer email
    const buyerResult = await pool.query(
      'SELECT email FROM buyers WHERE id = $1',
      [req.params.buyer_id]
    );
    if (buyerResult.rowCount === 0) {
      return res.status(404).json({ success: false, error: 'Buyer not found' });
    }

    const buyerEmail = buyerResult.rows[0].email;
    const plan = PLANS[plan_type];

    // Create Stripe checkout session
    const session = await stripe.checkout.sessions.create({
      payment_method_types: ['card'],
      line_items: [
        {
          price: plan.stripe_id,
          quantity: 1,
        },
      ],
      mode: 'subscription',
      success_url: `${process.env.FRONTEND_URL}/dashboard?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${process.env.FRONTEND_URL}/pricing`,
      customer_email: buyerEmail,
      metadata: {
        buyer_id: req.params.buyer_id,
        plan_type: plan_type,
      },
    });

    res.json({
      success: true,
      checkout_url: session.url,
      session_id: session.id,
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Cancel subscription
router.post('/:subscription_id/cancel', async (req, res) => {
  try {
    const result = await pool.query(
      'UPDATE subscriptions SET status = $1, cancelled_at = NOW() WHERE id = $2 RETURNING *',
      ['cancelled', req.params.subscription_id]
    );
    if (result.rowCount === 0) {
      return res.status(404).json({ success: false, error: 'Subscription not found' });
    }

    res.json({
      success: true,
      message: 'Subscription cancelled',
      subscription: result.rows[0],
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Webhook for Stripe events
router.post('/webhook', express.raw({ type: 'application/json' }), async (req, res) => {
  const sig = req.headers['stripe-signature'];

  let event;
  try {
    event = stripe.webhooks.constructEvent(
      req.body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET
    );
  } catch (error) {
    console.error('Webhook error:', error.message);
    return res.status(400).send(`Webhook Error: ${error.message}`);
  }

  try {
    switch (event.type) {
      case 'checkout.session.completed':
        const session = event.data.object;
        const { buyer_id, plan_type } = session.metadata;

        // Create subscription record
        await pool.query(
          `INSERT INTO subscriptions 
           (buyer_id, plan_type, stripe_subscription_id, status, started_at) 
           VALUES ($1, $2, $3, $4, NOW())
           ON CONFLICT (stripe_subscription_id) DO UPDATE 
           SET status = 'active'`,
          [buyer_id, plan_type, session.subscription, 'active']
        );

        console.log(`✅ Subscription created for buyer ${buyer_id}`);
        break;

      case 'invoice.payment_succeeded':
        console.log('Payment succeeded');
        break;

      case 'customer.subscription.deleted':
        const subscription = event.data.object;
        await pool.query(
          'UPDATE subscriptions SET status = $1 WHERE stripe_subscription_id = $2',
          ['cancelled', subscription.id]
        );
        console.log('Subscription cancelled');
        break;
    }

    res.json({ received: true });
  } catch (error) {
    console.error('Webhook processing error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get pricing plans
router.get('/', (req, res) => {
  res.json({
    success: true,
    plans: [
      {
        type: 'free',
        name: 'Free',
        price: 0,
        features: [
          '5 deals/month',
          'Basic filters',
          'Email notifications',
        ],
      },
      {
        type: 'pro',
        name: 'Pro',
        price: 4900,
        features: [
          '500 deals/month',
          'Advanced AI scoring',
          'Priority alerts',
          'API access',
        ],
      },
      {
        type: 'enterprise',
        name: 'Enterprise',
        price: 29900,
        features: [
          '10,000 deals/month',
          'Custom categories',
          'Dedicated support',
          'White-label API',
        ],
      },
    ],
  });
});

export default router;