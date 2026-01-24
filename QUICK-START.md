# Quick Start Guide

## 5-Minute Setup

### 1. Clone Repository
```bash
git clone https://github.com/vortexaiinvestors-source/wholesaling-automation.git
cd wholesaling-automation
```

### 2. Setup Environment
```bash
bash setup.sh
```

### 3. Configure API Keys
Edit `.env` with your API keys:
- SUPABASE_URL and SUPABASE_KEY
- OPENAI_API_KEY
- SCRAPERAPI_KEY, APIFY_API_KEY
- SENDGRID_API_KEY

### 4. Deploy Database
```bash
psql -h db.ggjgaftekrafsuixmosd.supabase.co -U postgres -d postgres -f database/DEPLOY-NOW.sql
```

### 5. Start Scrapers
```bash
python scrapers/master_scraper_orchestrator.py
```

## System Status
✅ Database: 7 tables deployed
✅ Scrapers: 25+ sources configured
✅ API: Ready for deployment

## Deployment
- **Supabase**: Database live
- **GitHub**: Code repository active
- **Railway**: Deployment ready
