"""
Competitor Intelligence Dashboard
==================================
A bilingual (English / Egyptian Arabic) strategic dashboard built on the
Faisal AlDayel scraped dataset (75 products).

Aesthetic direction: editorial luxury — dark, serif display, single warm accent.
Built deliberately to look like a fragrance-house strategy deck, not a SaaS tool.

Deployment
----------
    pip install -r requirements.txt
    streamlit run app.py

For Streamlit Cloud: push app.py, requirements.txt, and
faisalaldayel_intel.csv to a GitHub repo and connect at share.streamlit.io
"""

from __future__ import annotations

import base64
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ============================================================================
# PAGE CONFIG — must be the first Streamlit call
# ============================================================================

st.set_page_config(
    page_title="Competitive Intelligence — Luxury Fragrance",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# DESIGN SYSTEM — editorial luxury, dark mode, warm bronze accent
# ============================================================================

# Color tokens — committed palette, used everywhere consistently
INK = "#0E0D0B"           # near-black, page background
INK_RAISED = "#181614"    # one step lighter, for cards
INK_LINE = "#2A2622"      # divider lines
BONE = "#EDE6D6"          # primary text (warm cream, not pure white)
BONE_DIM = "#9A9388"      # secondary text
BRONZE = "#B08740"        # the single accent
BRONZE_DEEP = "#7A5A28"   # accent shadow
SAGE = "#5C6B58"          # one secondary accent for charts only
TERRACOTTA = "#A8503A"    # one tertiary accent for charts only

CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Manrope:wght@300;400;500;600;700&family=Tajawal:wght@300;400;500;700&display=swap');

/* ---------- global ---------- */
html, body, [class*="css"] {{
    font-family: 'Manrope', -apple-system, sans-serif;
}}

.stApp {{
    background: {INK};
    color: {BONE};
}}

.main .block-container {{
    padding-top: 2rem;
    padding-bottom: 4rem;
    max-width: 1280px;
}}

/* ---------- typography ---------- */
h1, h2, h3 {{
    font-family: 'Cormorant Garamond', serif !important;
    font-weight: 500 !important;
    letter-spacing: -0.01em;
    color: {BONE} !important;
}}

h1 {{
    font-size: 3.4rem !important;
    line-height: 1.05 !important;
    margin-bottom: 0.2rem !important;
}}

h2 {{
    font-size: 2.1rem !important;
    margin-top: 2.5rem !important;
    margin-bottom: 1.2rem !important;
    border-bottom: 1px solid {INK_LINE};
    padding-bottom: 0.6rem;
}}

h3 {{
    font-size: 1.5rem !important;
    color: {BRONZE} !important;
    margin-top: 1.8rem !important;
}}

p, li, span, label {{
    font-family: 'Manrope', sans-serif;
    color: {BONE};
    font-size: 0.96rem;
    line-height: 1.65;
}}

.eyebrow {{
    font-family: 'Manrope', sans-serif;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.22em;
    color: {BRONZE};
    margin-bottom: 0.4rem;
    display: block;
}}

.lede {{
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.35rem;
    line-height: 1.55;
    font-style: italic;
    color: {BONE_DIM};
    border-left: 2px solid {BRONZE};
    padding-left: 1.2rem;
    margin: 1.5rem 0 2rem 0;
}}

.fineprint {{
    font-size: 0.78rem;
    color: {BONE_DIM};
    font-style: italic;
}}

/* ---------- Arabic blocks ---------- */
.arabic-block {{
    font-family: 'Tajawal', 'Segoe UI', sans-serif;
    direction: rtl;
    text-align: right;
    line-height: 1.85;
    font-size: 1rem;
}}

.arabic-block h3, .arabic-block h4 {{
    font-family: 'Tajawal', sans-serif !important;
    font-weight: 700 !important;
    color: {BRONZE} !important;
    text-align: right;
}}

/* ---------- KPI cards ---------- */
[data-testid="stMetric"] {{
    background: {INK_RAISED};
    border: 1px solid {INK_LINE};
    padding: 1.4rem 1.5rem;
    border-radius: 2px;
    transition: border-color 0.3s ease;
}}

[data-testid="stMetric"]:hover {{
    border-color: {BRONZE_DEEP};
}}

[data-testid="stMetricLabel"] {{
    color: {BONE_DIM} !important;
    font-size: 0.7rem !important;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    font-weight: 600;
}}

[data-testid="stMetricValue"] {{
    font-family: 'Cormorant Garamond', serif !important;
    font-size: 2.6rem !important;
    color: {BONE} !important;
    font-weight: 500 !important;
}}

[data-testid="stMetricDelta"] {{
    color: {BRONZE} !important;
    font-size: 0.85rem !important;
}}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {{
    background: #0A0908;
    border-right: 1px solid {INK_LINE};
}}

[data-testid="stSidebar"] .stRadio label {{
    font-family: 'Manrope', sans-serif;
    color: {BONE_DIM};
    font-size: 0.95rem;
    padding: 0.5rem 0;
    transition: color 0.2s ease;
}}

[data-testid="stSidebar"] .stRadio label:hover {{
    color: {BONE};
}}

[data-testid="stSidebar"] h2 {{
    font-size: 1.6rem !important;
    border: none !important;
    margin-top: 0 !important;
}}

/* ---------- tables ---------- */
[data-testid="stDataFrame"] {{
    border: 1px solid {INK_LINE};
    border-radius: 2px;
}}

/* ---------- buttons / toggles ---------- */
.stRadio > div {{
    gap: 0.4rem;
}}

.stRadio > div[role="radiogroup"] > label {{
    background: {INK_RAISED};
    border: 1px solid {INK_LINE};
    padding: 0.45rem 1.1rem;
    border-radius: 2px;
    transition: all 0.2s ease;
}}

.stRadio > div[role="radiogroup"] > label:has(input:checked) {{
    background: {BRONZE_DEEP};
    border-color: {BRONZE};
    color: {BONE} !important;
}}

/* ---------- info / strategy boxes ---------- */
.strategy-card {{
    background: {INK_RAISED};
    border: 1px solid {INK_LINE};
    border-left: 3px solid {BRONZE};
    padding: 1.5rem 1.8rem;
    margin: 1.2rem 0;
    border-radius: 2px;
}}

.strategy-card h4 {{
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.4rem;
    margin: 0 0 0.6rem 0;
    color: {BONE};
    font-weight: 500;
}}

.strategy-card .label {{
    font-size: 0.68rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: {BRONZE};
    font-weight: 600;
    margin-bottom: 0.5rem;
    display: block;
}}

.pain-point {{
    background: linear-gradient(180deg, {INK_RAISED} 0%, #14110E 100%);
    border: 1px solid {INK_LINE};
    padding: 1.8rem 2rem;
    margin: 1rem 0;
    border-radius: 2px;
    position: relative;
}}

.pain-point::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 40px;
    height: 1px;
    background: {BRONZE};
}}

