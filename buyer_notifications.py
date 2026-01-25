"""
Buyer Notification System
Sends matching deals to buyers every 5 minutes
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging
from datetime import datetime, timedelta
import requests

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDGRID_FROM_EMAIL = "deals@vortexai.com"


def get_db_connection():
    """Get database connection"""
    if not DATABASE_URL:
        raise Exception("DATABASE_URL not set")
    return psycopg2.connect(DATABASE_URL)


def get_buyers():
    """Get all registered buyers"""
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
    """Get deals from last X minutes that haven't been sent to buyers yet"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get deals from last N minutes with score >= 7 (good deals)
        cur.execute("""
            SELECT id, name, email, asset_type, location, price, 
                   description, score, created_at
            FROM deals
            WHERE created_at >= NOW() - INTERVAL '%d minutes'
            AND score >= 7
            AND sent_to_buyers = false
            ORDER BY score DESC, created_at DESC
            LIMIT 50
        """ % minutes)
        
        deals = cur.fetchall()
        cur.close()
        conn.close()
        return deals
    except Exception as e:
        logger.error(f"Error fetching deals: {e}")
        return []


def matches_buyer_criteria(deal, buyer):
    """Check if deal matches buyer's criteria"""
    # Match by location
    deal_location = (deal.get('location') or '').lower()
    buyer_location = (buyer.get('location') or '').lower()
    
    if buyer_location and buyer_location not in deal_location:
        return False
    
    # Match by asset type
    asset_types = buyer.get('asset_types', '').split(',')
    asset_types = [a.strip() for a in asset_types if a.strip()]
    
    if asset_types and deal.get('asset_type') not in asset_types:
        return False
    
    # Match by budget
    price = deal.get('price', 0)
    min_budget = buyer.get('min_budget', 0)
    max_budget = buyer.get('max_budget', 1000000)
    
    if price < min_budget or price > max_budget:
        return False
    
    return True


def send_deal_email(buyer_email, buyer_name, deals):
    """Send deal notification email via SendGrid"""
    if not SENDGRID_API_KEY:
        logger.warning("SENDGRID_API_KEY not set, skipping email")
        return False
    
    if not deals:
        return False
    
    # Build HTML content
    deal_html = ""
    for deal in deals:
        score_color = "green" if deal['score'] >= 15 else "orange" if deal['score'] >= 7 else "red"
        deal_html += f"""
        <div style="border:1px solid #ddd; padding:15px; margin:10px 0; border-left:5px solid {score_color}">
            <h3>{deal.get('asset_type', 'Unknown').title()} - {deal.get('location', 'Unknown')}</h3>
            <p><strong>Price:</strong> ${deal.get('price', 0):,.0f}</p>
            <p><strong>Score:</strong> {deal.get('score', 0)}/100</p>
            <p>{deal.get('description', '')[:200]}...</p>
            <p style="color:#666; font-size:12px">{deal.get('created_at')}</p>
        </div>
        """
    
    html = f"""
    <html>
        <body style="font-family:Arial,sans-serif; max-width:600px; margin:0 auto;">
            <h2>New Deals for You - VortexAI</h2>
            <p>Hi {buyer_name},</p>
            <p>We found {len(deals)} new deal(s) matching your criteria:</p>
            {deal_html}
            <p><a href="https://real-estate-scraper-production.up.railway.app/buyer">View All Deals →</a></p>
            <hr>
            <p style="color:#999; font-size:12px">VortexAI Deal Matcher | Real Estate Automation</p>
        </body>
    </html>
    """
    
    payload = {
        "personalizations": [
            {
                "to": [{"email": buyer_email, "name": buyer_name}],
                "subject": f"🔥 {len(deals)} New Deal(s) Matching Your Criteria!"
            }
        ],
        "from": {
            "email": SENDGRID_FROM_EMAIL,
            "name": "VortexAI Deals"
        },
        "content": [
            {
                "type": "text/html",
                "value": html
            }
        ]
    }
    
    try:
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=payload,
            headers={"Authorization": f"Bearer {SENDGRID_API_KEY}"}
        )
        
        if response.status_code in [200, 202]:
            logger.info(f"Email sent to {buyer_email}")
            return True
        else:
            logger.error(f"SendGrid error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False


def mark_deals_as_sent(deal_ids):
    """Mark deals as sent to buyers"""
    if not deal_ids:
        return
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        placeholders = ','.join(['%s'] * len(deal_ids))
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
        logger.error(f"Error marking deals as sent: {e}")


def run_buyer_notifications():
    """Main function to send deals to buyers"""
    logger.info("Starting buyer notifications...")
    
    buyers = get_buyers()
    if not buyers:
        logger.info("No active buyers found")
        return {"sent": 0, "deals_matched": 0}
    
    deals = get_recent_deals(minutes=30)
    if not deals:
        logger.info("No recent deals found")
        return {"sent": 0, "deals_matched": 0}
    
    total_sent = 0
    total_matched = 0
    sent_deal_ids = set()
    
    for buyer in buyers:
        # Find matching deals for this buyer
        matching_deals = [d for d in deals if matches_buyer_criteria(d, buyer)]
        
        if matching_deals:
            # Send email
            success = send_deal_email(buyer['email'], buyer['name'], matching_deals)
            if success:
                total_sent += 1
                # Track which deals were sent
                for deal in matching_deals:
                    sent_deal_ids.add(deal['id'])
                total_matched += len(matching_deals)
    
    # Mark deals as sent
    if sent_deal_ids:
        mark_deals_as_sent(list(sent_deal_ids))
    
    result = {"sent": total_sent, "deals_matched": total_matched}
    logger.info(f"Buyer notification complete: {result}")
    return result


if __name__ == "__main__":
    run_buyer_notifications()
