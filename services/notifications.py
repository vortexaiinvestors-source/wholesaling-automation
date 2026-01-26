"""
VortexAI Notification Engine
- Sends matched deals to PAID buyers
- Email (SMTP / Brevo / SendGrid)
- Optional SMS (Twilio)
- Tracks sent status in deal_matches
"""

import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Optional SMS
try:
    from twilio.rest import Client as TwilioClient
except Exception:
    TwilioClient = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("notifications")

DATABASE_URL = os.getenv("DATABASE_URL")

# Email
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
EMAIL_FROM = os.getenv("EMAIL_FROM", "deals@vortexai.com")

# SMS (optional)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")  # your email for alerts


def get_db():
    return psycopg2.connect(DATABASE_URL)


def get_pending_matches(limit=50):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT 
            dm.id AS match_id,
            d.id AS deal_id,
            d.asset_type,
            d.location,
            d.price,
            d.score,
            b.id AS buyer_id,
            b.email,
            b.name,
            b.phone
        FROM deal_matches dm
        JOIN deals d ON d.id = dm.deal_id
        JOIN buyers b ON b.id = dm.buyer_id
        WHERE dm.status = 'matched'
        ORDER BY dm.created_at ASC
        LIMIT %s
    """, (limit,))

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def mark_match_status(match_id, status):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE deal_matches
        SET status = %s, updated_at = NOW()
        WHERE id = %s
    """, (status, match_id))
    conn.commit()
    cur.close()
    conn.close()


def send_email(to_email, subject, html):
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        logger.warning("SMTP not configured")
        return False

    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"Email failed: {e}")
        return False


def send_sms(phone, text):
    if not phone or not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        return False

    try:
        client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=text,
            from_=TWILIO_FROM_NUMBER,
            to=phone
        )
        return True
    except Exception as e:
        logger.error(f"SMS failed: {e}")
        return False


def notify_admin(message):
    if ADMIN_EMAIL:
        send_email(ADMIN_EMAIL, "VortexAI Alert", f"<pre>{message}</pre>")


def build_buyer_email(buyer_name, deal):
    return f"""
    <h2>New Deal Matched For You</h2>
    <p>Hi {buyer_name},</p>

    <b>Asset:</b> {deal['asset_type']}<br>
    <b>Location:</b> {deal['location']}<br>
    <b>Price:</b> ${deal['price']:,.0f}<br>
    <b>AI Score:</b> {deal['score']}/100<br>

    <p>Reply to this email or login to VortexAI to claim this deal.</p>
    """


def process_notifications():
    logger.info("🔔 Running notification engine")

    matches = get_pending_matches()

    if not matches:
        logger.info("No pending matches")
        return

    for m in matches:
        try:
            email_html = build_buyer_email(m["name"], m)

            email_ok = send_email(
                m["email"],
                f"🔥 New {m['asset_type']} deal matched",
                email_html
            )

            sms_ok = False
            if m.get("phone"):
                sms_ok = send_sms(
                    m["phone"],
                    f"New deal: {m['asset_type']} in {m['location']} for ${m['price']:,.0f}"
                )

            if email_ok or sms_ok:
                mark_match_status(m["match_id"], "contacted")
                notify_admin(f"Buyer {m['email']} notified for deal #{m['deal_id']}")
            else:
                mark_match_status(m["match_id"], "failed")

        except Exception as e:
            logger.error(f"Notification error: {e}")
            mark_match_status(m["match_id"], "failed")

    logger.info("✅ Notification run complete")


if __name__ == "__main__":
    process_notifications()
