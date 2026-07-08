import pytest
from app import scraper

def test_clean_price():
    assert scraper.clean_price("£51.77") == 51.77
    assert scraper.clean_price("$1,143.40") == 1143.40
    assert scraper.clean_price("$1143.4") == 1143.4
    assert scraper.clean_price("₹24,999.00") == 24999.00
    assert scraper.clean_price("₹24,999") == 24999.00
    assert scraper.clean_price("Price: 9.99 USD") == 9.99
    assert scraper.clean_price("No price here") is None

def test_detect_domain_key():
    assert scraper.detect_domain_key("http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html") == "books_toscrape"
    assert scraper.detect_domain_key("https://webscraper.io/test-sites/e-commerce/allinone/product/110") == "webscraper_io"
    assert scraper.detect_domain_key("https://www.amazon.com/Apple-iPhone-15-Pro-128GB/dp/B0CHX75B76") == "amazon"
    assert scraper.detect_domain_key("https://www.flipkart.com/apple-iphone-15-pro-black-titanium-128-gb/p/itm548b") == "flipkart"
    assert scraper.detect_domain_key("https://another-site.com/product/123") is None

def test_live_scrape_books_toscrape():
    url = "http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
    res = scraper.scrape_product(url)
    assert res["success"] is True
    assert res["title"] == "A Light in the Attic"
    assert res["price"] > 0
    assert res["error"] is None

def test_live_scrape_webscraper_io():
    url = "https://webscraper.io/test-sites/e-commerce/allinone/product/110"
    res = scraper.scrape_product(url)
    assert res["success"] is True
    assert "Dell Latitude" in res["title"]
    assert res["price"] > 0
    assert res["error"] is None

def test_simulated_demo_mode():
    res = scraper.scrape_product("https://www.amazon.com/dp/B0CHX75B76?mock=true")
    assert res["success"] is True
    assert res["title"] == "Amazon Product - Simulated Demo"
    assert 45.00 <= res["price"] <= 53.00
    assert res["error"] is None

    res2 = scraper.scrape_product("https://www.flipkart.com/p/itm548b?mock=true")
    assert res2["success"] is True
    assert res2["title"] == "Flipkart Product - Simulated Demo"
    assert 45.00 <= res2["price"] <= 53.00
    assert res2["error"] is None

