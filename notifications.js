const nodemailer = require('nodemailer');
const twilio = require('twilio');
const { query } = require('../config/database');

// Email transporter (using Gmail as example)
const emailTransporter = process.env.EMAIL_HOST ? nodemailer.createTransport({
  host: process.env.EMAIL_HOST,
  port: process.env.EMAIL_PORT || 587,
  secure: false,
  auth: {
    user: process.env.EMAIL_USER,
    pass: process.env.EMAIL_PASS
  }
}) : null;

// Twilio client (for SMS)
const twilioClient = process.env.TWILIO_ACCOUNT_SID ? twilio(
  process.env.TWILIO_ACCOUNT_SID,
  process.env.TWILIO_AUTH_TOKEN
) : null;

/**
 * Send deal notification to buyer
 */
const notifyBuyer = async (match, deal, buyer) => {
  const notifications = [];

  try {
    // Send email
    if (buyer.email && emailTransporter) {
      const emailResult = await sendEmailNotification(match, deal, buyer);
      notifications.push(emailResult);
    }

    // Send SMS
    if (buyer.phone && twilioClient && match.match_score >= 80) {
      const smsResult = await sendSMSNotification(match, deal, buyer);
      notifications.push(smsResult);
    }

    // Log notifications
    for (const notification of notifications) {
      await query(
        `INSERT INTO notifications (match_id, buyer_id, type, channel, content, status, sent_at)
         VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP)`,
        [
          match.id,
          buyer.id,
          'deal_match',
          notification.channel,
          notification.content,
          notification.status
        ]
      );
    }

    // Update match as notified
    await query(
      `UPDATE matches SET notified_at = CURRENT_TIMESTAMP WHERE id = $1`,
      [match.id]
    );

    return notifications;
  } catch (error) {
    console.error('Error sending notifications:', error);
    throw error;
  }
};

/**
 * Send email notification
 */
const sendEmailNotification = async (match, deal, buyer) => {
  try {
    const emailHTML = generateDealEmailHTML(deal, match, buyer);
    
    const info = await emailTransporter.sendMail({
      from: `"VortexAI Deals" <${process.env.EMAIL_USER}>`,
      to: buyer.email,
      subject: `🔥 New Deal Alert: ${deal.title}`,
      html: emailHTML
    });

    console.log('✅ Email sent:', info.messageId);
    
    return {
      channel: 'email',
      content: emailHTML,
      status: 'sent',
      messageId: info.messageId
    };
  } catch (error) {
    console.error('Email error:', error);
    return {
      channel: 'email',
      content: '',
      status: 'failed',
      error: error.message
    };
  }
};

/**
 * Send SMS notification
 */
const sendSMSNotification = async (match, deal, buyer) => {
  try {
    const smsContent = `🔥 VortexAI Deal Alert!\n\n${deal.title}\n💰 $${deal.price.toLocaleString()}\n⭐ Score: ${deal.ai_score}/100\n\nView: ${process.env.FRONTEND_URL}/deals/${deal.id}`;
    
    const message = await twilioClient.messages.create({
      body: smsContent,
      from: process.env.TWILIO_PHONE_NUMBER,
      to: buyer.phone
    });

    console.log('✅ SMS sent:', message.sid);
    
    return {
      channel: 'sms',
      content: smsContent,
      status: 'sent',
      messageId: message.sid
    };
  } catch (error) {
    console.error('SMS error:', error);
    return {
      channel: 'sms',
      content: '',
      status: 'failed',
      error: error.message
    };
  }
};

/**
 * Generate HTML email template
 */
const generateDealEmailHTML = (deal, match, buyer) => {
  const discountBadge = deal.discount_percentage > 0 
    ? `<span style="background: #ef4444; color: white; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: bold;">${deal.discount_percentage.toFixed(0)}% OFF</span>`
    : '';

  const profitBadge = deal.profit_potential > 0
    ? `<div style="color: #10b981; font-weight: bold; margin-top: 8px;">💰 Potential Profit: $${deal.profit_potential.toLocaleString()}</div>`
    : '';

  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px; text-align: center;">
    <h1 style="margin: 0; font-size: 28px;">🔥 New Deal Alert!</h1>
    <p style="margin: 10px 0 0 0; opacity: 0.9;">Match Score: ${match.match_score}/100</p>
  </div>

  <div style="background: #f9fafb; padding: 30px; margin-top: 20px; border-radius: 8px;">
    <h2 style="margin: 0 0 15px 0; color: #1f2937;">${deal.title}</h2>
    
    <div style="margin: 15px 0;">
      ${discountBadge}
      <span style="background: #3b82f6; color: white; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-left: 8px;">AI Score: ${deal.ai_score}/100</span>
    </div>

    <div style="margin: 20px 0;">
      <div style="font-size: 32px; font-weight: bold; color: #10b981;">$${deal.price.toLocaleString()}</div>
      ${deal.market_value ? `<div style="color: #6b7280; text-decoration: line-through;">Market Value: $${deal.market_value.toLocaleString()}</div>` : ''}
      ${profitBadge}
    </div>

    ${deal.description ? `<p style="color: #4b5563; margin: 15px 0;">${deal.description.substring(0, 200)}${deal.description.length > 200 ? '...' : ''}</p>` : ''}

    <div style="margin: 20px 0; padding: 15px; background: white; border-radius: 6px;">
      <div style="color: #6b7280; font-size: 14px; margin-bottom: 8px;">📍 Location</div>
      <div style="font-weight: 600;">${deal.location || 'Not specified'}</div>
    </div>

    <div style="margin: 20px 0; padding: 15px; background: white; border-radius: 6px;">
      <div style="color: #6b7280; font-size: 14px; margin-bottom: 8px;">🏷️ Category</div>
      <div style="font-weight: 600; text-transform: capitalize;">${deal.category.replace('-', ' ')}</div>
    </div>

    ${deal.urgency_keywords && deal.urgency_keywords.length > 0 ? `
    <div style="margin: 20px 0; padding: 15px; background: #fef3c7; border-radius: 6px;">
      <div style="color: #92400e; font-weight: 600; margin-bottom: 8px;">⚡ Urgency Signals</div>
      <div style="color: #78350f;">${deal.urgency_keywords.join(', ')}</div>
    </div>
    ` : ''}

    <div style="text-align: center; margin-top: 30px;">
      <a href="${process.env.FRONTEND_URL || 'https://vortexai.com'}/deals/${deal.id}" 
         style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 40px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px;">
        View Full Details →
      </a>
    </div>
  </div>

  <div style="text-align: center; color: #9ca3af; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
    <p>You're receiving this because you match this deal based on your preferences.</p>
    <p><a href="${process.env.FRONTEND_URL}/unsubscribe/${buyer.id}" style="color: #6b7280;">Unsubscribe</a> | <a href="${process.env.FRONTEND_URL}/preferences/${buyer.id}" style="color: #6b7280;">Update Preferences</a></p>
  </div>
</body>
</html>
  `;
};

module.exports = {
  notifyBuyer,
  sendEmailNotification,
  sendSMSNotification
};