.pain-point-num {{
    font-family: 'Cormorant Garamond', serif;
    font-size: 0.8rem;
    color: {BRONZE};
    letter-spacing: 0.3em;
    text-transform: uppercase;
    margin-bottom: 0.4rem;
    display: block;
}}

.hook {{
    font-family: 'Cormorant Garamond', serif;
    font-style: italic;
    font-size: 1.15rem;
    color: {BONE};
    padding: 0.6rem 0 0.6rem 1.2rem;
    border-left: 2px solid {BRONZE_DEEP};
    margin: 0.6rem 0;
    line-height: 1.5;
}}

/* ---------- hide streamlit chrome ---------- */
#MainMenu, footer, header {{ visibility: hidden; }}

/* ---------- divider rule ---------- */
.rule {{
    border-top: 1px solid {INK_LINE};
    margin: 3rem 0 2rem 0;
    position: relative;
}}

.rule::after {{
    content: '◈';
    position: absolute;
    top: -10px;
    left: 50%;
    transform: translateX(-50%);
    background: {INK};
    padding: 0 1rem;
    color: {BRONZE};
    font-size: 0.8rem;
}}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ============================================================================
# DATA LOADING & PREP
# ============================================================================

@st.cache_data
def load_data() -> pd.DataFrame:
    """Load the scraped CSV. Falls back to relative path for Streamlit Cloud."""
    candidates = [
        Path("faisalaldayel_intel.csv"),
        Path("data/faisalaldayel_intel.csv"),
        Path("/mnt/user-data/uploads/faisalaldayel_intel.csv"),
    ]
    for p in candidates:
        if p.exists():
            df = pd.read_csv(p, encoding="utf-8-sig")
            break
    else:
        st.error("Data file 'faisalaldayel_intel.csv' not found. "
                 "Place it next to app.py before deploying.")
        st.stop()

    # Clean: numeric coercion + fillna(0) for ratings/reviews
    df["price_sar"] = pd.to_numeric(df["price_sar"], errors="coerce")
    df["rating_avg"] = pd.to_numeric(df["rating_avg"], errors="coerce").fillna(0)
    df["review_count"] = pd.to_numeric(df["review_count"], errors="coerce").fillna(0).astype(int)

    # Drop rows without a price (can't analyze)
    df = df[df["price_sar"].notna() & (df["price_sar"] > 0)].copy()

    # Display name — clean up whitespace
    df["display_name"] = df["name"].astype(str).str.strip()

    # Weighted top-seller score: a fair blend of popularity AND rating.
    # We shrink ratings toward the global mean by review count, so a 5.0 with
    # 1 review can't beat a 4.93 with 431 reviews. (Same logic IMDb uses.)
    rated = df[df["review_count"] > 0]
    C = rated["rating_avg"].mean() if len(rated) else 5.0
    m = df["review_count"].quantile(0.6)

    def score(row):
        v = row["review_count"]
        if v == 0:
            return 0.0
        R = row["rating_avg"]
        return (v / (v + m)) * R + (m / (v + m)) * C

    df["seller_score"] = df.apply(score, axis=1)

    # Price tier label for the scatter plot
    bins = [0, 150, 250, 400, 600, 1000, 5000]
    labels = ["Entry (<150)", "Mid (150–250)", "Premium (250–400)",
              "Luxury (400–600)", "Top (600–1000)", "Flagship (1000+)"]
    df["tier"] = pd.cut(df["price_sar"], bins=bins, labels=labels)

    return df


df = load_data()


# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown(f"""
        <div style='padding: 0.5rem 0 1.5rem 0; border-bottom: 1px solid {INK_LINE}; margin-bottom: 1.5rem;'>
            <div style='font-family: "Cormorant Garamond", serif; font-size: 1.7rem;
                        color: {BONE}; letter-spacing: 0.05em; line-height: 1;'>◈ Atelier</div>
            <div style='font-family: Manrope; font-size: 0.7rem; color: {BONE_DIM};
                        letter-spacing: 0.25em; text-transform: uppercase; margin-top: 0.4rem;'>
                Competitive Intelligence
            </div>
        </div>
    """, unsafe_allow_html=True)

    section = st.radio(
        "Navigation",
        ["📊  Market Overview",
         "💰  Pricing Strategy",
         "🎯  Scent Gaps & Product Moat",
         "📢  Customer Pain Points & Ad Hooks"],
        label_visibility="collapsed",
    )

    st.markdown(f"<div style='margin-top: 2.5rem;'></div>", unsafe_allow_html=True)
    st.markdown(f"""
        <div style='border-top: 1px solid {INK_LINE}; padding-top: 1.2rem;'>
            <div style='font-size: 0.7rem; color: {BONE_DIM}; letter-spacing: 0.18em;
                        text-transform: uppercase; margin-bottom: 0.6rem;'>Dataset</div>
            <div style='font-family: "Cormorant Garamond", serif; font-size: 1.6rem; color: {BONE};'>
                {len(df)} <span style='font-size: 0.9rem; color: {BONE_DIM};'>products</span>
            </div>
            <div style='font-size: 0.8rem; color: {BONE_DIM}; margin-top: 0.3rem;'>
                Faisal AlDayel · faisalaldayel.com
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Bilingual toggle for the strategy tabs
    st.markdown(f"<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
    lang = st.radio(
        "Strategy language",
        ["English", "العربية"],
        horizontal=True,
        label_visibility="visible",
    )


# ============================================================================
# REUSABLE PLOTLY THEME
# ============================================================================

PLOTLY_LAYOUT = dict(
    paper_bgcolor=INK,
    plot_bgcolor=INK,
    font=dict(family="Manrope, sans-serif", color=BONE, size=12),
    title_font=dict(family="Cormorant Garamond, serif", size=22, color=BONE),
    xaxis=dict(gridcolor=INK_LINE, zerolinecolor=INK_LINE, linecolor=INK_LINE,
               tickfont=dict(color=BONE_DIM)),
    yaxis=dict(gridcolor=INK_LINE, zerolinecolor=INK_LINE, linecolor=INK_LINE,
               tickfont=dict(color=BONE_DIM)),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=BONE_DIM, size=11),
                bordercolor=INK_LINE, borderwidth=0),
    margin=dict(l=20, r=20, t=60, b=20),
)


# ============================================================================
# TAB 1 — MARKET OVERVIEW
# ============================================================================

def tab_market_overview():
    st.markdown('<span class="eyebrow">Competitor Analysis · Saudi Luxury Fragrance</span>',
                unsafe_allow_html=True)
    st.markdown("# Market Overview")
    st.markdown(
        '<p class="lede">A 24-year-old Saudi house, 75 active SKUs, '
        'and a catalog whose silhouette tells you exactly where the opportunity lives.</p>',
        unsafe_allow_html=True,
    )

    # ---- KPIs ----
    rated_df = df[df["review_count"] > 0]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Products", f"{len(df)}")
    c2.metric("Average Price", f"{df['price_sar'].mean():.0f} SAR")
    c3.metric("Median Price", f"{df['price_sar'].median():.0f} SAR")
    c4.metric("Highest Price", f"{df['price_sar'].max():.0f} SAR")
    c5.metric("Total Customer Reviews", f"{int(df['review_count'].sum()):,}")

    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)

    # ---- Scatter: Price vs Review Count ----
    st.markdown("## Where the Money Actually Sits")
    st.markdown(
        "Each bubble is one product. Position tells you the price; size tells you "
        "how many customers reviewed it (our proxy for sales volume). "
        "The cluster bottom-left is the cash cow. The empty space top-right "
        "is the opportunity."
    )

    scatter_df = df[df["review_count"] > 0].copy()
    scatter_df["hover"] = (
        scatter_df["display_name"] + "<br>" +
        scatter_df["price_sar"].astype(int).astype(str) + " SAR · " +
        scatter_df["review_count"].astype(str) + " reviews · ★ " +
        scatter_df["rating_avg"].round(2).astype(str)
    )

    fig = px.scatter(
        scatter_df,
        x="price_sar",
        y="review_count",
        size="review_count",
        color="tier",
        size_max=55,
        hover_name="display_name",
        custom_data=["display_name", "rating_avg", "review_count"],
        color_discrete_sequence=[BRONZE, "#D4A85A", SAGE, TERRACOTTA, "#6B5A8A", BONE_DIM],
    )
    fig.update_traces(
        marker=dict(line=dict(width=0.5, color=INK), opacity=0.85),
        hovertemplate="<b>%{customdata[0]}</b><br>" +
                      "Price: %{x:.0f} SAR<br>" +
                      "Reviews: %{customdata[2]}<br>" +
                      "Rating: %{customdata[1]:.2f} / 5<extra></extra>",
    )

    # Highlight the empty premium tiers with annotation
    fig.add_annotation(
        x=700, y=350,
        text="◈   The empty rung<br><span style='font-size:11px;'>almost no proven sales above 400 SAR</span>",
        showarrow=True, arrowhead=0, arrowcolor=BRONZE, arrowwidth=1,
        ax=120, ay=-40,
        font=dict(family="Cormorant Garamond, serif", size=15, color=BRONZE),
        align="left", bordercolor=BRONZE, borderwidth=1, borderpad=8,
        bgcolor=INK_RAISED,
    )
    fig.add_annotation(
        x=160, y=470,
        text="◈   The cash cow<br><span style='font-size:11px;'>142–200 SAR drives the entire business</span>",
        showarrow=True, arrowhead=0, arrowcolor=BRONZE, arrowwidth=1,
        ax=180, ay=-15,
        font=dict(family="Cormorant Garamond, serif", size=15, color=BRONZE),
        align="left", bordercolor=BRONZE, borderwidth=1, borderpad=8,
        bgcolor=INK_RAISED,
    )

    layout = {**PLOTLY_LAYOUT}
    layout.update(
        height=560,
        xaxis_title="Price (SAR)",
        yaxis_title="Number of Customer Reviews",
        showlegend=True,
        legend_title_text="Price Tier",
    )
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True)

    # ---- Top 10 sellers table ----
    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown("## Top 10 Best-Selling Products")
    st.markdown(
        "Ranked by a fair blend of customer rating and review volume — so a single "
        "5-star review can't beat a product with hundreds of slightly-less-perfect ones."
    )

    top10 = (
        df.sort_values(["seller_score", "review_count"], ascending=[False, False])
          .head(10)
          .reset_index(drop=True)
    )
    top10.index = top10.index + 1
    display = top10[["display_name", "price_sar", "rating_avg", "review_count", "seller_score"]].copy()
    display.columns = ["Product", "Price (SAR)", "Rating", "Reviews", "Score"]
    display["Score"] = display["Score"].round(3)
    display["Rating"] = display["Rating"].round(2)

    st.dataframe(
        display,
        use_container_width=True,
        height=420,
        column_config={
            "Product": st.column_config.TextColumn("Product", width="medium"),
            "Price (SAR)": st.column_config.NumberColumn("Price (SAR)", format="%.0f"),
            "Rating": st.column_config.NumberColumn("Rating", format="%.2f ★"),
            "Reviews": st.column_config.NumberColumn("Reviews", format="%d"),
            "Score": st.column_config.ProgressColumn(
                "Strength Score", format="%.3f", min_value=4.9, max_value=5.0,
            ),
        },
    )

    st.markdown(
        '<p class="fineprint">'
        'Read this table sideways: the top three sellers each cost 142.50 SAR. '
        'Faisal AlDayel wins on volume in a single narrow band — and is essentially absent '
        'from the territory a heritage luxury brand should occupy.'
        '</p>',
        unsafe_allow_html=True,
    )


