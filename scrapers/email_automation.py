import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from datetime import datetime

logger = logging.getLogger(__name__)

class EmailAutomation:
    def __init__(self):
        self.sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        self.from_email = os.getenv('SENDER_EMAIL', 'noreply@wholesalingautomation.com')
    
    def send_property_alert(self, buyer_email: str, property_data: dict):
        try:
            subject = f"New Deal Alert: {property_data.get('address')}"
            content = f"""
            <h2>New Investment Property Available</h2>
            <p><strong>Address:</strong> {property_data.get('address')}</p>
            <p><strong>List Price:</strong> ${property_data.get('list_price'):,}</p>
            <p><strong>Estimated ARV:</strong> ${property_data.get('estimated_arv'):,}</p>
            <p><strong>Estimated Repairs:</strong> ${property_data.get('estimated_repairs'):,}</p>
            <p><strong>MAO:</strong> ${property_data.get('mao'):,}</p>
            <p><strong>Potential Assignment Fee:</strong> ${max(0, property_data.get('list_price', 0) - property_data.get('mao', 0)):,}</p>
            """
            
            message = Mail(
                from_email=self.from_email,
                to_emails=buyer_email,
                subject=subject,
                html_content=content
            )
            
            response = self.sg.send(message)
            logger.info(f"Property alert sent to {buyer_email}")
            return True
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    def send_daily_summary(self, recipient_email: str, summary_data: dict):
        try:
            subject = f"Daily Wholesaling Summary - {datetime.now().strftime('%Y-%m-%d')}"
            content = f"""
            <h2>Daily Wholesaling Summary</h2>
            <p><strong>Total Properties Found:</strong> {summary_data.get('total_properties', 0)}</p>
            <p><strong>High-Value Deals:</strong> {summary_data.get('quality_deals', 0)}</p>
            <p><strong>Total Potential Assignment Fees:</strong> ${summary_data.get('total_fees', 0):,}</p>
            <p><strong>Buyers Contacted:</strong> {summary_data.get('buyers_contacted', 0)}</p>
            """
            
            message = Mail(
                from_email=self.from_email,
                to_emails=recipient_email,
                subject=subject,
                html_content=content
            )
            
            response = self.sg.send(message)
            logger.info(f"Daily summary sent to {recipient_email}")
            return True
        except Exception as e:
            logger.error(f"Error sending summary: {e}")
            return False