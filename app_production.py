from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from dotenv import load_dotenv

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="VortexAI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL not set")
    return psycopg2.connect(DATABASE_URL)

@app.get("/")
def root():
    return {"system": "VortexAI", "status": "running"}

@app.get("/health")
def health():
    if not DATABASE_URL:
        return {"status": "ok", "db": "not_configured"}
    try:
        conn = get_db_connection()
        conn.close()
        return {"status": "ok", "db": "connected"}
    except:
        return {"status": "ok", "db": "offline"}

@app.get("/seller", response_class=HTMLResponse)
def seller_portal():
    return "<html><body><h1>Seller Portal</h1></body></html>"

@app.get("/buyer", response_class=HTMLResponse)
def buyer_portal():
    return "<html><body><h1>Buyer Portal</h1></body></html>"

@app.post("/admin/webhooks/deal-ingest")
def ingest_deal(data: dict):
    return {"status": "ok"}

@app.get("/admin/deals")
def get_deals():
    return {"status": "ok", "deals": []}
