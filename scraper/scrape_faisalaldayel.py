"""
Faisal AlDayel catalog scraper
==============================
Collects the public product catalog of faisalaldayel.com (a Salla store) into
the CSV the dashboard reads (faisalaldayel_intel.csv).

How it works
------------
1. Reads the public sitemap to get every product URL (Arabic + English).
2. Opens each product page and reads what the page already publishes:
   - JSON-LD (schema.org Product): name, description, price,
     average rating, rating count, and the latest customer reviews.
   - <meta property="product:..."> tags: regular price, sale price, category.
3. Detects fragrance notes in the description (see fragrance_notes.py).
4. Writes one row per product.

It only reads public pages, respects robots.txt, and waits between requests.

Usage
-----
    pip install -r scraper/requirements.txt
    python scraper/scrape_faisalaldayel.py --out faisalaldayel_intel.csv

    # quick test on 5 products
    python scraper/scrape_faisalaldayel.py --limit 5 --out sample.csv

If the site starts answering with 403 (bot protection), install Playwright
(`pip install playwright && playwright install chromium`) and add --playwright.
"""

from __future__ import annotations

import argparse
import csv
import html as html_lib
import json
import random
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib import robotparser

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fragrance_notes import find_notes  # noqa: E402

BASE = "https://faisalaldayel.com"
SITEMAP_URL = f"{BASE}/sitemap.xml"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

COLUMNS = [
    "url", "name", "name_ar", "price_sar", "price_compare_sar", "discount_pct",
    "currency", "category", "description", "fragrance_notes_raw", "top_notes",
    "heart_notes", "base_notes", "rating_avg", "review_count", "review_texts",
    "reviews_status", "scraped_at",
]

PRODUCT_URL_RE = re.compile(r"/(ar|en)/[^/]+/p(\d+)/?$")
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

class Fetcher:
    """requests by default; Playwright when --playwright is passed."""

    def __init__(self, use_playwright: bool = False, delay: float = 1.5):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept-Language": "ar,en;q=0.8",
        })
        self._pw = self._browser = self._page = None
        if use_playwright:
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=True)
            self._page = self._browser.new_page(user_agent=USER_AGENT)

        self.robots = robotparser.RobotFileParser()
        try:
            r = self.session.get(f"{BASE}/robots.txt", timeout=20)
            self.robots.parse(r.text.splitlines() if r.ok else [])
        except requests.RequestException:
            self.robots.parse([])

    def get(self, url: str, retries: int = 3) -> tuple[int, str]:
        if not self.robots.can_fetch(USER_AGENT, url):
            return 999, ""
        for attempt in range(1, retries + 1):
            try:
                if self._page is not None:
                    resp = self._page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    status, text = (resp.status if resp else 0), self._page.content()
                else:
                    r = self.session.get(url, timeout=30)
                    status, text = r.status_code, r.text
            except Exception as exc:  # network error: retry
                status, text = 0, str(exc)
            if status in (429, 500, 502, 503, 504, 0) and attempt < retries:
                time.sleep(self.delay * 2 ** attempt)
                continue
            return status, text
        return status, text

    def pause(self) -> None:
        time.sleep(self.delay + random.uniform(0, self.delay / 2))

    def close(self) -> None:
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()


# ---------------------------------------------------------------------------
# Parsing (pure functions, covered by tests/)
# ---------------------------------------------------------------------------

def parse_sitemap(xml_text: str) -> tuple[list[str], list[str]]:
    """Return (child sitemap URLs, page URLs) from a sitemap or sitemap index."""
    root = ET.fromstring(xml_text.encode("utf-8"))
    children = [e.text.strip() for e in root.findall("sm:sitemap/sm:loc", SITEMAP_NS) if e.text]
    pages = [e.text.strip() for e in root.findall("sm:url/sm:loc", SITEMAP_NS) if e.text]
    return children, pages


def group_product_urls(urls: list[str]) -> dict[str, dict[str, str]]:
    """{product_id: {"ar": url, "en": url}}"""
    products: dict[str, dict[str, str]] = {}
    for u in urls:
        m = PRODUCT_URL_RE.search(u)
        if m:
            lang, pid = m.groups()
            products.setdefault(pid, {})[lang] = u
    return products


def parse_jsonld_product(page_html: str) -> dict:
    """Find the schema.org Product object in the page's JSON-LD blocks."""
    blocks = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        page_html, flags=re.S | re.I,
    )
    for raw in blocks:
        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError:
            continue
        candidates = data.get("@graph", [data]) if isinstance(data, dict) else data
        for obj in candidates if isinstance(candidates, list) else [candidates]:
            if isinstance(obj, dict) and obj.get("@type") == "Product":
                return obj
    return {}


def parse_meta(page_html: str) -> dict[str, str]:
    """All <meta property="..." content="..."> pairs, either attribute order."""
    out: dict[str, str] = {}
    for tag in re.findall(r"<meta\b[^>]*>", page_html, flags=re.I):
        prop = re.search(r'property=["\']([^"\']+)["\']', tag)
        content = re.search(r'content=["\']([^"\']*)["\']', tag)
        if prop and content:
            out[prop.group(1)] = html_lib.unescape(content.group(1))
    return out


