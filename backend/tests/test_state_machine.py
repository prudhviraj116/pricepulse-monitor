import pytest
from decimal import Decimal
from app import models
from app.scheduler import should_trigger_alert

def test_should_trigger_alert_logic():
    # Setup test models
    product = models.Product(
        target_price=Decimal("100.00"),
        alert_threshold_percent=Decimal("5.00") # 5% drop required
    )
    
    comp_url = models.CompetitorURL(
        last_notified_price=None
    )
    
    # 1. Price drops to $98 (2% drop). This is below the 5% threshold, should NOT trigger.
    assert should_trigger_alert(product, comp_url, Decimal("98.00")) is False
    
    # 2. Price drops to $94 (6% drop). This is >= 5% threshold, and last_notified_price is None, should trigger.
    assert should_trigger_alert(product, comp_url, Decimal("94.00")) is True
    
    # Simulate saving alert state: update last_notified_price to $94.00
    comp_url.last_notified_price = Decimal("94.00")
    
    # 3. Next run: price is still $94.00. Same price, should NOT trigger (prevent spam).
    assert should_trigger_alert(product, comp_url, Decimal("94.00")) is False
    
    # 4. Next run: price goes slightly up to $95.00. Higher price, should NOT trigger.
    assert should_trigger_alert(product, comp_url, Decimal("95.00")) is False
    
    # 5. Next run: price drops further to $90.00 (10% drop). Lower than last notified ($94.00), should trigger.
    assert should_trigger_alert(product, comp_url, Decimal("90.00")) is True
    
    # Simulate saving alert state: update last_notified_price to $90.00
    comp_url.last_notified_price = Decimal("90.00")
    
    # 6. Next run: price rises back up to $99.00 (1% drop).
    # Since 1% drop is below the 5% threshold, alert doesn't trigger.
    assert should_trigger_alert(product, comp_url, Decimal("99.00")) is False
    
    # Simulate scheduler resetting last_notified_price when price rises back above threshold:
    # In scheduler.py, we have: if delta_p < threshold: comp.last_notified_price = None
    delta_p = ((product.target_price - Decimal("99.00")) / product.target_price) * Decimal("100.00")
    if delta_p < product.alert_threshold_percent:
        comp_url.last_notified_price = None
        
    assert comp_url.last_notified_price is None
    
    # 7. Next run: price drops back down to $94.00 (6% drop).
    # Since last_notified_price was reset, this is treated as a new drop event and should trigger!
    assert should_trigger_alert(product, comp_url, Decimal("94.00")) is True
