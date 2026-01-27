import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { Pool } from 'pg';
import dealRoutes from './routes/deals.js';
import buyerRoutes from './routes/buyers.js';
import categoryRoutes from './routes/categories.js';
import subscriptionRoutes from './routes/subscriptions.js';

dotenv.config();

const app = express();
const port = process.env.PORT || 3000;
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

// Middleware
app.use(cors());
app.use(express.json());

// Logger middleware
app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
  next();
});

// Health checks
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    service: 'vortexai-backend',
    uptime: process.uptime(),
  });
});

app.get('/api/health/db', async (req, res) => {
  try {
    const result = await pool.query('SELECT NOW()');
    res.json({
      status: 'ok',
      database: 'connected',
      timestamp: result.rows[0].now,
    });
  } catch (error) {
    res.status(500).json({
      status: 'error',
      database: 'disconnected',
      error: error.message,
    });
  }
});

// API Routes
app.use('/api/deals', dealRoutes);
app.use('/api/buyers', buyerRoutes);
app.use('/api/categories', categoryRoutes);
app.use('/api/subscriptions', subscriptionRoutes);

// Root endpoint
app.get('/api', (req, res) => {
  res.json({
    name: 'VortexAI Backend API',
    version: '1.0.0',
    status: 'production',
    endpoints: {
      health: '/health',
      db_health: '/api/health/db',
      deals: '/api/deals',
      buyers: '/api/buyers',
      categories: '/api/categories',
      subscriptions: '/api/subscriptions',
    },
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    success: false,
    error: 'Endpoint not found',
  });
});

// Error handler
app.use((err, req, res, next) => {
  console.error('❌ Error:', err);
  res.status(500).json({
    success: false,
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? err.message : undefined,
  });
});

// Start server
app.listen(port, () => {
  console.log(`✅ VortexAI Backend running on port ${port}`);
  console.log(`📍 Health: http://localhost:${port}/health`);
  console.log(`🗄️  DB: http://localhost:${port}/api/health/db`);
  console.log(`🔗 API: http://localhost:${port}/api`);
  console.log(`🚀 Ready for deals!`);
});