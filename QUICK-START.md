# ⚡ VortexAI Quick Start

Get VortexAI running in 10 minutes!

---

## 🎯 What Is This?

VortexAI is your **complete AI-powered deal-finding platform** that:
- Finds undervalued assets automatically (real estate, cars, equipment, etc.)
- Scores deals with AI (0-100)
- Matches them to buyers
- Sends instant notifications
- Runs 24/7 without you

---

## 🚀 Deploy in 10 Minutes

### 1. Create Railway Account
Go to **railway.app** and sign up (free tier works)

### 2. Deploy Backend

```bash
cd backend
npm install

# Login to Railway
npm i -g @railway/cli
railway login

# Create project and add database
railway init
railway add -d postgres

# Deploy
railway up

# Run database migration
railway run npm run db:migrate

# Get your backend URL
railway domain
```

Copy your backend URL! (e.g., `https://xxx.up.railway.app`)

### 3. Deploy Frontend

```bash
cd ../frontend
npm install

# Deploy to Railway
railway init
railway up

# Get your frontend URL
railway domain
```

### 4. Connect Frontend to Backend

In Railway frontend service:
1. Go to **Variables**
2. Add: `NEXT_PUBLIC_API_URL=https://your-backend-url`
3. Redeploy

### 5. Update Backend with Frontend URL

In Railway backend service:
1. Go to **Variables**
2. Add: `FRONTEND_URL=https://your-frontend-url`
3. Redeploy

---

## ✅ Test It Works

1. **Visit frontend**: `https://your-frontend-url`
2. **Check backend health**: `https://your-backend-url/health`
3. **Sign up a buyer**: Click "Get Started" on homepage
4. **View dashboard**: Go to `/admin`

---

## 🔌 Add Deal Sources (Zapier)

1. Create free **Zapier** account
2. Make a Zap:
   - **Trigger**: RSS Feed / Email / Facebook Marketplace
   - **Action**: Webhooks → POST to `https://your-backend-url/api/webhooks/zapier`
   - **Data**: Send deal info as JSON

3. Deals auto-appear on `/deals` page!

---

## 📧 Enable Notifications (Optional)

### Email (Gmail)
In Railway backend, add variables:
```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your@gmail.com
EMAIL_PASS=your-app-password
```

### SMS (Twilio)
In Railway backend, add variables:
```
TWILIO_ACCOUNT_SID=xxx
TWILIO_AUTH_TOKEN=xxx
TWILIO_PHONE_NUMBER=+1234567890
```

---

## 📁 What You Get

✅ **Complete backend** (Node.js + PostgreSQL)
✅ **Beautiful frontend** (Next.js + Tailwind)
✅ **AI scoring** (automatic deal evaluation)
✅ **Buyer matching** (smart algorithm)
✅ **Notifications** (email + SMS)
✅ **Admin dashboard** (analytics)
✅ **Zapier ready** (webhook integrations)

---

## 🎯 Next Steps

1. ✅ Deploy backend + frontend (done!)
2. 📝 Set up Zapier for deal sources
3. 📧 Configure email/SMS (optional)
4. 👥 Promote buyer signup form
5. 💰 Start closing deals!

---

## 📚 Full Docs

- [README.md](./README.md) - Complete overview
- [docs/deployment-guide.md](./docs/deployment-guide.md) - Detailed deployment
- [backend/README.md](./backend/README.md) - API documentation
- [frontend/README.md](./frontend/README.md) - Frontend customization

---

## 🎉 You're Ready!

Everything is built. Just deploy and start finding deals!

**Questions?** Check the full deployment guide.

**Ready to scale?** See the README for growth strategy.

---

**Let's go make some money! 💰🚀**
