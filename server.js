require('dotenv').config();
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const rateLimit = require('express-rate-limit');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());
app.use(morgan('combined'));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100 // limit each IP to 100 requests per windowMs
});
app.use('/api/', limiter);

// Import routes
const dealsRoutes = require('./routes/deals');
const buyersRoutes = require('./routes/buyers');
const matchesRoutes = require('./routes/matches');
const webhookRoutes = require('./routes/webhooks');
const adminRoutes = require('./routes/admin');

// Health check
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy',
    timestamp: new Date().toISOString(),
    service: 'VortexAI Backend',
    version: '1.0.0'
  });
});

// API Routes
app.use('/api/deals', dealsRoutes);
app.use('/api/buyers', buyersRoutes);
app.use('/api/matches', matchesRoutes);
app.use('/api/webhooks', webhookRoutes);
app.use('/api/admin', adminRoutes);

// Root endpoint
app.get('/', (req, res) => {
  res.json({
    service: 'VortexAI Backend API',
    version: '1.0.0',
    endpoints: {
      health: '/health',
      deals: '/api/deals',
      buyers: '/api/buyers',
      matches: '/api/matches',
      webhooks: '/api/webhooks',
      admin: '/api/admin'
    }
  });
});

// Error handling
app.use((err, req, res, next) => {
  console.error('Error:', err);
  res.status(err.status || 500).json({
    error: err.message || 'Internal Server Error',
    timestamp: new Date().toISOString()
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Route not found' });
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 VortexAI Backend running on port ${PORT}`);
  console.log(`📊 Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`🔗 Health check: http://localhost:${PORT}/health`);
});

module.exports = app;
