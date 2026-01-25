"""
Buyer Notification System (Brevo SMTP)
Sends matching deals to buyers every 5 minutes
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DATABASE_URL = os.getenv("DATABASE_URL")

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
EMAIL_FROM = os.getenv("EMAIL_FROM", "deals@vortexai.com")


def get_db_connection():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL not set")
    return psycopg2.connect(DATABASE_URL)


def get_buyers():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, email, name, location, asset_types, min_budget, max_budget
            FROM buyers
            WHERE active = true
        """)
        buyers = cur.fetchall()
        cur.close()
        conn.close()
        return buyers
    except Exception as e:
        logger.error(f"Error fetching buyers: {e}")
        return []


def get_recent_deals(minutes=30):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(f"""
            SELECT id, asset_type, location, price, description, score, created_at
            FROM deals
            WHERE created_at >= NOW() - INTERVAL '{minutes} minutes'
            AND score >= 7
            AND sent_to_buyers = false
            ORDER BY score DESC, created_at DESC
            LIMIT 50
        """)

        deals = cur.fetchall()
        cur.close()
        conn.close()
        return deals
    except Exception as e:
        logger.error(f"Error fetching deals: {e}")
        return []


def matches_buyer_criteria(deal, buyer):
    deal_location = (deal.get("location") or "").lower()
    buyer_location = (buyer.get("location") or "").lower()

    if buyer_location and buyer_location not in deal_location:
        return False

    asset_types = buyer.get("asset_types", "").split(",")
    asset_types = [a.strip() for a in asset_types if a.strip()]

    if asset_types and deal.get("asset_type") not in asset_types:
        return False

    price = deal.get("price", 0)
    if price < buyer.get("min_budget", 0) or price > buyer.get("max_budget", 10_000_000):
        return False

    return True


def send_deal_email(buyer_email, buyer_name, deals):

    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        logger.error("SMTP credentials not set")
        return False

    html_blocks = ""
    for deal in deals:
        html_blocks += f"""
        <div style="border:1px solid #ddd;padding:10px;margin:10px 0">
            <b>{deal['asset_type'].upper()}</b> – {deal['location']}<br>
            Price: ${deal['price']:,.0f}<br>
            Score: {deal['score']}/100
        </div>
        """

    html = f"""
    <html>
      <body>
        <h2>New VortexAI Deals</h2>
        <p>Hi {buyer_name},</p>
        {html_blocks}
        <p>Login to view more.</p>
      </body>
    </html>
    """

    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = buyer_email
    msg["Subject"] = f"🔥 {len(deals)} New Deals Matching Your Criteria"

    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)

        logger.info(f"Email sent to {buyer_email}")
        return True

    except Exception as e:
        logger.error(f"Email failed: {e}")
        return False


def mark_deals_as_sent(deal_ids):
    if not deal_ids:
        return

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        placeholders = ",".join(["%s"] * len(deal_ids))
        cur.execute(f"""
            UPDATE deals
            SET sent_to_buyers = true, sent_at = NOW()
            WHERE id IN ({placeholders})
        """, deal_ids)

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"Marked {len(deal_ids)} deals as sent")

    except Exception as e:
        logger.error(f"Failed to mark deals: {e}")


def run_buyer_notifications():

    logger.info("Starting buyer notifications")

    buyers = get_buyers()
    if not buyers:
        logger.info("No buyers found")
        return

    deals = get_recent_deals()
    if not deals:
        logger.info("No new deals found")
        return

    sent_ids = set()

    for buyer in buyers:
        matches = [d for d in deals if matches_buyer_criteria(d, buyer)]

        if matches:
            success = send_deal_email(buyer["email"], buyer["name"], matches)
            if success:
                for d in matches:
                    sent_ids.add(d["id"])

    if sent_ids:
        mark_deals_as_sent(list(sent_ids))

    logger.info("Buyer notifications completed")


if __name__ == "__main__":
    run_buyer_notifications()
