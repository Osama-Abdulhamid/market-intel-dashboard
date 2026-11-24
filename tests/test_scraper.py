"""Offline tests for the scraper's parsing logic and the note matcher.

Fixtures are trimmed copies of real faisalaldayel.com pages (Nov 2026).
Run:  python -m pytest tests/
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scraper"))

from fragrance_notes import find_notes  # noqa: E402
import scrape_faisalaldayel as s  # noqa: E402

FIX = Path(__file__).parent / "fixtures"


def read(name):
    return (FIX / name).read_text(encoding="utf-8")


def test_sitemap_index_and_products():
    children, pages = s.parse_sitemap(read("sitemap_index.xml"))
    assert len(children) == 2 and pages == []
    _, pages = s.parse_sitemap(read("sitemap_products.xml"))
    products = s.group_product_urls(pages)
    assert set(products) == {"353151008", "1343253445"}
    assert products["353151008"]["en"].endswith("/en/green/p353151008")
    assert "en" not in products["1343253445"]


def test_build_row_regular_product():
    row = s.build_row(read("product_ar_green.html"),
                      "https://faisalaldayel.com/ar/green/p353151008",
                      read("product_en_green.html"), "2026-11-24 07:00:00")
    assert row["name"] == "Green - 1983"
    assert row["name_ar"] == "الأخضر - 1983"
    assert row["price_sar"] == 285.0
    assert row["price_compare_sar"] == "" and row["discount_pct"] == ""
    assert row["review_count"] == 586
    assert abs(row["rating_avg"] - 4.942) < 0.001
    assert row["category"] == "جميع المنتجات"
    assert len(json.loads(row["review_texts"])) == 3
    assert row["reviews_status"] == "jsonld_latest_3"
    assert set(row) == set(s.COLUMNS)


def test_build_row_sale_product():
    row = s.build_row(read("product_ar_sale.html"), "u", None, "t")
    assert row["price_sar"] == 199.0
    assert row["price_compare_sar"] == 399.0
    assert row["discount_pct"] == 50.1
    assert row["review_count"] == ""          # no aggregateRating on the page
    assert row["reviews_status"] == "no_reviews"


def test_notes_whole_word_arabic():
    # "السعودية" (Saudi) must not count as oud
    assert "Oud" not in find_notes("القهوة السعودية الأصيلة")
    assert "Oud" in find_notes("مزيج من العود والعنبر")
    assert "Oud" in find_notes("بالعود")
    assert find_notes("بنكهة اللافندر مع الباتشولي") == ["Patchouli", "Lavender"]
    assert "Rose" not in find_notes("لون وردي")          # pink, not rose


def test_notes_english():
    assert find_notes("Top notes of Oud and Saffron") == ["Oud", "Saffron"]
    assert find_notes("") == [] and find_notes(None) == []


def test_pyramid():
    p = s.parse_pyramid("المقدمة: زعفران، هيل\nالقلب: ورد\nالقاعدة: عود، مسك")
    assert p == {"top_notes": "زعفران، هيل", "heart_notes": "ورد", "base_notes": "عود، مسك"}
