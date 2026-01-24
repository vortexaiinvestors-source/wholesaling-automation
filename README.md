# VortexAI Backend

AI-powered deal-finding and buyer-matching platform backend.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Required variables:
- `DATABASE_URL` - Railway PostgreSQL connection string
- `PORT` - Server port (default: 3000)

Optional variables:
- `OPENAI_API_KEY` - For advanced AI scoring
- `EMAIL_*` - For email notifications
- `TWILIO_*` - For SMS notifications

### 3. Run Database Migration

```bash
npm run db:migrate
```

This creates all required tables and indexes.

### 4. Start Server

```bash
# Development
npm run dev

# Production
npm start
```

## 📡 API Endpoints

### Deals

- `GET /api/deals` - List all deals
- `GET /api/deals/:id` - Get single deal
- `POST /api/deals` - Create new deal
- `PUT /api/deals/:id` - Update deal
- `DELETE /api/deals/:id` - Delete deal
- `GET /api/deals/:id/matches` - Get matches for deal

### Buyers

- `GET /api/buyers` - List all buyers
- `GET /api/buyers/:id` - Get single buyer
- `POST /api/buyers` - Create buyer (signup)
- `PUT /api/buyers/:id` - Update buyer preferences
- `DELETE /api/buyers/:id` - Delete buyer
- `GET /api/buyers/:id/matches` - Get matches for buyer
- `POST /api/buyers/:id/unsubscribe` - Unsubscribe buyer

### Matches

- `GET /api/matches` - List all matches
- `PUT /api/matches/:id` - Update match status
- `POST /api/matches/:id/track` - Track buyer interaction

### Webhooks

- `POST /api/webhooks/zapier` - Receive deals from Zapier
- `POST /api/webhooks/google-forms` - Receive buyer signups
- `GET /api/webhooks/logs` - View webhook logs

### Admin

- `GET /api/admin/stats` - Dashboard statistics
- `GET /api/admin/performance` - Performance metrics
- `POST /api/admin/cleanup` - Clean old data

## 🔧 Workers

### Deal Scraper

Run the deal scraper to find new deals:

```bash
npm run scrape
```

This can be scheduled as a cron job on Railway.

## 🏗️ Architecture

```
backend/
├── config/
│   └── database.js          # PostgreSQL connection
├── routes/
│   ├── deals.js             # Deal endpoints
│   ├── buyers.js            # Buyer endpoints
│   ├── matches.js           # Match endpoints
│   ├── webhooks.js          # Webhook receivers
│   └── admin.js             # Admin dashboard
├── services/
│   ├── aiScoring.js         # AI deal scoring logic
│   ├── buyerMatcher.js      # Buyer matching algorithm
│   └── notifications.js     # Email/SMS sender
├── workers/
│   └── dealScraper.js       # Automated deal finder
├── scripts/
│   └── migrate.js           # Database migration
└── server.js                # Main Express server
```

## 🎯 How It Works

1. **Deal Ingestion**
   - Webhook receives deal from Zapier/Forms
   - Deal scraper finds deals from sources
   - API creates deal manually

2. **AI Scoring** (0-100 points)
   - Discount percentage (30 pts)
   - Urgency keywords (25 pts)
   - Price range (15 pts)
   - Category quality (10 pts)
   - Source reliability (10 pts)
   - Optional OpenAI adjustment (10 pts)

3. **Buyer Matching**
   - Finds buyers matching deal criteria
   - Scores each match (0-100)
   - Creates match records
   - Sends notifications

4. **Notifications**
   - Email for all high-score matches
   - SMS for excellent matches (80+)
   - Tracks opens/clicks

## 🚀 Deployment to Railway

### Option 1: Deploy from GitHub

1. Push this code to GitHub
2. In Railway:
   - New Project → Deploy from GitHub
   - Select your repository
   - Add PostgreSQL database
   - Set environment variables
   - Deploy!

### Option 2: Deploy from CLI

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Initialize
railway init

# Link database
railway add -d postgres

# Deploy
railway up
```

### Post-Deployment

1. Run migration:
```bash
railway run npm run db:migrate
```

2. Get your public URL:
```bash
railway domain
```

3. Update `FRONTEND_URL` in environment variables

## 📊 Database Schema

### deals
- id, title, description, price, market_value
- category, location, source, source_url
- ai_score, urgency_keywords, discount_percentage
- profit_potential, status, created_at

### buyers
- id, name, email, phone
- preferences, budget_min, budget_max
- locations, categories, subscription_tier
- is_active, created_at

### matches
- id, deal_id, buyer_id, match_score
- status, notified_at, viewed_at, interested_at
- notes, created_at

### notifications
- id, match_id, buyer_id, type, channel
- content, sent_at, opened_at, clicked_at
- status, error_message

### webhook_logs
- id, source, payload, processed
- deal_id, error_message, created_at

## 🔐 Security

- Rate limiting enabled (100 req/15min)
- Helmet.js for security headers
- CORS enabled
- Input validation on all endpoints
- SQL injection prevention via parameterized queries

## 📈 Monitoring

Health check endpoint:
```
GET /health
```

Returns:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "service": "VortexAI Backend",
  "version": "1.0.0"
}
```

## 🐛 Troubleshooting

### Database connection fails
- Check `DATABASE_URL` is correct
- Verify Railway PostgreSQL is running
- Check network/firewall settings

### Notifications not sending
- Verify email/Twilio credentials
- Check notification service logs
- Test with a single notification first

### Low match rate
- Verify buyer preferences are set
- Check AI scoring thresholds
- Review category mappings

## 📝 License

MIT
