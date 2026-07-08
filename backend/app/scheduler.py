import os
import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from .database import SessionLocal
from . import models, scraper, alerts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurable trigger threshold (default is 0.0%, meaning any price at or below baseline triggers it)
ALERT_THRESHOLD_PERCENT = Decimal(os.getenv("ALERT_THRESHOLD_PERCENT", "0.0"))
# Configurable run interval (default 3600 seconds = 1 hour)
SCRAPE_INTERVAL_SECONDS = int(os.getenv("SCRAPE_INTERVAL_SECONDS", "3600"))

def should_trigger_alert(product: models.Product, competitor_url: models.CompetitorURL, current_scraped_price: Decimal) -> bool:
    """
    State tracking logic to prevent duplicate alerts/notification spam.
    Only triggers if the price drop exceeds the product's threshold percent
    AND it is either the first alert or a new, deeper drop than the last notified price.
    """
    p_base = product.target_price
    p_current = current_scraped_price
    delta_p = ((p_base - p_current) / p_base) * Decimal("100.0")
    
    if delta_p >= product.alert_threshold_percent:
        if competitor_url.last_notified_price is not None:
            # If current price is higher or same as last notified price, do not alert
            if p_current >= competitor_url.last_notified_price:
                return False
        return True
    return False

def run_scraping_cycle(db: Session) -> dict:
    """
    Executes a single scraping cycle for all active competitor URLs.
    Can be triggered manually by API or automatically by the scheduler.
    """
    logger.info("Starting scraping cycle...")
    
    # Get active competitor URLs (where product is active and URL is active)
    competitors = (
        db.query(models.CompetitorURL)
        .join(models.Product)
        .filter(models.Product.is_active == True)
        .filter(models.CompetitorURL.is_active == True)
        .all()
    )
    
    results = {
        "processed": 0,
        "successful": 0,
        "failed": 0,
        "alerts_triggered": 0,
        "details": []
    }
    
    for comp in competitors:
        results["processed"] += 1
        product = comp.product
        user = product.user
        
        logger.info(f"Scraping competitor URL {comp.url} for product '{product.name}'")
        
        scrape_res = scraper.scrape_product(comp.url, comp.domain_selector_key)
        
        if not scrape_res["success"]:
            # Scraping failed: track safety details
            error_msg = scrape_res["error"] or "Unknown scraping error"
            logger.warning(f"Failed to scrape {comp.url}: {error_msg}")
            
            comp.error_count += 1
            comp.last_error_message = error_msg
            
            # Auto-disable if failure repeats more than 5 times
            if comp.error_count > 5:
                comp.is_active = False
                logger.error(f"URL disabled automatically due to repeated failures (>5): {comp.url}")
            
            db.commit()
            
            results["failed"] += 1
            results["details"].append({
                "competitor_url_id": comp.id,
                "url": comp.url,
                "success": False,
                "error": error_msg,
                "error_count": comp.error_count,
                "is_active": comp.is_active
            })
            continue
            
        # Scraping succeeded: reset safety tracking
        comp.error_count = 0
        comp.last_error_message = None
        
        current_price = Decimal(str(scrape_res["price"]))
        previous_price = comp.last_scraped_price
        
        # Save to Price History
        history_entry = models.PriceHistory(
            competitor_url_id=comp.id,
            price=current_price,
            scraped_at=datetime.utcnow()
        )
        db.add(history_entry)
        
        # Update competitor url record
        comp.last_scraped_price = current_price
        comp.last_scraped_at = datetime.utcnow()
        
        # Calculate percentage price drop compared to target baseline price (P_base)
        p_base = product.target_price
        delta_p = ((p_base - current_price) / p_base) * Decimal("100.0")
        
        # Run state boundary check
        triggered = should_trigger_alert(product, comp, current_price)
        
        # If the price went back up above threshold, we reset the last_notified_price
        if delta_p < product.alert_threshold_percent:
            comp.last_notified_price = None
        
        if triggered:
            recipient = user.email if user else "admin@pricepulse.local"
            logger.info(f"🚨 Price drop threshold reached for '{product.name}': {delta_p:.2f}% drop (Target: {p_base}, Competitor: {current_price})")
            
            # Send alert (saves to DB and sends email/logs)
            alerts.send_email_alert(
                db=db,
                product=product,
                competitor_url=comp,
                previous_price=previous_price,
                new_price=current_price,
                price_drop_percent=delta_p,
                recipient_email=recipient
            )
            
            # Update notified price state boundary
            comp.last_notified_price = current_price
            results["alerts_triggered"] += 1
            
        db.commit()
        results["successful"] += 1
        results["details"].append({
            "competitor_url_id": comp.id,
            "url": comp.url,
            "success": True,
            "previous_price": float(previous_price) if previous_price else None,
            "new_price": float(current_price),
            "price_drop_percent": float(delta_p),
            "alert_triggered": triggered
        })
        
    logger.info(f"Scraping cycle completed: {results['successful']} succeeded, {results['failed']} failed, {results['alerts_triggered']} alerts triggered.")
    return results

async def start_scheduler_loop():
    """
    Background loop that runs the scraping cycle periodically.
    """
    logger.info(f"Background price monitor scheduler started. Running every {SCRAPE_INTERVAL_SECONDS} seconds.")
    # Add a short delay on startup to let the app initialize
    await asyncio.sleep(5)
    
    while True:
        try:
            db = SessionLocal()
            try:
                run_scraping_cycle(db)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error in scheduler scraping cycle: {e}")
            
        await asyncio.sleep(SCRAPE_INTERVAL_SECONDS)
