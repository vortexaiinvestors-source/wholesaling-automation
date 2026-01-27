# VortexAI Backend

Production-ready Node.js/Express backend for VortexAI deal matching platform.

## Quick Start

```bash
npm install
cp .env.example .env
npm start
```

API runs on `http://localhost:3000`

## API Endpoints

- `GET /health` - Server health check
- `GET /api/health/db` - Database connection status
- `GET /api/deals` - List all deals
- `POST /api/deals` - Create a new deal
- `GET /api/buyers` - List all buyers  
- `POST /api/buyers` - Create a new buyer

## Environment Variables

See `.env.example` for required configuration.

## Deployment

Ready for Railway.app:
1. Connect repo to Railway project
2. Set DATABASE_URL env var
3. Deploy!

## Database

Requires PostgreSQL 12+ with pre-created schema tables.