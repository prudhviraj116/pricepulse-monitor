import os
import requests
import logging
from typing import Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from . import models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config from environment variables
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "onboarding@resend.dev")

def send_email_alert(
    db: Session,
    product: models.Product,
    competitor_url: models.CompetitorURL,
    previous_price: Optional[Decimal],
    new_price: Decimal,
    price_drop_percent: Decimal,
    recipient_email: str
) -> models.SentAlert:
    """
    Saves the alert event to the database and dispatches a dynamic HTML email.
    If RESEND_API_KEY is configured, it uses Resend HTTP API to send the email.
    Otherwise, it logs the email contents to the terminal/logs.
    """
    # 1. Create a database record for this alert
    alert = models.SentAlert(
        product_id=product.id,
        competitor_url_id=competitor_url.id,
        previous_price=previous_price,
        new_price=new_price,
        price_drop_percent=price_drop_percent,
        recipient_email=recipient_email
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    # 2. Build email content
    subject = f"🚨 Price Drop Alert: {product.name} has dropped by {price_drop_percent:.1f}%!"
    
    prev_price_str = f"${previous_price:.2f}" if previous_price else "N/A"
    new_price_str = f"${new_price:.2f}"
    baseline_str = f"${product.target_price:.2f}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Price Drop Alert</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                color: #333333;
                background-color: #f9f9f9;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 600px;
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 30px;
                margin: 0 auto;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            }}
            .header {{
                text-align: center;
                border-bottom: 2px solid #edf2f7;
                padding-bottom: 20px;
                margin-bottom: 20px;
            }}
            .header h1 {{
                color: #e53e3e;
                font-size: 24px;
                margin: 0;
            }}
            .product-name {{
                font-size: 18px;
                font-weight: bold;
                color: #2d3748;
                margin-bottom: 15px;
            }}
            .details-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 25px;
            }}
            .details-table th, .details-table td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #edf2f7;
            }}
            .details-table th {{
                color: #718096;
                font-weight: 600;
            }}
            .details-table td {{
                color: #2d3748;
            }}
            .price-drop {{
                color: #38a169;
                font-weight: bold;
            }}
            .btn-container {{
                text-align: center;
                margin-top: 20px;
            }}
            .btn {{
                background-color: #3182ce;
                color: #ffffff !important;
                text-decoration: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                display: inline-block;
            }}
            .footer {{
                text-align: center;
                color: #a0aec0;
                font-size: 12px;
                margin-top: 30px;
                border-top: 1px solid #edf2f7;
                padding-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚨 Competitor Price Drop!</h1>
            </div>
            
            <p>Hello,</p>
            <p>One of your tracked competitor URLs has experienced a price drop that crossed your alert threshold.</p>
            
            <div class="product-name">Product: {product.name}</div>
            
            <table class="details-table">
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td>Your Target Baseline Price</td>
                    <td>{baseline_str}</td>
                </tr>
                <tr>
                    <td>Previous Scraped Competitor Price</td>
                    <td>{prev_price_str}</td>
                </tr>
                <tr>
                    <td>New Scraped Competitor Price</td>
                    <td class="price-drop">{new_price_str}</td>
                </tr>
                <tr>
                    <td>Percentage Drop</td>
                    <td class="price-drop">-{price_drop_percent:.2f}%</td>
                </tr>
            </table>
            
            <div class="btn-container">
                <a href="{competitor_url.url}" class="btn" target="_blank">View Competitor Deal</a>
            </div>
            
            <div class="footer">
                <p>This is an automated notification from your PricePulse Monitor system.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # 3. Deliver email
    if RESEND_API_KEY:
        logger.info(f"Dispatching real email via Resend to {recipient_email}")
        try:
            res = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": f"PricePulse Monitor <{SENDER_EMAIL}>",
                    "to": [recipient_email],
                    "subject": subject,
                    "html": html_content
                },
                timeout=10
            )
            if res.status_code == 200 or res.status_code == 201:
                logger.info("Resend email sent successfully.")
            else:
                logger.error(f"Resend returned error: {res.status_code} - {res.text}")
        except Exception as e:
            logger.error(f"Failed to dispatch email via Resend: {e}")
    else:
        # Mock mode
        logger.info("=" * 60)
        logger.info("[MOCK EMAIL DISPATCH]")
        logger.info(f"TO: {recipient_email}")
        logger.info(f"SUBJECT: {subject}")
        logger.info("-" * 60)
        logger.info(f"Product: {product.name}")
        logger.info(f"Your Target Baseline: {baseline_str}")
        logger.info(f"Previous Competitor Price: {prev_price_str}")
        logger.info(f"New Competitor Price: {new_price_str}")
        logger.info(f"Price Drop Percentage: {price_drop_percent:.2f}%")
        logger.info(f"URL: {competitor_url.url}")
        logger.info("=" * 60)

    return alert
