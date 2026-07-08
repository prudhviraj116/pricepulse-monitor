import re
import random
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
from .headers import get_safe_headers

def detect_domain_key(url: str) -> Optional[str]:
    """
    Detects which scrapable domain the URL belongs to.
    Supports books.toscrape.com, webscraper.io, amazon, and flipkart.
    """
    url_lower = url.lower()
    if "books.toscrape.com" in url_lower:
        return "books_toscrape"
    elif "webscraper.io" in url_lower:
        return "webscraper_io"
    elif "amazon." in url_lower or "amazon/dp/" in url_lower:
        return "amazon"
    elif "flipkart.com" in url_lower:
        return "flipkart"
    return None

def clean_price(price_text: str) -> Optional[float]:
    """
    Extracts the numeric float value from a price string (e.g. '£51.77', '$1,143.40', '₹24,999' -> 51.77, 1143.40, 24999.00).
    """
    if not price_text:
        return None
    # Find numbers with decimals
    match = re.search(r'[\d\.,]+', price_text)
    if match:
        raw_val = match.group(0)
        # Remove commas just in case of format like 1,143.40
        raw_val = raw_val.replace(',', '')
        try:
            return float(raw_val)
        except ValueError:
            return None
    return None

def scrape_product(url: str, selector_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Scrapes the product URL using BeautifulSoup4 with header rotation.
    Supports a mock query parameter to simulate successful scrapes and bypass bot checks.
    Returns a dict with: {'success': bool, 'title': str, 'price': float, 'error': str}
    """
    if not selector_key:
        selector_key = detect_domain_key(url)
        if not selector_key:
            return {
                "success": False,
                "title": None,
                "price": None,
                "error": "Unsupported domain. Supported: books.toscrape.com, webscraper.io, amazon, flipkart"
            }

    # Simulation / Demo fallback mode (checks for ?mock=true)
    if "mock=true" in url.lower():
        sim_price = round(random.uniform(45.00, 53.00), 2)
        if selector_key == "amazon":
            return {"success": True, "title": "Amazon Product - Simulated Demo", "price": sim_price, "error": None}
        elif selector_key == "flipkart":
            return {"success": True, "title": "Flipkart Product - Simulated Demo", "price": sim_price, "error": None}
        elif selector_key == "books_toscrape":
            return {"success": True, "title": "Books To Scrape - Simulated Demo", "price": sim_price, "error": None}
        else:
            return {"success": True, "title": "WebScraper.io - Simulated Demo", "price": sim_price, "error": None}

    # Rotate headers to prevent block bans
    headers = get_safe_headers()

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return {
                "success": False,
                "title": None,
                "price": None,
                "error": f"HTTP status code {response.status_code}. Anti-bot block triggered. Try appending ?mock=true to the URL for demo testing."
            }

        soup = BeautifulSoup(response.content, "html.parser")

        title = None
        price = None

        if selector_key == "books_toscrape":
            # Title is in <h1> on books.toscrape.com detail page
            h1_elem = soup.find("h1")
            if h1_elem:
                title = h1_elem.get_text(strip=True)
            
            # Price is in <p class="price_color">
            price_elem = soup.find("p", class_="price_color")
            if price_elem:
                price = clean_price(price_elem.get_text(strip=True))

        elif selector_key == "webscraper_io":
            # Title is in <h4 class="title card-title" itemprop="name"> or similar
            title_elem = soup.select_one(".caption .title")
            if not title_elem:
                title_elem = soup.find(itemprop="name")
            if title_elem:
                title = title_elem.get_text(strip=True)

            # Price is in <h4 class="price float-end pull-right" itemprop="offers"> -> <span itemprop="price">
            price_elem = soup.select_one(".caption .price")
            if not price_elem:
                price_elem = soup.find(itemprop="price")
            if price_elem:
                price = clean_price(price_elem.get_text(strip=True))

        elif selector_key == "amazon":
            # Title is in span#productTitle
            title_elem = soup.find("span", id="productTitle")
            if title_elem:
                title = title_elem.get_text(strip=True)

            # Price is in span.a-price span.a-offscreen
            price_elem = soup.select_one("span.a-price span.a-offscreen") or soup.select_one("#priceblock_ourprice") or soup.select_one("#priceblock_dealprice")
            if price_elem:
                price = clean_price(price_elem.get_text(strip=True))

        elif selector_key == "flipkart":
            # Title is typically in span.B_NuCI or span.VU-ZEa
            title_elem = soup.select_one("span.B_NuCI") or soup.select_one(".VU-ZEa")
            if title_elem:
                title = title_elem.get_text(strip=True)

            # Price is typically in div._30jeq3 or div.Nx92iy
            price_elem = soup.select_one("div._30jeq3") or soup.select_one(".Nx92iy")
            if price_elem:
                price = clean_price(price_elem.get_text(strip=True))

        if not title:
            # Fallback to page title if specific tag not found
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)

        if price is None:
            # Provide descriptive error if we got blocked
            if "captcha" in response.text.lower() or "robot" in response.text.lower():
                err_msg = "CAPTCHA/Robot verification blocked crawl. Try appending ?mock=true to the URL for demo testing."
            else:
                err_msg = "Could not extract price from HTML structure. Selector mismatch or page layout change."
            return {
                "success": False,
                "title": title,
                "price": None,
                "error": err_msg
            }

        return {
            "success": True,
            "title": title,
            "price": price,
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "title": None,
            "price": None,
            "error": str(e)
        }
