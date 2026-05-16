"""
SENETNAY Competitive Intelligence Scraper
==========================================
Target: faisalaldayel.com (TryOrder-platform luxury perfume storefront, Riyadh, est. 2002)
Purpose: Extract marketing-grade data to position SENETNAY against an established
         Gulf luxury fragrance house.

Engineering notes
-----------------
1. The site is JS-hydrated (TryOrder SPA). Requests+BS4 alone returns an empty shell.
   Selenium (headless Chrome) is the only reliable path.
2. The root domain returns 403 to bare scripts -> we MUST set a real UA, accept-language
   (ar,en-US), and use undetected-chromedriver to bypass bot fingerprinting.
3. Selectors are isolated in the SELECTORS dict at the top. The site is on a SaaS
   platform (TryOrder) whose DOM may change without notice; if a field comes back
   empty on first run, open one product page in DevTools and patch ONE string.
   Do not rewrite the script.
4. Politeness: 2-5s randomized delay between requests, 1 worker, full UA, robots
   respected (the site does not currently disallow /products in robots.txt -
   verify before each run).
5. Review text on TryOrder is usually rendered by a 3rd-party widget (Yotpo/Loox).
   The script attempts the inline ratings JSON-LD first, then falls back to
   widget scraping. If unreachable, the row records ratings/count but logs
   reviews_status='widget_unreachable' instead of fabricating data.

Usage
-----
    pip install selenium undetected-chromedriver beautifulsoup4 pandas tenacity
    python senetnay_scraper.py
"""

from __future__ import annotations

import csv
import json
import logging
import random
import re
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import pandas as pd
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tenacity import retry, stop_after_attempt, wait_exponential

# ============================================================================
# CONFIGURATION — edit selectors here if the site updates its DOM
# ============================================================================

BASE_URL = "https://faisalaldayel.com"
LISTING_PATHS = [
    "/en/products",
    "/en/categories",  # fallback if /products is gated
]

OUTPUT_CSV = Path("faisalaldayel_intel.csv")

MIN_DELAY_SEC = 2.0  # polite floor
MAX_DELAY_SEC = 5.0  # polite ceiling — random uniform between
PAGE_LOAD_TIMEOUT = 30
MAX_PAGES = 25       # safety cap on pagination

# CSS selectors — TryOrder platform conventions. Verify on first run.
SELECTORS = {
    # Listing page
    "product_card": "div.product-card, article.product, a.product-link, .product-item",
    "next_page_btn": "a[rel='next'], li.pagination-next a, button[aria-label='Next']",
    "product_link_in_card": "a[href*='/products/'], a[href*='/product/']",

    # Product detail page
    "product_title": "h1.product-title, h1[itemprop='name'], h1.title",
    "product_price": "span.price, [itemprop='price'], .product-price, .current-price",
    "product_price_compare": ".compare-price, .was-price, del.price",
    "product_description": (
        "div.product-description, [itemprop='description'], "
        ".product-details, .description-content"
    ),
    "product_notes_section": (
        ".fragrance-notes, .notes-section, "
        "div:has(> h2:contains('Notes')), div:has(> h3:contains('Notes'))"
    ),
    "rating_value": "[itemprop='ratingValue'], .rating-value, .stars-rating",
    "review_count": "[itemprop='reviewCount'], .review-count, .reviews-total",
    "reviews_container": ".reviews, #reviews, .product-reviews, [data-reviews]",
    "review_item": ".review-item, .review, [itemprop='review']",
    "review_text": ".review-body, .review-content, [itemprop='reviewBody']",
    "review_author": ".review-author, [itemprop='author']",
    "review_rating_individual": "[itemprop='ratingValue'], .review-rating",
}

# Keywords that signal fragrance notes inside free-text descriptions.
# Used as a fallback when no dedicated notes block exists. Bilingual — Arabic
# storefronts often label these in Arabic even on the /en/ pages.
NOTE_LABELS = [
    "top notes", "heart notes", "middle notes", "base notes", "notes:",
    "المقدمة", "القلب", "الأساس", "مكونات", "نوتات",  # Arabic equivalents
    "opening", "drydown", "dry down",
]

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("senetnay")


# ============================================================================
# DATA MODEL
# ============================================================================

@dataclass
class Product:
    """One row of the output CSV. Every field is marketing-relevant."""
    url: str
    name: str = ""
    name_ar: str = ""
    price_sar: Optional[float] = None
    price_compare_sar: Optional[float] = None       # original price if discounted
    discount_pct: Optional[float] = None
    currency: str = "SAR"
    category: str = ""                               # e.g. "Collection 1983"
    description: str = ""
    fragrance_notes_raw: str = ""                    # free-text containing notes
    top_notes: str = ""
    heart_notes: str = ""
    base_notes: str = ""
    rating_avg: Optional[float] = None
    review_count: Optional[int] = None
    review_texts: list = field(default_factory=list) # list of dicts
    reviews_status: str = "ok"                       # ok / widget_unreachable / none_found
    scraped_at: str = ""


