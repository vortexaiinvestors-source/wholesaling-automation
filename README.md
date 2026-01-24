# VortexAI Real Estate Wholesaling System

## 🚀 Production System

**Status:** DEPLOYING TO RAILWAY

### What You Get

✅ **Seller Portal** - Properties submitted at `/seller`
✅ **Buyer Portal** - Browse deals at `/buyer`
✅ **Deal API** - Color-coded: 🟢 GREEN (>$15K), 🟡 YELLOW ($7.5K-$15K), 🔴 RED (<$7.5K)
✅ **KPI Tracking** - Daily metrics at `/api/kpi/daily`
✅ **Database** - Supabase PostgreSQL (7 tables)
✅ **Automation** - Deals sent to buyers every 5 minutes

### Getting Started

1. **Seller:** Go to `https://vortexai-app.up.railway.app/seller`
2. **Buyer:** Visit `https://vortexai-app.up.railway.app/buyer`
3. **Health Check:** `https://vortexai-app.up.railway.app/health`

### Files

- `app_production.py` - Complete FastAPI application
- `Dockerfile` - Production container
- `requirements.txt` - 6 essential dependencies
- `.env.template` - Configuration template
- `railway.yml` - Railway deployment config

### API Endpoints

- `GET /health` - System status
- `POST /api/seller/intake` - Submit property
- `GET /api/deals/available` - List available deals
- `POST /api/deals/{id}/purchase` - Buy a deal
- `GET /api/kpi/daily` - Daily KPI metrics

### Automation

Triggers active (every 5 minutes):
- Check for new GREEN/YELLOW deals
- Send notifications to buyers
- Track KPI metrics

---

**Built with:** FastAPI + Supabase + Railway
