# Competitive Intelligence Dashboard: Saudi Luxury Fragrance

A freelance project for a client planning a heritage fragrance brand in Saudi Arabia.
It scrapes the full public catalog of an established competitor (Faisal AlDayel,
[faisalaldayel.com](https://faisalaldayel.com)) and turns it into a bilingual
(English / Arabic) strategy dashboard: where the competitor makes its money, which
price bands are open, which scent notes it leans on, and which launch messages to test.

## What's inside

| Section | What it answers |
| --- | --- |
| **Market Overview** | Price vs. review volume for every product, and a top-10 ranked by a Bayesian rating score (a 5.0 from one review can't beat 4.93 from 400). |
| **Pricing Strategy** | How products and reviews spread across price tiers, and three pricing moves for the new brand. |
| **Scent Gaps** | Which fragrance notes the competitor uses most, detected from product descriptions. |
| **Pain Points & Ad Hooks** | Three category-level pain points with ad hooks in both languages, plus a **Review Evidence** section that tests them against the competitor's real customer reviews. |

Every number in the charts *and* in the strategy text is computed from the CSV when the
app loads. A fresh scrape updates everything together.

## Pipeline

```
sitemap.xml ──► product URLs (ar + en)
                     │
                     ▼
         product page ──► JSON-LD (name, description, price, rating, latest reviews)
                     └──► <meta product:*> (regular price, sale price, category)
                     │
                     ▼
       fragrance_notes.py (whole-word note detection, Arabic + English)
                     │
                     ▼
         faisalaldayel_intel.csv ──► app.py (Streamlit + Plotly)
```

## Run the dashboard

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Refresh the data

```bash
pip install -r scraper/requirements.txt
python scraper/scrape_faisalaldayel.py --out faisalaldayel_intel.csv

# quick test on 5 products
python scraper/scrape_faisalaldayel.py --limit 5 --out sample.csv
```

The scraper reads public pages only, respects `robots.txt`, and waits 1.5–2.25 s between
requests (`--delay` to change it). If the site starts returning 403, install Playwright
(`pip install playwright && playwright install chromium`) and add `--playwright`.

## Tests

```bash
pip install pytest
python -m pytest tests/
```

- `tests/test_scraper.py`: parsing of the sitemap, JSON-LD and meta tags, using trimmed
  copies of real pages in `tests/fixtures/`, plus the note matcher.
- `tests/test_app.py`: every dashboard section renders in both languages.

## Data notes and limits

- **Reviews are a proxy for sales.** Review counts show what customers engaged with, not
  units sold.
- **Review text is a sample.** Each product page publishes its latest 5 reviews, so the
  Review Evidence section works on those, not the full history.
- **Notes come from descriptions.** A note counts once per product and only as a whole word
  (an early version counted "عود" inside "السعودية"). Descriptions don't always list every
  note, so the counts are lower bounds.
- **The pain points are hypotheses** drawn from common category complaints until the review
  evidence supports them.
- **The committed CSV is the May 2026 snapshot** (75 products). The review widget couldn't be
  read at that time, so it has no review text. Re-run the scraper for a current snapshot.

## Structure

```
app.py                        Streamlit dashboard
fragrance_notes.py            note lexicon + whole-word matching (shared)
faisalaldayel_intel.csv       data snapshot
scraper/
  scrape_faisalaldayel.py     catalog scraper
  requirements.txt
tests/
  test_scraper.py
  test_app.py
  fixtures/                   trimmed real pages for offline tests
```

## Stack

Python · requests · Streamlit · Plotly · pandas · pytest