# ============================================================================
# BROWSER
# ============================================================================

def build_driver() -> uc.Chrome:
    """undetected-chromedriver bypasses TryOrder's Cloudflare-ish 403."""
    opts = uc.ChromeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1440,900")
    opts.add_argument("--lang=en-US,en;q=0.9,ar;q=0.8")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    driver = uc.Chrome(options=opts, version_main=None)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    return driver


def polite_sleep() -> None:
    time.sleep(random.uniform(MIN_DELAY_SEC, MAX_DELAY_SEC))


# ============================================================================
# PARSERS
# ============================================================================

PRICE_RE = re.compile(r"([\d,]+(?:\.\d+)?)")

def parse_price(text: str) -> Optional[float]:
    """Strip 'SAR', 'ر.س', commas, whitespace -> float."""
    if not text:
        return None
    m = PRICE_RE.search(text.replace(",", ""))
    return float(m.group(1)) if m else None


def first_text(soup: BeautifulSoup, selector: str) -> str:
    el = soup.select_one(selector)
    return el.get_text(" ", strip=True) if el else ""


def extract_jsonld(soup: BeautifulSoup) -> dict:
    """
    Most SaaS storefronts emit a Product JSON-LD block. This is the
    GOLDEN PATH — when present, it gives us name, price, rating, and
    review count with zero CSS-selector fragility.
    """
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        # JSON-LD can be a list or a single object
        candidates = data if isinstance(data, list) else [data]
        for obj in candidates:
            if isinstance(obj, dict) and obj.get("@type") == "Product":
                return obj
    return {}


def split_notes(notes_text: str) -> dict:
    """
    Heuristic note splitter. Looks for 'Top: ... Heart: ... Base: ...'
    patterns in the description blob. Bilingual aware.
    """
    out = {"top_notes": "", "heart_notes": "", "base_notes": ""}
    if not notes_text:
        return out

    patterns = {
        "top_notes":   r"(?:top notes?|opening|المقدمة)\s*[:\-]\s*([^\.\n]+)",
        "heart_notes": r"(?:heart notes?|middle notes?|القلب)\s*[:\-]\s*([^\.\n]+)",
        "base_notes":  r"(?:base notes?|drydown|dry down|الأساس)\s*[:\-]\s*([^\.\n]+)",
    }
    for key, pat in patterns.items():
        m = re.search(pat, notes_text, flags=re.IGNORECASE)
        if m:
            out[key] = m.group(1).strip(" ,.")
    return out


def looks_like_notes_paragraph(text: str) -> bool:
    """Cheap detector: does this paragraph mention any note label?"""
    t = text.lower()
    return any(lbl in t for lbl in NOTE_LABELS)


# ============================================================================
# SCRAPER STAGES
# ============================================================================

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, max=20))
def fetch(driver: uc.Chrome, url: str) -> str:
    """Load a URL, wait for body, return rendered HTML. Retries on transient fail."""
    log.info("GET %s", url)
    driver.get(url)
    WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    # Give SPA hydration a moment — TryOrder lazy-loads product cards
    time.sleep(2.5)
    return driver.page_source


def discover_product_urls(driver: uc.Chrome) -> list[str]:
    """Walk listing pages, collect product detail URLs. Deduplicated."""
    seen: set[str] = set()
    ordered: list[str] = []

    for path in LISTING_PATHS:
        page_url = urljoin(BASE_URL, path)
        for page_num in range(1, MAX_PAGES + 1):
            current = f"{page_url}?page={page_num}" if page_num > 1 else page_url
            try:
                html = fetch(driver, current)
            except (TimeoutException, WebDriverException) as e:
                log.warning("Listing fetch failed at %s: %s", current, e)
                break

            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select(SELECTORS["product_card"])
            if not cards:
                log.info("No cards on %s — end of pagination or wrong path", current)
                break

            new_on_page = 0
            for card in cards:
                link_el = card if card.name == "a" else card.select_one(
                    SELECTORS["product_link_in_card"]
                )
                if not link_el or not link_el.get("href"):
                    continue
                href = urljoin(BASE_URL, link_el["href"])
                if href not in seen:
                    seen.add(href)
                    ordered.append(href)
                    new_on_page += 1

            log.info("Page %d on %s: %d new products (total %d)",
                     page_num, path, new_on_page, len(ordered))

            if new_on_page == 0:
                break  # pagination exhausted
            polite_sleep()

        if ordered:
            break  # successful path — don't hit the fallback

    return ordered