_PYRAMID = {
    "top_notes":   r"(?:top notes?|head notes?|المقدمة|النفحات العليا|النوتات العليا|القمة)",
    "heart_notes": r"(?:heart notes?|middle notes?|القلب|النفحات الوسطى|النوتات الوسطى)",
    "base_notes":  r"(?:base notes?|القاعدة|النفحات الأساسية|النوتات الأساسية)",
}
_ANY_LABEL = "|".join(_PYRAMID.values())


def parse_pyramid(description: str) -> dict[str, str]:
    """Best effort: pull 'Top notes: ...' style sections out of the description."""
    out = {k: "" for k in _PYRAMID}
    if not description:
        return out
    for key, label in _PYRAMID.items():
        m = re.search(
            rf"{label}\s*[:：\-–]\s*(.+?)(?=(?:{_ANY_LABEL})\s*[:：\-–]|\n|$)",
            description, flags=re.I | re.S,
        )
        if m:
            out[key] = m.group(1).strip(" .،,")
    return out


def _num(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_row(ar_html: str, url: str, en_html: str | None, scraped_at: str) -> dict:
    product = parse_jsonld_product(ar_html)
    meta = parse_meta(ar_html)
    offers = product.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}

    price = _num(meta.get("product:sale_price:amount")) or _num(offers.get("price"))
    regular = _num(meta.get("product:price:amount"))
    compare = regular if (regular and price and regular > price) else None
    discount = round((compare - price) / compare * 100, 1) if compare else None

    agg = product.get("aggregateRating") or {}
    rating = _num(agg.get("ratingValue"))
    count = int(_num(agg.get("ratingCount") or agg.get("reviewCount")) or 0)

    reviews = product.get("review") or []
    if isinstance(reviews, dict):
        reviews = [reviews]
    texts = [r.get("reviewBody", "").strip() for r in reviews if r.get("reviewBody")]

    if texts:
        status = f"jsonld_latest_{len(texts)}"
    elif count == 0:
        status = "no_reviews"
    else:
        status = "jsonld_no_review_text"

    description = (product.get("description") or "").strip()
    pyramid = parse_pyramid(description)
    name_ar = (product.get("name") or "").strip()
    name_en = (parse_jsonld_product(en_html).get("name") or "").strip() if en_html else ""

    return {
        "url": url,
        "name": name_en or name_ar,
        "name_ar": name_ar,
        "price_sar": price if price is not None else "",
        "price_compare_sar": compare if compare is not None else "",
        "discount_pct": discount if discount is not None else "",
        "currency": offers.get("priceCurrency") or meta.get("product:price:currency") or "SAR",
        "category": meta.get("product:category", ""),
        "description": description,
        "fragrance_notes_raw": "|".join(find_notes(description)),
        **pyramid,
        "rating_avg": round(rating, 4) if rating is not None else "",
        "review_count": count if agg else "",
        "review_texts": json.dumps(texts, ensure_ascii=False),
        "reviews_status": status,
        "scraped_at": scraped_at,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def collect_product_urls(fetcher: Fetcher) -> dict[str, dict[str, str]]:
    status, text = fetcher.get(SITEMAP_URL)
    if status != 200:
        sys.exit(f"Could not read the sitemap ({status}). Try --playwright.")
    children, pages = parse_sitemap(text)
    for child in children:
        fetcher.pause()
        s, t = fetcher.get(child)
        if s == 200:
            pages += parse_sitemap(t)[1]
        else:
            print(f"  ! sitemap {child} -> {s}", file=sys.stderr)
    return group_product_urls(pages)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="faisalaldayel_intel.csv")
    ap.add_argument("--delay", type=float, default=1.5, help="seconds between requests")
    ap.add_argument("--limit", type=int, default=0, help="only scrape the first N products")
    ap.add_argument("--no-english", action="store_true", help="skip English pages (half the requests)")
    ap.add_argument("--playwright", action="store_true", help="fetch pages with a headless browser")
    args = ap.parse_args()

    fetcher = Fetcher(use_playwright=args.playwright, delay=args.delay)
    try:
        products = collect_product_urls(fetcher)
        ids = sorted(products)
        if args.limit:
            ids = ids[: args.limit]
        print(f"Found {len(products)} products in the sitemap, scraping {len(ids)}.")

        rows, failed = [], []
        scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for i, pid in enumerate(ids, 1):
            urls = products[pid]
            url = urls.get("ar") or urls.get("en")
            fetcher.pause()
            status, ar_html = fetcher.get(url)
            if status != 200 or not parse_jsonld_product(ar_html):
                failed.append((url, status))
                print(f"[{i}/{len(ids)}] FAILED {status} {url}")
                continue
            en_html = None
            if not args.no_english and urls.get("en") and urls.get("en") != url:
                fetcher.pause()
                s, t = fetcher.get(urls["en"])
                en_html = t if s == 200 else None
            row = build_row(ar_html, url, en_html, scraped_at)
            rows.append(row)
            print(f"[{i}/{len(ids)}] {row['name'][:40]:40} {row['price_sar']} SAR  "
                  f"{row['review_count']} ratings")
    finally:
        fetcher.close()

    if not rows:
        sys.exit("No products scraped. If every request returned 403, try --playwright.")

    with open(args.out, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} products to {args.out}")
    if failed:
        print(f"{len(failed)} pages failed:")
        for url, status in failed:
            print(f"  {status}  {url}")


if __name__ == "__main__":
    main()
