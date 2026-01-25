# VortexAI Production Checklist - Phase 3 & 4

## Overview
Estimated Time: 30-45 minutes | Status: 92% → 100% Complete

## PHASE 3A: BREVO SMTP EMAIL SETUP

### Step 1: Get Brevo Credentials
- [ ] Sign up at https://www.brevo.com
- [ ] Navigate to Settings → Sender Details → SMTP Settings
- [ ] Copy SMTP login and password

### Step 2: Update Environment Variables
```bash
BREVO_SMTP_USER=your-brevo-sender-email@domain.com
BREVO_SMTP_PASSWORD=your-smtp-key
BREVO_SMTP_FROM=noreply@vortexai.com
```

### Step 3: Deploy Updated server.js
- [ ] Replace server.js with server-production-phase3-4.js
- [ ] Ensure nodemailer is in package.json
- [ ] Deploy to Railway
- [ ] Check logs for "Brevo SMTP Connected"

## PHASE 3B: WEBHOOK AUTHENTICATION

### Step 1: Generate Webhook Key
```bash
openssl rand -base64 32
```

### Step 2: Add to Environment
```bash
API_INGEST_KEY=your-generated-key-here
ENABLE_WEBHOOK_SIGNATURE=true
```

## PHASE 3C: SCRAPER INTEGRATION

### Step 1: Deploy Python Scraper
- [ ] Upload master_scraper_orchestrator.py
- [ ] Ensure Python 3.8+ available
- [ ] Install: pip install requests

### Step 2: Test Scraper
```bash
export API_BASE_URL=https://your-railway-url.up.railway.app
python3 master_scraper_orchestrator.py
```

## PHASE 4: AUTOMATION SCHEDULING

### Step 1: Create Railway Cron Job
1. Go to Railway Dashboard
2. Click "Create New" → "Cron Job"
3. Name: VortexAI Deal Scanner
4. Schedule: */30 * * * *
5. Timeout: 300 seconds

### Step 2: Set Environment Variables
- [ ] API_BASE_URL
- [ ] DATABASE_URL
- [ ] BREVO_SMTP_USER
- [ ] BREVO_SMTP_PASSWORD
- [ ] API_INGEST_KEY

## FINAL VERIFICATION

- [ ] Brevo credentials configured
- [ ] Test email received
- [ ] Webhook security enabled
- [ ] Scraper working
- [ ] Cron job scheduled
- [ ] All 65 sources configured
- [ ] AI scoring active
- [ ] Buyer matching enabled
- [ ] Logs show no errors

## EXPECTED METRICS

- Scan Frequency: Every 30 minutes
- Deals per Scan: 5-15 deals
- Monthly Deals: 7,200 - 21,600 leads
- Hot Deals: ~20-30% (score >= 75)
- System Uptime: 99%+

---

Status: Ready for Production Deployment ✅