def scrape_product(driver: uc.Chrome, url: str) -> Product:
    """Pull the full marketing payload for one product."""
    p = Product(url=url, scraped_at=time.strftime("%Y-%m-%d %H:%M:%S"))

    try:
        html = fetch(driver, url)
    except Exception as e:
        log.error("Product fetch failed %s: %s", url, e)
        return p

    soup = BeautifulSoup(html, "html.parser")

    # ---- Golden path: JSON-LD ----
    jsonld = extract_jsonld(soup)
    if jsonld:
        p.name = jsonld.get("name", "") or p.name
        offers = jsonld.get("offers", {})
        if isinstance(offers, list) and offers:
            offers = offers[0]
        if isinstance(offers, dict):
            p.price_sar = parse_price(str(offers.get("price", "")))
            p.currency = offers.get("priceCurrency", "SAR")
        agg = jsonld.get("aggregateRating", {})
        if isinstance(agg, dict):
            try:
                p.rating_avg = float(agg.get("ratingValue", 0)) or None
                p.review_count = int(agg.get("reviewCount", 0)) or None
            except (TypeError, ValueError):
                pass
        p.description = jsonld.get("description", "") or p.description

    # ---- Fallback / supplement: CSS selectors ----
    if not p.name:
        p.name = first_text(soup, SELECTORS["product_title"])
    if not p.price_sar:
        p.price_sar = parse_price(first_text(soup, SELECTORS["product_price"]))
    p.price_compare_sar = parse_price(first_text(soup, SELECTORS["product_price_compare"]))
    if p.price_compare_sar and p.price_sar and p.price_compare_sar > p.price_sar:
        p.discount_pct = round(
            (p.price_compare_sar - p.price_sar) / p.price_compare_sar * 100, 1
        )
    if not p.description:
        p.description = first_text(soup, SELECTORS["product_description"])
    if not p.rating_avg:
        p.rating_avg = parse_price(first_text(soup, SELECTORS["rating_value"]))
    if not p.review_count:
        rc_text = first_text(soup, SELECTORS["review_count"])
        m = re.search(r"\d+", rc_text)
        if m:
            p.review_count = int(m.group(0))

    # ---- Fragrance notes extraction ----
    notes_block = first_text(soup, SELECTORS["product_notes_section"])
    if not notes_block:
        # Hunt note-bearing paragraphs in the description body
        for para in soup.select(f"{SELECTORS['product_description']} p, "
                                f"{SELECTORS['product_description']} li"):
            txt = para.get_text(" ", strip=True)
            if looks_like_notes_paragraph(txt):
                notes_block += " " + txt
    p.fragrance_notes_raw = notes_block.strip()
    note_parts = split_notes(p.fragrance_notes_raw or p.description)
    p.top_notes = note_parts["top_notes"]
    p.heart_notes = note_parts["heart_notes"]
    p.base_notes = note_parts["base_notes"]

    # ---- Review texts ----
    review_container = soup.select_one(SELECTORS["reviews_container"])
    if not review_container:
        p.reviews_status = "widget_unreachable"
    else:
        items = review_container.select(SELECTORS["review_item"])
        if not items:
            p.reviews_status = "none_found"
        for item in items[:30]:  # cap per product to keep CSV sane
            p.review_texts.append({
                "author": first_text(item, SELECTORS["review_author"]),
                "rating": parse_price(first_text(item, SELECTORS["review_rating_individual"])),
                "text": first_text(item, SELECTORS["review_text"]),
            })

    log.info(
        "  -> %s | %s SAR | rating=%s | reviews=%s | review_texts=%d",
        (p.name or "??")[:40],
        p.price_sar, p.rating_avg, p.review_count, len(p.review_texts),
    )
    return p


# ============================================================================
# OUTPUT
# ============================================================================

def write_csv(products: list[Product], path: Path) -> None:
    """Flatten and write. review_texts is JSON-encoded into one cell."""
    rows = []
    for p in products:
        d = asdict(p)
        d["review_texts"] = json.dumps(d["review_texts"], ensure_ascii=False)
        rows.append(d)
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_ALL)
    log.info("Wrote %d rows -> %s", len(rows), path.resolve())


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:
    driver = build_driver()
    try:
        log.info("=== Stage 1: discovering product URLs ===")
        urls = discover_product_urls(driver)
        log.info("Discovered %d unique product URLs", len(urls))

        if not urls:
            log.error("No products found. Open the site in a real browser, "
                      "inspect a product card, and update SELECTORS['product_card'].")
            return

        log.info("=== Stage 2: scraping product detail pages ===")
        products = []
        for i, url in enumerate(urls, 1):
            log.info("[%d/%d] %s", i, len(urls), url)
            products.append(scrape_product(driver, url))
            polite_sleep()

        log.info("=== Stage 3: writing CSV ===")
        write_csv(products, OUTPUT_CSV)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()