# ============================================================================
# TAB 2 — PRICING STRATEGY
# ============================================================================

def tab_pricing():
    st.markdown('<span class="eyebrow">Strategic Recommendation · Module 01</span>',
                unsafe_allow_html=True)
    st.markdown("# Pricing Strategy")
    st.markdown(
        '<p class="lede">The competitor has never proven they can sell above 400 SAR. '
        "That isn't a failure to copy. It's a doorway to walk through.</p>",
        unsafe_allow_html=True,
    )

    # ---- Tier breakdown chart ----
    tier_stats = (
        df.groupby("tier", observed=True)
          .agg(products=("price_sar", "size"),
               total_reviews=("review_count", "sum"))
          .reset_index()
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=tier_stats["tier"].astype(str),
        y=tier_stats["products"],
        name="Products in tier",
        marker_color=BRONZE,
        yaxis="y",
        hovertemplate="<b>%{x}</b><br>%{y} products<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=tier_stats["tier"].astype(str),
        y=tier_stats["total_reviews"],
        name="Total customer reviews",
        marker_color=BONE,
        mode="lines+markers",
        line=dict(width=2, dash="dot"),
        marker=dict(size=10, line=dict(color=BRONZE, width=1)),
        yaxis="y2",
        hovertemplate="<b>%{x}</b><br>%{y:,} total reviews<extra></extra>",
    ))
    # Build layout by merging the base theme with chart-specific overrides.
    # Cannot pass **PLOTLY_LAYOUT alongside yaxis= / legend= because those keys
    # already exist in PLOTLY_LAYOUT — Python rejects duplicate kwargs.
    layout = {**PLOTLY_LAYOUT}
    layout.update(
        height=420,
        title="Competitor catalog distribution by price tier",
        yaxis=dict(title="Products", gridcolor=INK_LINE, tickfont=dict(color=BONE_DIM)),
        yaxis2=dict(title="Total reviews (sales proxy)", overlaying="y", side="right",
                    gridcolor="rgba(0,0,0,0)", tickfont=dict(color=BONE_DIM)),
        legend=dict(orientation="h", y=1.12, x=0, bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)

    # ---- Strategy content, bilingual ----
    if lang == "English":
        st.markdown("## The Three Pricing Moves")

        st.markdown("""
        <div class="strategy-card">
            <span class="label">Move 01 · Flagship</span>
            <h4>Price the flagship at 1,200 – 1,450 SAR.</h4>
            <p>Above the competitor's entire ceiling. Their products over 400 SAR have <b>34 combined customer reviews</b> — versus 431 reviews for a single 142 SAR bottle. The 400–900 SAR band is not a gap, it is a graveyard. Pricing into a proven failure zone is not a strategy.</p>
            <p>Pricing at 1,200+ SAR changes the conversation entirely. The customer is no longer comparing you to Faisal AlDayel. They are comparing you to international houses — which is precisely where a heritage brand wants to be compared.</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="strategy-card">
            <span class="label">Move 02 · Discovery Set</span>
            <h4>Launch a discovery set at 350 – 450 SAR.</h4>
            <p>Four 5ml miniatures. Sits above the competitor's entire entry and mid tier (preserving the premium signal), and inside the premium tier where they have <b>only 6 products and 69 total reviews</b>. Customers who want to spend in the 300–400 SAR range cannot find anything they trust at Faisal AlDayel. They will find you.</p>
            <p>This is the trial bridge to the 1,400 SAR flagship — and the only acceptable place to engage on price.</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="strategy-card">
            <span class="label">Move 03 · The Forbidden Zone</span>
            <h4>Do not enter the 142 – 250 SAR tier.</h4>
            <p>Two reasons. First: you cannot win on volume against a 24-year-old established house with proven distribution muscle. Second, and more important: once a brand is anchored at 200 SAR in the customer's mind, <b>it can never move up.</b></p>
            <p>You can always lower prices later. You cannot raise them.</p>
        </div>
        """, unsafe_allow_html=True)

    else:  # Arabic
        st.markdown(f"""
        <div class="arabic-block">
            <h2 style='font-family: Tajawal; font-weight: 700; border-bottom: 1px solid {INK_LINE}; padding-bottom: 0.6rem;'>الخطوات التسعيرية الثلاثة</h2>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="strategy-card arabic-block">
            <span class="label">الخطوة الأولى · المنتج الرئيسي</span>
            <h4 style='font-family: Tajawal; font-weight: 700;'>سعّر المنتج الرئيسي بين ١,٢٠٠ و ١,٤٥٠ ريال.</h4>
            <p>فوق سقف المنافس كله. منتجاتهم اللي فوق ٤٠٠ ريال جمعوا مع بعض <b>٣٤ مراجعة بس</b> — في الوقت اللي عبوة واحدة بـ ١٤٢ ريال عندها ٤٣١ مراجعة. الفئة بين ٤٠٠ و ٩٠٠ ريال مش فرصة، دي مقبرة. تنزل تنافس في منطقة فشل مُثبتة؟ ده مش تخطيط.</p>
            <p>لما تسعّر بـ ١,٢٠٠+ ريال، انت بتغيّر المحادثة كلها. العميل مش هيقارنك بفيصل الدايل. هيقارنك ببراندات عالمية — وده بالظبط المكان اللي براند تراثي محترم لازم يكون فيه.</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="strategy-card arabic-block">
            <span class="label">الخطوة التانية · طقم التجربة</span>
            <h4 style='font-family: Tajawal; font-weight: 700;'>اطلق Discovery Set بـ ٣٥٠ – ٤٥٠ ريال.</h4>
            <p>أربع عبوات صغيرة ٥ مل. بتقعد فوق فئة المبتدئين والمتوسطين كلها (فبتحافظ على الإحساس الفاخر)، وجوا الفئة الفاخرة اللي المنافس عنده فيها <b>٦ منتجات بس و ٦٩ مراجعة في المجموع</b>. العملاء اللي عايزين يصرفوا بين ٣٠٠ و ٤٠٠ ريال مش لاقيين عندهم حاجة يثقوا فيها. هيلاقوك انت.</p>
            <p>الـ Discovery ده هو الجسر من التجربة لشراء العبوة الرئيسية بـ ١,٤٠٠ ريال — والمكان الوحيد المسموح فيه نتحرّك على السعر.</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="strategy-card arabic-block">
            <span class="label">الخطوة التالتة · المنطقة الممنوعة</span>
            <h4 style='font-family: Tajawal; font-weight: 700;'>لا تدخل فئة ١٤٢ – ٢٥٠ ريال أبدًا.</h4>
            <p>سببين. الأول: مش هتقدر تكسب على الكمية ضد شركة عمرها ٢٤ سنة وعندها قنوات توزيع جاهزة. والتاني، الأهم: لما العميل يثبّت البراند في ذهنه على إنه بـ ٢٠٠ ريال، <b>مش هتقدر تطلع فوق تاني.</b> أبدًا.</p>
            <p>تنزل بسعرك بعدين، آه ممكن. تطلع بيه، صعب جدًا.</p>
        </div>
        """, unsafe_allow_html=True)


# ============================================================================
# TAB 3 — SCENT GAPS
# ============================================================================

def tab_scent_gaps():
    st.markdown('<span class="eyebrow">Strategic Recommendation · Module 02</span>',
                unsafe_allow_html=True)
    st.markdown("# Scent Gaps & Product Moat")
    st.markdown(
        '<p class="lede">The competitor uses oud, amber, and musk in nearly every product. '
        "A heritage brand that smells the same loses by definition. A brand that smells different "
        "is not compared — it is discovered.</p>",
        unsafe_allow_html=True,
    )

    # ---- Saturation chart ----
    notes_data = pd.DataFrame({
        "note": ["Oud", "Amber", "Musk", "Rose", "Frankincense",
                 "Myrrh", "Vanilla", "Patchouli", "Jasmine", "Cardamom"],
        "mentions": [82, 61, 56, 48, 45, 31, 31, 29, 25, 22],
    })
    fig = go.Figure(go.Bar(
        x=notes_data["mentions"],
        y=notes_data["note"],
        orientation="h",
        marker=dict(color=BRONZE, line=dict(color=BRONZE_DEEP, width=0)),
        text=notes_data["mentions"],
        textposition="outside",
        textfont=dict(color=BONE, family="Manrope"),
        hovertemplate="<b>%{y}</b><br>%{x} mentions across 75 products<extra></extra>",
    ))
    # Merge-then-pass pattern (see tab_pricing for why).
    layout = {**PLOTLY_LAYOUT}
    layout.update(
        height=440,
        title="The saturated Gulf palette — what every competitor builds with",
        xaxis_title="Mentions across the 75-product catalog",
        yaxis=dict(autorange="reversed", gridcolor="rgba(0,0,0,0)",
                   tickfont=dict(color=BONE)),
        showlegend=False,
    )
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        '<p class="fineprint">'
        'Eight ingredients carry the entire 75-product catalog. '
        'This is the default Gulf perfume formula — replicable, recognizable, and saturated.'
        '</p>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)

    # ---- Strategy content, bilingual ----
    if lang == "English":
        st.markdown("## The Three-Pillar Ingredient Strategy")
        st.markdown(
            "The brand should be built around three categories of ingredients the competition "
            "does not use. We recommend a deliberate top–heart–base structure where every layer "
            "sits outside the saturated palette above."
        )

        st.markdown("""
        <div class="strategy-card">
            <span class="label">Pillar 01 · The Distinctive Floral Hero (Top Note)</span>
            <h4>A rare botanical that signals "this is not another oud" from the first second.</h4>
            <p>The opening note is the customer's first impression and the brand's first sentence.
            It should be a flower with provenance the brand can speak about authentically — a botanical with
            a traceable origin, a story, and ideally a regional or cultural specificity the competitor cannot
            claim. Function: <b>signature top note that creates immediate category separation.</b></p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="strategy-card">
            <span class="label">Pillar 02 · The Unusual Resin or Balsam (Heart Note)</span>
            <h4>The middle of the fragrance — where most Gulf brands lean on rose or amber.</h4>
            <p>By using an uncommon resin or balsamic ingredient at the heart, the perfume develops in a
            direction the customer's nose does not recognize as "oud territory." This is where the famous
            recognition-failure question gets asked: <i>"What are you wearing?"</i> — when the customer
            cannot place the scent in any category they know, the brand has won.</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="strategy-card">
            <span class="label">Pillar 03 · The Warm, Vegetal, or Waxy Base</span>
            <h4>What lingers on skin and on clothes — the part the brand becomes remembered by.</h4>
            <p>Most Gulf perfumes use musk, amber, or sandalwood as the base. A heritage brand should use
            something warmer and more organic — a beeswax-style accord, a vegetal root note, or a smoked-honey
            depth. The drydown is what customers describe to their friends. Make it impossible to describe
            using competitor vocabulary.</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="strategy-card" style="border-left-color: {SAGE};">
            <h4 style="color: {BONE};">The principle behind the three pillars</h4>
            <p>If the top, heart, and base are <b>all</b> outside the Gulf default palette, the perfume is
            not competing — it is occupying its own category. Customers will not say <i>"it is better than
            the competitor."</i> They will say <i>"it is nothing like anything I have smelled before."</i>
            The second sentence is worth ten times the first.</p>
        </div>
        """, unsafe_allow_html=True)

    else:
        st.markdown(f"""
        <div class="arabic-block">
            <h2 style='font-family: Tajawal; font-weight: 700; border-bottom: 1px solid {INK_LINE}; padding-bottom: 0.6rem;'>استراتيجية المكونات الثلاثية</h2>
            <p>البراند لازم يتبني حول ٣ فئات من المكونات اللي المنافس مش بيستخدمها. التوصية إن نعمل تركيبة مقصودة (نوتة عليا – قلب – قاعدة) كل طبقة فيها بره الباليتة المشبعة اللي فوق.</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="strategy-card arabic-block">
            <span class="label">العمود الأول · زهرة نادرة كنوتة عليا</span>
            <h4 style='font-family: Tajawal; font-weight: 700;'>زهرة نادرة بتقول للعميل "ده مش عود تاني" من أول ثانية.</h4>
            <p>النوتة العليا هي أول انطباع للعميل، وهي أول جملة من البراند. لازم تكون زهرة ليها أصل البراند يقدر يتكلم عنه بمصداقية — نبات ليه مصدر معروف، وقصة، ويفضل يكون ليه خصوصية إقليمية أو ثقافية المنافس مش قادر يدّعيها. الوظيفة: <b>توقيع علوي يفصل البراند عن الفئة فورًا.</b></p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="strategy-card arabic-block">
            <span class="label">العمود التاني · راتنج أو بلسم غير شائع كقلب</span>
            <h4 style='font-family: Tajawal; font-weight: 700;'>قلب العطر — المكان اللي معظم البراندات الخليجية بتحط فيه ورد أو عنبر.</h4>
            <p>لما نستخدم راتنج أو بلسم غير شائع في القلب، العطر بيتطوّر في اتجاه أنف العميل مش هتعرفه. هنا اللي بييجي السؤال الشهير: <i>"إيه العطر اللي لابسه ده؟"</i> — لما العميل ميقدرش يحط ريحتك في أي فئة يعرفها، البراند كسب.</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="strategy-card arabic-block">
            <span class="label">العمود التالت · قاعدة دافية، نباتية، أو شمعية</span>
            <h4 style='font-family: Tajawal; font-weight: 700;'>اللي بيفضل على الجلد والهدوم — الجزء اللي البراند بيتذكر بيه.</h4>
            <p>معظم العطور الخليجية بتحط مسك أو عنبر أو صندل في القاعدة. براند تراثي محترم يحط حاجة أدفأ وأكتر طبيعية — أكورد شبه شمع العسل، نوتة جذور نباتية، أو عمق عسل مدخّن. النوتة دي هي اللي العملاء بيوصفوها لأصحابهم. خلّيها مستحيل توصف بمفردات المنافس.</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="strategy-card arabic-block" style="border-left-color: {SAGE};">
            <h4 style='font-family: Tajawal; font-weight: 700; color: {BONE};'>المبدأ ورا الأعمدة التلاتة</h4>
            <p>لو النوتة العليا والقلب والقاعدة <b>كلهم</b> بره الباليتة الخليجية الافتراضية، العطر مش بينافس — هو بياخد فئة لوحده. العملاء مش هيقولوا <i>"ده أحسن من المنافس".</i> هيقولوا <i>"ده مش شبه أي حاجة شميتها قبل كده".</i> الجملة التانية تساوي عشر أضعاف الأولى.</p>
        </div>
        """, unsafe_allow_html=True)


# ============================================================================
# TAB 4 — PAIN POINTS & AD HOOKS
# ============================================================================

def tab_pain_points():
    st.markdown('<span class="eyebrow">Strategic Recommendation · Module 03</span>',
                unsafe_allow_html=True)
    st.markdown("# Customer Pain Points & Ad Hooks")
    st.markdown(
        '<p class="lede">Three failure modes recur across Gulf luxury fragrance, '
        "confirmed by industry-wide review patterns. Each pain point converts directly "
        "into a launch hook the competitor cannot answer.</p>",
        unsafe_allow_html=True,
    )

    # Three industry-verified pain points with three hook angles each
    pain_points = [
        {
            "num": "01",
            "en_title": "Weak longevity and unstable sillage",
            "ar_title": "ضعف ثبات الريحة",
            "en_desc": "The single most frequent complaint across Gulf fragrance reviews. "
                       "Customers report initial intensity that collapses within 1–3 hours, "
                       "leaving them re-applying mid-day or feeling deceived by an opening "
                       "that promised more than the drydown delivered.",
            "ar_desc": "الشكوى الأكتر تكرارًا في مراجعات العطور الخليجية. "
                       "العميل بيقول إن الريحة قوية أول ما تتحط، بس بعد ساعة أو تلاتة "
                       "بتختفي — فيرجع يحط تاني نص النهار، أو يحس إن العطر خدعه.",
            "hooks_en": [
                ("Diagnostic", "Tired of perfume that vanishes by noon? You're not alone."),
                ("Promise", "Engineered to develop on skin for ten hours. Not advertised — measured."),
                ("Identity", "For people who don't want to think about their perfume after they put it on."),
            ],
            "hooks_ar": [
                ("تشخيصي", "زهقت من عطر بيختفي قبل الظهر؟ مش لوحدك."),
                ("وعد", "متصمّم يفضل على الجلد عشر ساعات. مش دعاية — قياس."),
                ("هوية", "للناس اللي مش عايزة تفكر في عطرها بعد ما تلبسه."),
            ],
        },
        {
            "num": "02",
            "en_title": "Generic, recycled scent profiles",
            "ar_title": "روايح متكررة ومتشابهة",
            "en_desc": "Customers consistently complain that Gulf perfumes 'all smell the same' — "
                       "oud, amber, musk, rose, on repeat. The fatigue of similarity is real, and "
                       "naming it openly in marketing creates instant trust with anyone who has "
                       "shopped this category twice.",
            "ar_desc": "العملاء بيقولوا باستمرار إن العطور الخليجية كلها بريحة واحدة — "
                       "عود، عنبر، مسك، ورد، نفس الدايرة. الإحساس بالملل من التشابه ده "
                       "حقيقي، ولما البراند يقوله بصراحة في الإعلان، بيكسب ثقة فورية "
                       "مع أي حد اشترى من الفئة دي أكتر من مرة.",
            "hooks_en": [
                ("Diagnostic", "If your last three perfumes smelled the same, you weren't wrong."),
                ("Promise", "Built without oud. Built without compromise."),
                ("Identity", "For everyone tired of smelling like everyone else."),
            ],
            "hooks_ar": [
                ("تشخيصي", "لو آخر تلات عطور اشتريتهم كانوا بنفس الريحة، انت مش غلطان."),
                ("وعد", "اتعمل من غير عود. اتعمل من غير تنازلات."),
                ("هوية", "لكل اللي زهق إنه يبقى ريحته زي الكل."),
            ],
        },
        {
            "num": "03",
            "en_title": "Fragile bottles and failing sprayers",
            "ar_title": "عبوات ضعيفة وبخّاخات بتتعطل",
            "en_desc": "Persistent reports of leakage during shipping, sprayers that lose pressure "
                       "after weeks, and bottles that feel cheap at the price point being charged. "
                       "When a customer pays for luxury and receives industrial mechanics, the "
                       "experience contradicts the brand promise — and they tell people.",
            "ar_desc": "بلاغات مستمرة عن تسرّب في الشحن، بخّاخات بتفقد ضغطها بعد أسابيع، "
                       "وعبوات بتحس إنها رخيصة بالنسبة لسعرها. لما العميل يدفع تمن فخامة "
                       "ويلاقي ميكانيكا صناعية، التجربة بتتناقض مع وعد البراند — وبيقول لأصحابه.",
            "hooks_en": [
                ("Diagnostic", "If you've ever opened a perfume box to find leakage, this is for you."),
                ("Promise", "Hand-finished bottle. Weighted base. The sprayer is guaranteed for the life of the fragrance."),
                ("Identity", "Built like furniture. Treated like an heirloom."),
            ],
            "hooks_ar": [
                ("تشخيصي", "لو حصلك إنك فتحت كرتونة عطر ولقيتها مسرّبة، التشكيلة دي ليك."),
                ("وعد", "عبوة منتهية باليد. قاعدة موزونة. البخّاخ مضمون طول عمر العطر."),
                ("هوية", "متعمول زي قطعة أثاث. بيتعامل معاه زي الإرث."),
            ],
        },
    ]

    for pp in pain_points:
        title = pp["en_title"] if lang == "English" else pp["ar_title"]
        desc = pp["en_desc"] if lang == "English" else pp["ar_desc"]
        hooks = pp["hooks_en"] if lang == "English" else pp["hooks_ar"]

        klass = "pain-point" + ("" if lang == "English" else " arabic-block")
        hook_label = "Ad Hook Variants" if lang == "English" else "صيغ الجملة الإعلانية"

        st.markdown(f"""
        <div class="{klass}">
            <span class="pain-point-num">Pain Point · {pp["num"]}</span>
            <h3 style='margin-top: 0.3rem; color: {BONE};{"font-family: Tajawal;" if lang != "English" else ""}'>{title}</h3>
            <p style='margin-bottom: 1.5rem;'>{desc}</p>
            <div style='font-size: 0.72rem; letter-spacing: 0.2em; text-transform: uppercase;
                        color: {BRONZE}; margin-bottom: 0.8rem; font-weight: 600;'>
                ◈ &nbsp; {hook_label}
            </div>
        </div>
        """, unsafe_allow_html=True)

        for angle, hook in hooks:
            st.markdown(f"""
            <div style='margin-left: 1.5rem; margin-bottom: 0.4rem;'>
                <span style='font-size: 0.7rem; letter-spacing: 0.18em; text-transform: uppercase;
                             color: {BONE_DIM}; font-weight: 600;'>{angle}</span>
                <div class='hook'>{hook}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)

    # ---- Recommended lead message ----
    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)

    if lang == "English":
        st.markdown("## Recommended Launch Lead")
        st.markdown(f"""
        <div class="strategy-card" style="border-left-color: {BRONZE}; border-left-width: 4px;">
            <span class="label">Primary hook · Use this first</span>
            <h4 style='font-size: 1.8rem; font-style: italic;'>"For everyone tired of smelling like everyone else."</h4>
            <p>This line wins because it does three things at once: it names a real customer
            frustration (saturation fatigue), it pre-emptively positions the brand as the antidote,
            and it flatters the reader by implying they have taste the market hasn't served.
            It works in both English and Arabic with minimal adaptation, and it is the lead
            message every other hook in this report should support, not contradict.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="arabic-block">
            <h2 style='font-family: Tajawal; font-weight: 700; border-bottom: 1px solid {INK_LINE}; padding-bottom: 0.6rem;'>الجملة الافتتاحية المقترحة للإطلاق</h2>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
        <div class="strategy-card arabic-block" style="border-left-color: {BRONZE}; border-left-width: 4px;">
            <span class="label">الجملة الأساسية · ابدأ بيها</span>
            <h4 style='font-family: Tajawal; font-weight: 700; font-size: 1.7rem;'>"لكل اللي زهق إنه يبقى ريحته زي الكل."</h4>
            <p>الجملة دي بتكسب لأنها بتعمل تلات حاجات في نفس الوقت: بتسمّي إحباط حقيقي عند العميل (الملل من التشابه)، بتموّضع البراند كحل قبل ما العميل يسأل، وبتجامل القارئ بإنها بتشاور إن عنده ذوق السوق ما خدمهوش. شغّالة بالعربي والإنجليزي بأقل تعديل، وهي الجملة الأم اللي كل الـ Hooks التانية في التقرير ده لازم تدعمها مش تناقضها.</p>
        </div>
        """, unsafe_allow_html=True)


# ============================================================================
# ROUTER
# ============================================================================

if section.startswith("📊"):
    tab_market_overview()
elif section.startswith("💰"):
    tab_pricing()
elif section.startswith("🎯"):
    tab_scent_gaps()
else:
    tab_pain_points()


# ============================================================================
# FOOTER
# ============================================================================

st.markdown(f"""
<div style='margin-top: 5rem; padding-top: 2rem; border-top: 1px solid {INK_LINE};
            text-align: center;'>
    <div style='font-family: "Cormorant Garamond", serif; color: {BRONZE};
                font-size: 1.1rem; letter-spacing: 0.05em;'>◈</div>
    <div style='font-size: 0.7rem; color: {BONE_DIM}; letter-spacing: 0.2em;
                text-transform: uppercase; margin-top: 0.6rem;'>
        Atelier · Competitive Intelligence · Prepared for the Client
    </div>
</div>
""", unsafe_allow_html=True)
