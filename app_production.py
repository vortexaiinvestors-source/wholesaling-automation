import os
import logging
import asyncio
import smtplib
from email.mime.text import MIMEText
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from pydantic import BaseModel
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vortexai")

app = FastAPI(title="VortexAI", version="3.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)

# ---------------- MODELS ----------------

class DealData(BaseModel):
    name: str
    email: str
    asset_type: str
    location: str
    price: float
    description: str = ""

class BuyerRegister(BaseModel):
    name: str
    email: str
    location: str = ""
    asset_types: str = "any"
    min_budget: float = 0
    max_budget: float = 999999999

# ---------------- EMAIL ----------------

def send_email(buyer_email, deal):
    try:
        body = f"""
🔥 NEW DEAL FOUND

Type: {deal['asset_type']}
Location: {deal['location']}
Price: ${deal['price']}
Score: {deal['score']}

Login to view full details.
"""

        msg = MIMEText(body)
        msg["Subject"] = "New Investment Deal Found"
        msg["From"] = os.getenv("EMAIL_FROM")
        msg["To"] = buyer_email

        server = smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT")))
        server.starttls()
        server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS"))
        server.send_message(msg)
        server.quit()

        logger.info(f"📧 Email sent to {buyer_email}")

    except Exception as e:
        logger.error(f"Email error: {e}")

# ---------------- AI MATCHING ----------------

def match(buyer, deal):
    if buyer["asset_types"] not in ("any", deal["asset_type"]):
        return False

    if buyer["location"] and buyer["location"].lower() not in deal["location"].lower():
        return False

    if not (buyer["min_budget"] <= deal["price"] <= buyer["max_budget"]):
        return False

    if deal["score"] < 60:
        return False

    return True

# ---------------- AUTOMATION ENGINE ----------------

async def automation_loop():
    await asyncio.sleep(10)

    while True:
        logger.info("🔁 Automation running...")

        try:
            conn = get_db()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            cur.execute("SELECT * FROM deals WHERE notified = false AND score >= 60 LIMIT 50")
            deals = cur.fetchall()

            cur.execute("SELECT * FROM buyers WHERE active = true")
            buyers = cur.fetchall()

            sent = 0

            for deal in deals:
                for buyer in buyers:
                    if match(buyer, deal):
                        send_email(buyer["email"], deal)
                        cur.execute("UPDATE deals SET notified = true WHERE id = %s", (deal["id"],))
                        conn.commit()
                        sent += 1
                        break

            cur.close()
            conn.close()

            logger.info(f"✅ Sent {sent} notifications")

        except Exception as e:
            logger.error(f"Automation error: {e}")

        await asyncio.sleep(900)  # 15 minutes

@app.on_event("startup")
async def start():
    asyncio.create_task(automation_loop())

# ---------------- API ----------------

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/admin/webhooks/deal-ingest")
def ingest(data: DealData):
    conn = get_db()
    cur = conn.cursor()

    score = 50
    if data.price < 100000:
        score += 15
    if "urgent" in data.description.lower():
        score += 20

    cur.execute("""
        INSERT INTO deals (name,email,asset_type,location,price,description,score,notified,created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,false,NOW())
    """, (
        data.name, data.email, data.asset_type,
        data.location, data.price, data.description, score
    ))

    conn.commit()
    cur.close()
    conn.close()

    return {"status": "ok"}

@app.post("/buyers/register")
def register(buyer: BuyerRegister):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO buyers (name,email,location,asset_types,min_budget,max_budget,active,created_at)
        VALUES (%s,%s,%s,%s,%s,%s,true,NOW())
    """, (
        buyer.name, buyer.email, buyer.location,
        buyer.asset_types, buyer.min_budget, buyer.max_budget
    ))

    conn.commit()
    cur.close()
    conn.close()

    return {"status": "ok"}

@app.get("/admin/deals")
def deals():
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM deals ORDER BY created_at DESC LIMIT 100")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"deals": rows}
