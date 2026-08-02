import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
import json
from datetime import datetime, date, timedelta
from streamlit_autorefresh import st_autorefresh

from core.regime_engine import (
    detect_market_regime,
    save_regime_history,
    load_regime_history
)

from core.portfolio_engine import (
    load_portfolio,
    calculate_portfolio
)
from components.ui import premium_card
def format_billions(value):

    if pd.isna(value):
        return "N/A"

    return f"${value/1_000_000_000:.1f}B"

is_mobile = False

WATCHLIST = [
    "NVDA",
    "AMD",
    "AMZN",
    "GOOG",
    "MSFT",
    "TSLA"
]


FINANCIAL_RESULTS_LINKS = {
    "TSLA": {
        "name": "Tesla",
        "category": "Company",
        "ir": "https://ir.tesla.com/",
        "results": "https://ir.tesla.com/",
        "sec": "https://www.sec.gov/edgar/browse/?CIK=1318605&owner=exclude",
        "note": "Quarterly disclosure, shareholder decks, webcast replays, and SEC filings."
    },
    "META": {
        "name": "Meta Platforms",
        "category": "Company",
        "ir": "https://investor.atmeta.com/",
        "results": "https://investor.atmeta.com/financials/default.aspx",
        "sec": "https://www.sec.gov/edgar/browse/?CIK=1326801&owner=exclude",
        "note": "Quarterly earnings, press releases, and SEC filings."
    },
    "PLTR": {
        "name": "Palantir",
        "category": "Company",
        "ir": "https://investors.palantir.com/",
        "results": "https://investors.palantir.com/financials/quarterly-results/default.aspx/",
        "sec": "https://www.sec.gov/edgar/browse/?CIK=1321655&owner=exclude",
        "note": "Quarterly results, shareholder letters, presentations, and SEC filings."
    },
    "AAPL": {
        "name": "Apple",
        "category": "Company",
        "ir": "https://investor.apple.com/investor-relations/default.aspx",
        "results": "https://investor.apple.com/investor-relations/default.aspx",
        "sec": "https://www.sec.gov/edgar/browse/?CIK=320193&owner=exclude",
        "note": "Quarterly earnings reports, financial statements, and 10-Q/10-K filings."
    },
    "MU": {
        "name": "Micron Technology",
        "category": "Company",
        "ir": "https://investors.micron.com/",
        "results": "https://investors.micron.com/quarterly-results",
        "sec": "https://www.sec.gov/edgar/browse/?CIK=723125&owner=exclude",
        "note": "Quarterly results, presentations, prepared remarks, and SEC filings."
    },
    "SPCX": {
        "name": "SpaceX",
        "category": "Private Company",
        "ir": "https://ir.spacex.com/investors/default.aspx",
        "results": "https://ir.spacex.com/investors/default.aspx",
        "sec": "https://ir.spacex.com/investors/default.aspx",
        "note": "Official SpaceX investor portal for investor updates, reports, SEC filings, and events."
    },
}


def load_market_calendar():
    calendar_file = "data/market_calendar.json"

    fallback_events = [
        {
            "date": (date.today() + timedelta(days=1)).isoformat(),
            "event": "US CPI",
            "type": "Inflation",
            "level": "Critical",
            "assets": "Stocks - Bonds - USD"
        },
        {
            "date": (date.today() + timedelta(days=8)).isoformat(),
            "event": "Tesla Earnings",
            "type": "Earnings",
            "level": "High",
            "assets": "TSLA - EVs - Nasdaq"
        },
        {
            "date": (date.today() + timedelta(days=15)).isoformat(),
            "event": "FOMC Decision",
            "type": "Federal Reserve",
            "level": "Critical",
            "assets": "Rates - Growth - Dollar"
        },
    ]

    try:
        with open(calendar_file, "r") as f:
            events = json.load(f)
    except Exception:
        events = fallback_events

    normalized_events = []

    for event in events:
        event_date = datetime.strptime(event["date"], "%Y-%m-%d").date()
        days_away = (event_date - date.today()).days

        if days_away < 0:
            continue
        elif days_away == 0:
            days_label = "Today"
        elif days_away == 1:
            days_label = "Tomorrow"
        else:
            days_label = f"{days_away} Days"

        normalized_events.append({
            "date": event_date.strftime("%b %d"),
            "event": event.get("event", "Market Event"),
            "type": event.get("type", "Macro"),
            "level": event.get("level", "Medium"),
            "days": days_label,
            "assets": event.get("assets", "Stocks - Bonds - USD"),
        })

    return normalized_events[:12]


def impact_badge(level):
    level_lower = level.lower()

    if "critical" in level_lower:
        return "🔴 Critical", "#ef4444"
    if "high" in level_lower:
        return "🟠 High", "#f59e0b"
    if "medium" in level_lower:
        return "🟡 Medium", "#facc15"

    return "🟢 Low", "#22c55e"


def build_calendar_insight(events):
    if not events:
        return "No major market events are scheduled in the current calendar file."

    critical_events = [
        event for event in events
        if event["level"].lower() == "critical"
    ]
    focus_events = critical_events if critical_events else events[:3]
    top_events = ", ".join(event["event"] for event in focus_events[:3])

    event_types = []
    for event in events:
        if event["type"] not in event_types:
            event_types.append(event["type"])

    main_types = ", ".join(event_types[:3])

    return (
        f"This week's calendar is led by {top_events}. "
        f"The main pressure points are {main_types}, which can affect rates, "
        f"mega-cap technology, and overall risk appetite."
    )


def portfolio_impact_rows(events, tickers):
    ticker_themes = {
        "TSLA": ["rates", "growth", "consumer", "nasdaq", "inflation"],
        "NVDA": ["ai", "semiconductors", "nasdaq", "software", "cloud"],
        "META": ["ai", "nasdaq", "mega-cap tech", "software", "consumer"],
        "AAPL": ["mega-cap tech", "nasdaq", "consumer", "rates", "growth"],
        "MU": ["semiconductors", "ai", "nasdaq", "memory"],
        "PLTR": ["ai", "software", "data", "defense", "nasdaq"],
        "SPCX": ["space", "defense", "growth", "rates", "nasdaq"],
    }

    rows = []

    for ticker in tickers:
        score = 0
        ticker_lower = ticker.lower()
        reasons = []

        for event in events:
            event_text = (
                f"{event['event']} {event['type']} {event['assets']}"
            ).lower()

            if ticker_lower in event_text:
                score += 3
                reasons.append(event["event"])

            if any(
                keyword in event_text
                for keyword in ["nasdaq", "mega-cap tech", "ai", "semiconductors"]
            ) and ticker in ["AAPL", "MSFT", "META", "NVDA", "MU", "AMZN", "GOOG"]:
                score += 2
                reasons.append(event["type"])

            if any(
                keyword in event_text
                for keyword in ["rates", "inflation", "federal reserve", "pce"]
            ) and ticker in ["TSLA", "NVDA", "META", "AAPL", "AMZN", "GOOG"]:
                score += 1
                reasons.append(event["type"])

            for theme in ticker_themes.get(ticker, []):
                if theme in event_text:
                    score += 1
                    reasons.append(event["type"])
                    break

        if score >= 4:
            level = "HIGH"
            color = "#ef4444"
        elif score >= 2:
            level = "MEDIUM"
            color = "#facc15"
        else:
            level = "LOW"
            color = "#22c55e"

        unique_reasons = []
        for reason in reasons:
            if reason not in unique_reasons:
                unique_reasons.append(reason)

        reason_text = "No direct calendar catalyst"
        if unique_reasons:
            reason_text = " + ".join(unique_reasons[:2])

        rows.append((ticker, level, color, reason_text))

    return rows

# =====================================================
# DEV MODE / AI COST CONTROL
# =====================================================

DEV_MODE = False
USE_AI_MARKET_BRIEF = False

TEXT = {
    "English": {
        "search": "🔎 Search Any Company",
        "dashboard": "🌎 Dashboard",
        "portfolio": "💼 Portfolio",
        "financial_results": "📄 Financial Results",
        "research": "📑 Research",
        "watchlist": "⭐ Watchlist",
        "market_command_center": "🌎 Market Command Center",
        "market_calendar": "### 📅 Market Calendar",
        "calendar_insight": "### 🤖 Calendar Insight",
        "portfolio_impact": "### 💼 Portfolio Impact",
        "market_regime": "MARKET REGIME",
        "emotion": "Emotion",
        "drivers": "Drivers",
        "no_drivers": "No major macro drivers detected",
        "market_narrative": "MARKET NARRATIVE",
        "portfolio_snapshot": "📊 PORTFOLIO SNAPSHOT",
        "portfolio_value": "Portfolio Value",
        "largest_position": "Largest Position",
        "total_gain_loss": "Total Gain / Loss",
    },
    "日本語": {
        "search": "🔎 企業を検索",
        "dashboard": "🌎 ダッシュボード",
        "portfolio": "💼 ポートフォリオ",
        "financial_results": "📄 決算資料",
        "research": "📑 企業分析",
        "watchlist": "⭐ ウォッチリスト",
        "market_command_center": "🌎 マーケット司令室",
        "market_calendar": "### 📅 市場カレンダー",
        "calendar_insight": "### 🤖 カレンダー分析",
        "portfolio_impact": "### 💼 保有銘柄への影響",
        "market_regime": "市場レジーム",
        "emotion": "心理",
        "drivers": "要因",
        "no_drivers": "大きなマクロ要因は検出されていません",
        "market_narrative": "マーケット解説",
        "portfolio_snapshot": "📊 ポートフォリオ概要",
        "portfolio_value": "ポートフォリオ評価額",
        "largest_position": "最大保有銘柄",
        "total_gain_loss": "合計損益",
    },
}

st.set_page_config(
    page_title="Yuichi AI Terminal",
    layout="centered" if is_mobile else "wide",
)
if "active_ticker" not in st.session_state:
    st.session_state["active_ticker"] = "AAPL"

st.markdown(
    '<div class="mobile-top-spacer"></div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="language-label">Language</div>',
    unsafe_allow_html=True
)

language = st.selectbox(
    "Language",
    ["English", "日本語"],
    index=0,
    label_visibility="collapsed"
)

t = TEXT[language]
st_autorefresh(interval=60000, key="refresh")

st.markdown(
    """
    <style>
    

    section[data-testid="stSidebar"] {
        background-color: #111827;
    }
    .stApp {
        background-color: #050816;
        color: #e2e8f0;
    }

    html, body {
        font-family: 'Courier New', monospace;
    }

    h1:not(.custom-market-title) {
        color: #38bdf8 !important;
        font-size: 3rem !important;
        font-weight: 800 !important;
        letter-spacing: 1px;
    }
    
    h2, h3 {
        color: #f8fafc !important;
    }

    div[data-testid="metric-container"] {
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(56, 189, 248, 0.4);
        padding: 20px;
        border-radius: 20px;
        box-shadow: 0 0 25px rgba(56, 189, 248, 0.18);
    }

    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        transition: 0.2s;
        box-shadow: 0 0 35px rgba(56, 189, 248, 0.35);
    }

    div[data-testid="metric-container"] label {
        color: #94a3b8 !important;
        font-size: 14px !important;
    }

    div[data-testid="metric-container"] div {
        color: #f8fafc !important;
    }

    .stAlert {
        background-color: rgba(15, 23, 42, 0.95) !important;
        border: 1px solid rgba(56, 189, 248, 0.3) !important;
        border-radius: 16px !important;
    }

    .language-label {
        color: #94a3b8;
        font-size: 13px;
        font-weight: 700;
        margin-bottom: 6px;
    }

    @media (max-width: 768px) {
        .block-container {
            padding: 2.25rem 0.85rem 2rem !important;
        }

        .mobile-top-spacer {
            display: block !important;
            height: 42px !important;
        }

        .language-label {
            color: #94a3b8 !important;
            display: block !important;
            font-size: 13px !important;
            font-weight: 700 !important;
            margin-bottom: 8px !important;
            margin-top: 4px !important;
        }

        div[data-testid="stHorizontalBlock"] {
            gap: 0.65rem !important;
        }

        div[data-testid="stTabs"] button {
            font-size: 0.82rem !important;
            padding: 0.45rem 0.55rem !important;
            white-space: nowrap !important;
        }

        div[data-testid="stTabs"] [role="tablist"] {
            overflow-x: auto !important;
            flex-wrap: nowrap !important;
        }

        h1:not(.custom-market-title) {
            font-size: 2rem !important;
        }

        h2 {
            font-size: 1.55rem !important;
        }

        h3 {
            font-size: 1.25rem !important;
        }

        .status-bar {
            flex-direction: column !important;
            align-items: flex-start !important;
            gap: 6px !important;
            margin-bottom: 18px !important;
        }

        .ticker-card {
            min-height: 58px !important;
            padding: 10px 8px !important;
            border-radius: 12px !important;
        }

        .ticker-label {
            font-size: 15px !important;
        }

        .dashboard-card-title {
            font-size: 12px !important;
        }

        .dashboard-card-value {
            font-size: 30px !important;
            line-height: 1.15 !important;
            overflow-wrap: anywhere !important;
        }

        .dashboard-card-body {
            font-size: 14px !important;
            line-height: 1.6 !important;
        }
    }

    </style>
    """,
    unsafe_allow_html=True
)

from datetime import time
# =====================================================
# HEADER
# =====================================================


from datetime import datetime
import pytz

eastern = pytz.timezone("US/Eastern")

now = datetime.now(eastern)

current_time = now.strftime("%Y-%m-%d %H:%M:%S")

weekday = now.weekday()

now_hour = now.hour

if weekday >= 5:
    market_status = "🔴 MARKET CLOSED"
    status_color = "#f87171"

elif 9 <= now_hour < 16:
    market_status = "🟢 MARKET OPEN"
    status_color = "#22c55e"

elif 4 <= now_hour < 9:
    market_status = "🟡 PRE-MARKET"
    status_color = "#facc15"

elif 16 <= now_hour < 20:
    market_status = "🟠 AFTER HOURS"
    status_color = "#fb923c"

else:
    market_status = "🔴 MARKET CLOSED"
    status_color = "#f87171"
st.markdown(
    f"""
    <div class="status-bar" style="
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 14px;
        padding: 12px 18px;
        margin-top: 10px;
        margin-bottom: 28px;
        display:flex;
        justify-content:space-between;
        align-items:center;
        font-size:14px;
        color:#94a3b8;
    ">

    <div style="color:{status_color};font-weight:700;">
    {market_status}
    </div>

    <div>
    LAST UPDATED: {current_time}
    </div>

    </div>
    """,
    unsafe_allow_html=True
)
# =====================================================
# LIVE MACRO DATA
# =====================================================

macro_tickers = {
    "NASDAQ": "^IXIC",
    "S&P 500": "^GSPC",
    "GOLD": "GC=F",
    "OIL": "CL=F",
    "VIX": "^VIX",
    "BTC": "BTC-USD",
    "NVDA": "NVDA",
    "TSLA": "TSLA",
    "AAPL": "AAPL",
    "MU": "MU"
}

macro_changes = {}

ticker_items = list(macro_tickers.items())
ticker_rows = [ticker_items[i:i + 5] for i in range(0, len(ticker_items), 5)]

for ticker_row in ticker_rows:

    if is_mobile:
        macro_cols = [st.container() for _ in ticker_row]
    else:
        macro_cols = st.columns(len(ticker_row))

    for col, (label, symbol) in zip(macro_cols, ticker_row):

        data = yf.Ticker(symbol).history(period="5d")

        if data.empty:
            continue

        close_prices = data["Close"].dropna()

        if len(close_prices) < 2:
            continue

        latest = close_prices.iloc[-1]
        previous = close_prices.iloc[-2]

        pct_change = (
            (latest - previous)
            / previous
        ) * 100

        if pd.isna(pct_change):
            continue

        macro_changes[label] = pct_change

        color = "#22c55e" if pct_change >= 0 else "#f87171"

        arrow = "▲" if pct_change >= 0 else "▼"

        with col:

            st.markdown(
                f"""
<div class="ticker-card" style="
background:rgba(15,23,42,0.78);
border:1px solid {color};
border-radius:16px;
padding:12px 10px;
text-align:center;
box-shadow:0 0 18px {color}33;
margin-bottom:12px;
min-height:72px;
display:flex;
align-items:center;
justify-content:center;
">

<div class="ticker-label" style="
color:{color};
font-size:20px;
font-weight:800;
line-height:1.2;
">
{label}<br>{arrow} {pct_change:.2f}%
</div>

</div>
""",
                unsafe_allow_html=True
            )

if DEV_MODE:

    regime = {
        "name": "RISK_OFF",
        "emotion": "fear",
        "color": "#f87171",
        "drivers": [
            "Dev Mode",
            "Oil Spike",
            "Volatility Surge"
        ]
    }

else:

    regime = detect_market_regime(macro_changes)
    

    save_regime_history(regime)
# =====================================================
# DYNAMIC THEME ENGINE
# =====================================================

if regime["name"] == "RISK_OFF":

    primary_glow = "rgba(248,113,113,0.25)"
    secondary_glow = "rgba(127,29,29,0.12)"

elif regime["name"] == "RISK_ON":

    primary_glow = "rgba(34,197,94,0.22)"
    secondary_glow = "rgba(20,83,45,0.10)"

else:

    primary_glow = "rgba(250,204,21,0.20)"
    secondary_glow = "rgba(113,63,18,0.08)"

st.markdown(
    f"""
<style>

.stApp {{
    background:
    radial-gradient(circle at top left, {primary_glow}, transparent 28%),
    radial-gradient(circle at top right, {secondary_glow}, transparent 30%),
    radial-gradient(circle at bottom center, rgba(168,85,247,0.10), transparent 35%),
    radial-gradient(circle at center, rgba(14,165,233,0.05), transparent 45%),
    linear-gradient(180deg, #020617 0%, #020817 45%, #01030f 100%);
    background-attachment: fixed;
}}

@keyframes pulseGlow {{
    0% {{ opacity: 0.7; }}
    50% {{ opacity: 1; }}
    100% {{ opacity: 0.7; }}
}}

.glow {{
    animation: pulseGlow 4s infinite ease-in-out;
}}

</style>
""",
    unsafe_allow_html=True
)

# =====================================================
# MARKET STATE ENGINE
# =====================================================

market_stress = 50

if macro_changes.get("NASDAQ", 0) < -0.5:
    market_stress += 10

if macro_changes.get("VIX", 0) > 20:
    market_stress += 15

if macro_changes.get("BTC", 0) < 0:
    market_stress += 5

if macro_changes.get("OIL", 0) > 2:
    market_stress += 5

market_stress = min(market_stress, 100)

ai_momentum = 90 if market_stress < 70 else 65

tesla_sentiment = (
    "BULLISH"
    if market_stress < 75
    else "CAUTIOUS"
)
# =====================================================
# MARKET PULSE ENGINE
# =====================================================

if macro_changes.get("BTC", 0) > 1:
    btc_signal = "🟢 Bitcoin Confirming"
elif macro_changes.get("BTC", 0) > 0:
    btc_signal = "🟡 Bitcoin Stable"
else:
    btc_signal = "🔴 Bitcoin Weakness"

if ai_momentum >= 80:
    ai_signal = "🟢 AI Momentum Strong"
elif ai_momentum >= 60:
    ai_signal = "🟡 AI Momentum Neutral"
else:
    ai_signal = "🔴 AI Momentum Weak"

if macro_changes.get("OIL", 0) < -1:
    oil_signal = "🟢 Oil Weakness"
elif macro_changes.get("OIL", 0) > 1:
    oil_signal = "🔴 Oil Strength"
else:
    oil_signal = "🟡 Oil Stable"

if macro_changes.get("VIX", 0) < 0:
    risk_signal = "🟢 Risk Appetite Improving"
elif macro_changes.get("VIX", 0) > 0:
    risk_signal = "🔴 Risk Appetite Falling"
else:
    risk_signal = "🟡 Risk Appetite Neutral"
# =====================================================
# MARKET COMMAND CENTER
# =====================================================

st.subheader(t["market_command_center"])

if is_mobile:
    calendar_col = st.container()
    ai_col = st.container()
else:
    calendar_col, ai_col = st.columns([2.2, 1])
    
with calendar_col:

    st.markdown(t["market_calendar"])

    events = load_market_calendar()
    calendar_grid = st.columns(2) if not is_mobile else [st.container()]

    for index, event in enumerate(events):

        impact_label, impact_color = impact_badge(event["level"])
        event_col = calendar_grid[index % len(calendar_grid)]

        with event_col:
            st.markdown(
            f"""
<div style="
background:rgba(15,23,42,0.75);
border:1px solid rgba(56,189,248,0.25);
border-radius:16px;
padding:14px;
margin-bottom:12px;
">

<div style="
color:#38bdf8;
font-size:13px;
font-weight:700;
">
{event['date']}
</div>

<div style="
color:#f8fafc;
font-size:18px;
font-weight:700;
margin-top:4px;
">
{event['event']}
</div>

<div style="
color:#38bdf8;
font-size:13px;
font-weight:700;
margin-top:6px;
">
{event['type']}
</div>

<div style="
color:#94a3b8;
font-size:13px;
margin-top:6px;
">
{event['assets']}
</div>

<div style="
color:#94a3b8;
font-size:13px;
margin-top:8px;
">
⏳ {event['days']}
</div>

<div style="
color:{impact_color};
font-size:14px;
font-weight:700;
margin-top:6px;
">
{impact_label}
</div>

</div>
""",
                unsafe_allow_html=True,
            )



with ai_col:

    st.markdown(t["calendar_insight"])

    st.markdown(build_calendar_insight(events))
    st.markdown(t["portfolio_impact"])

    impact_html = ""
    portfolio_tickers = list(load_portfolio().keys())

    for ticker, level, color, reason in portfolio_impact_rows(
        events,
        portfolio_tickers
    ):
        impact_html += f"""
<div style="
display:flex;
justify-content:space-between;
gap:14px;
border-bottom:1px solid rgba(148,163,184,0.12);
padding-bottom:10px;
margin-bottom:10px;
">
<div>
<div style="color:#f8fafc;font-weight:800;">{ticker}</div>
<div style="color:#94a3b8;font-size:12px;margin-top:3px;">{reason}</div>
</div>
<div style="color:{color};font-weight:800;white-space:nowrap;">{level}</div>
</div>
"""

    st.markdown(
        f"""
<div style="
background:rgba(15,23,42,0.75);
border:1px solid rgba(56,189,248,0.25);
border-radius:16px;
padding:16px;
margin-top:18px;
">

{impact_html}

</div>
""",
        unsafe_allow_html=True,
    )
# =====================================================
# MARKET CONTEXT OBJECT
# =====================================================

market_context = {
    "NASDAQ": round(macro_changes.get("NASDAQ", 0), 2),
    "S&P 500": round(macro_changes.get("S&P 500", 0), 2),
    "BTC": round(macro_changes.get("BTC", 0), 2),
    "OIL": round(macro_changes.get("OIL", 0), 2),
    "VIX": round(macro_changes.get("VIX", 0), 2),
    "GOLD": round(macro_changes.get("GOLD", 0), 2),
    "NVDA": round(macro_changes.get("NVDA", 0), 2),
    "TSLA": round(macro_changes.get("TSLA", 0), 2),
    "AAPL": round(macro_changes.get("AAPL", 0), 2),
    "MU": round(macro_changes.get("MU", 0), 2),
    "market_stress": market_stress,
    "ai_momentum": ai_momentum,
    "tesla_sentiment": tesla_sentiment,
}
dashboard_tab, portfolio_tab, financials_tab, research_tab, watchlist_tab = st.tabs(
    [
        t["dashboard"],
        t["portfolio"],
        t["financial_results"],
        t["research"],
        t["watchlist"]
    ]
)
with dashboard_tab:

    # =====================================================
    # EXECUTIVE SUMMARY ROW
    # =====================================================

    if is_mobile:
        summary1 = st.container()
        summary2 = st.container()
        summary3 = st.container()
    else:
        summary1, summary2, summary3 = st.columns(3)
    # =====================================================
    # PORTFOLIO SNAPSHOT
    # =====================================================

    portfolio_stats = calculate_portfolio()

    positions = portfolio_stats["positions"]

    largest_position = max(
        positions,
        key=lambda x: x["market_value"]
    )

    with summary3:

        st.markdown(
            f"""
    <div style="
    background:rgba(15,23,42,0.82);
    border:1px solid rgba(34,197,94,0.25);
    border-radius:22px;
    padding:24px;
    margin-top:20px;
    box-shadow:0 0 24px rgba(34,197,94,0.12);
    ">

    <div class="dashboard-card-title" style="
    color:#22c55e;
    font-size:13px;
    font-weight:700;
    letter-spacing:1px;
    margin-bottom:12px;
    ">
    {t['portfolio_snapshot']}
    </div>

    <div class="dashboard-card-value" style="
    color:#f8fafc;
    font-size:34px;
    font-weight:900;
    margin-bottom:8px;
    ">
    ${portfolio_stats['market_value']:,.0f}
    </div>

    <div class="dashboard-card-body" style="
    color:#94a3b8;
    font-size:14px;
    margin-bottom:18px;
    ">
    {t['portfolio_value']}
    </div>

    <div class="dashboard-card-value" style="
    color:#38bdf8;
    font-size:24px;
    font-weight:800;
    margin-bottom:6px;
    ">
    {largest_position['ticker']}
    </div>

    <div class="dashboard-card-body" style="
    color:#94a3b8;
    font-size:14px;
    margin-bottom:18px;
    ">
    {t['largest_position']}
    </div>

    <div class="dashboard-card-value" style="
    color:#22c55e;
    font-size:20px;
    font-weight:800;
    ">
    ${portfolio_stats['pnl']:,.0f}
    </div>

    <div class="dashboard-card-body" style="
    color:#94a3b8;
    font-size:14px;
    ">
    {t['total_gain_loss']}
    </div>

    </div>
    """,
            unsafe_allow_html=True
        )
    with summary1:

        # =====================================================
        # MARKET REGIME PANEL
        # =====================================================

        st.markdown(
            f"""
    <div class="glow" style="
    background:rgba(15,23,42,0.78);
    border:1px solid {regime['color']};
    border-radius:22px;
    padding:24px;
    margin-top:20px;
    margin-bottom:28px;
    box-shadow:0 0 24px {regime['color']}33;
    ">

    <div class="dashboard-card-title" style="
    color:{regime['color']};
    font-size:14px;
    font-weight:700;
    letter-spacing:1px;
    margin-bottom:12px;
    ">
    {t['market_regime']}
    </div>

    <div class="dashboard-card-value" style="
    color:{regime['color']};
    font-size:42px;
    font-weight:900;
    margin-bottom:14px;
    text-shadow:0 0 18px {regime['color']}55;
    ">
    {regime['name']}
    </div>

    <div class="dashboard-card-body" style="
    color:#e2e8f0;
    font-size:18px;
    line-height:1.8;
    ">
    {t['emotion']}: {regime['emotion']}
    </div>

    <div class="dashboard-card-body" style="
    color:#94a3b8;
    font-size:15px;
    margin-top:10px;
    line-height:1.7;
    ">
    {t['drivers']}:
    {", ".join(regime['drivers']) if regime['drivers'] else t['no_drivers']}
    </div>

    </div>
    """,
        unsafe_allow_html=True
    )
    # =====================================================
    # AI SIGNAL ENGINE
    # =====================================================

    signals = []

    if regime["name"] == "RISK_OFF":
        signals.append(
            "🔴 Defensive market behavior detected across growth assets."
        )

    if macro_changes.get("VIX", 0) > 20:
        signals.append(
            "⚠️ Volatility expansion suggests elevated macro fear."
        )

    if tesla_sentiment == "BULLISH":
        signals.append(
            "🟢 Tesla and AI momentum remain structurally supportive."
        )

    if ai_momentum >= 90:
        signals.append(
            "🧠 AI infrastructure demand remains extremely strong."
        )

    if macro_changes.get("BTC", 0) > 1:
        signals.append(
            "₿ Crypto strength suggests speculative appetite returning."
        )

    if len(signals) == 0:
        signals.append(
            "⚪ No major macro signals detected."
        )


    # =====================================================
    # MARKET NARRATOR LOGIC
    # =====================================================

    if DEV_MODE or not USE_AI_MARKET_BRIEF:

        oil_move = macro_changes.get("OIL", 0)
        btc_move = macro_changes.get("BTC", 0)
        nasdaq_move = macro_changes.get("NASDAQ", 0)
        vix_move = macro_changes.get("VIX", 0)

        if regime["name"] == "RISK_OFF":

            market_narrative = (
                f"Volatility remains elevated with VIX moving "
                f"{vix_move:.1f}% while growth assets face defensive positioning."
            )

        elif regime["name"] == "RISK_ON":

            market_narrative = (
                f"Risk appetite remains constructive as NASDAQ advances "
                f"{nasdaq_move:.1f}% and speculative activity improves."
            )

        else:

            market_narrative = (
                f"Cross-asset signals remain mixed with NASDAQ at "
                f"{nasdaq_move:.1f}% and Bitcoin at {btc_move:.1f}%."
            )

    else:

        from core.ai_brain import generate_market_brief

        market_narrative = generate_market_brief(
            regime,
            market_context,
            signals,
            radar_data=None
        )

    with summary2:

        # =====================================================
        # MARKET NARRATIVE PANEL
        # =====================================================

        st.markdown(
            f"""
<div class="glow" style="
background:rgba(15,23,42,0.72);
border:1px solid rgba(56,189,248,0.22);
border-radius:22px;
padding:24px;
margin-top:20px;
margin-bottom:28px;
box-shadow:0 0 28px rgba(56,189,248,0.10);
">

<div class="dashboard-card-title" style="
color:#38bdf8;
font-size:14px;
font-weight:700;
letter-spacing:1px;
margin-bottom:14px;
">
{t['market_narrative']}
</div>

<div class="dashboard-card-body" style="
color:#e2e8f0;
font-size:20px;
line-height:1.8;
">
{market_narrative}
</div>

</div>
""",
            unsafe_allow_html=True
        )

        # =====================================================
        # REGIME HISTORY
        # =====================================================

        with st.expander("📈 Regime History"):

            history = load_regime_history()

            st.dataframe(
                history.tail(30),
                use_container_width=True
            )  
with portfolio_tab:
    # =====================================================
    # PORTFOLIO DATA
    # =====================================================

    portfolio_stats = calculate_portfolio()

    positions = portfolio_stats["positions"]

    # =====================================================
    # PORTFOLIO SUMMARY
    # =====================================================

    st.subheader("💰 Portfolio Summary")

    if is_mobile:
        c1 = st.container()
        c2 = st.container()
        c3 = st.container()
        c4 = st.container()
    else:
        c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Portfolio Value",
            f"${portfolio_stats['market_value']:,.0f}"
        )

    with c2:
        st.metric(
            "Cost Basis",
            f"${portfolio_stats['cost_basis']:,.0f}"
        )

    with c3:
        st.metric(
            "Gain / Loss",
            f"${portfolio_stats['pnl']:,.0f}"
        )

    with c4:
        st.metric(
            "Return %",
            f"{portfolio_stats['return_pct']:.1f}%"
        )

    # =====================================================
    # WINNER / LOSER
    # =====================================================

    if positions:

        winner = max(
            positions,
            key=lambda x: x["pnl"]
        )

        loser = min(
            positions,
            key=lambda x: x["pnl"]
        )
        if is_mobile:
            winner_col = st.container()
            loser_col = st.container()
        else:
            winner_col, loser_col = st.columns(2)

        with winner_col:

            st.markdown(
                f"""
        <div style="
        background:rgba(15,23,42,0.88);
        border:1px solid #22c55e;
        border-radius:22px;
        padding:24px;
        box-shadow:0 0 24px rgba(34,197,94,0.25);
        ">

        <div style="
        color:#22c55e;
        font-size:15px;
        font-weight:700;
        margin-bottom:12px;
        ">
        🏆 LARGEST WINNER
        </div>

        <div style="
        color:#f8fafc;
        font-size:40px;
        font-weight:900;
        ">
        {winner["ticker"]}
        </div>

        <div style="
        color:#22c55e;
        font-size:24px;
        font-weight:700;
        ">
        ${winner["pnl"]:,.0f}
        </div>

        </div>
        """,
                unsafe_allow_html=True
            )

        with loser_col:

            st.markdown(
                f"""
        <div style="
        background:rgba(15,23,42,0.88);
        border:1px solid #f87171;
        border-radius:22px;
        padding:24px;
        box-shadow:0 0 24px rgba(248,113,113,0.25);
        ">

        <div style="
        color:#f87171;
        font-size:15px;
        font-weight:700;
        margin-bottom:12px;
        ">
        💀 LARGEST LOSER
        </div>

        <div style="
        color:#f8fafc;
        font-size:40px;
        font-weight:900;
        ">
        {loser["ticker"]}
        </div>

        <div style="
        color:#f87171;
        font-size:24px;
        font-weight:700;
        ">
        ${loser["pnl"]:,.0f}
        </div>

        </div>
        """,
                unsafe_allow_html=True
            )
    # =====================================================
    # PORTFOLIO ALLOCATION
    # =====================================================

    st.subheader("📊 Portfolio Allocation")

    allocation_df = pd.DataFrame([
        {
            "Ticker": p["ticker"],
            "Allocation": p["market_value"]
        }
        for p in positions
    ])

    fig = px.pie(
        allocation_df,
        values="Allocation",
        names="Ticker",
        hole=0.45
    )

    fig.update_layout(
        paper_bgcolor="#050816",
        plot_bgcolor="#050816",
        font=dict(color="#e2e8f0")
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # =====================================================
    # PORTFOLIO RISK ASSESSMENT
    # =====================================================

    st.subheader("🧠 Portfolio Risk Assessment")

    largest_position = max(
        positions,
        key=lambda x: x["market_value"]
    )

    allocation_pct = (
        largest_position["market_value"]
        / portfolio_stats["market_value"]
    ) * 100

    risk_level = "LOW"

    if allocation_pct > 40:
        risk_level = "HIGH"

    elif allocation_pct > 25:
        risk_level = "MODERATE"

    portfolio_theme = "US Technology & AI"

    risk_note = "Portfolio remains diversified."

    if allocation_pct > 40:

        risk_note = (
            f"Portfolio is heavily dependent on "
            f"{largest_position['ticker']}."
        )

    st.info(
        f"""

    Current Regime: {regime['name']}

    Portfolio Risk: {risk_level}

    Largest Position:
    {largest_position['ticker']} ({allocation_pct:.1f}%)

    Theme Exposure:
    {portfolio_theme}

    Risk Note:
    {risk_note}
    """
    )

    # =====================================================
    # POSITION BREAKDOWN
    # =====================================================

    with st.expander("📊 Position Breakdown"):

        positions_df = pd.DataFrame(
            positions
        )

        if not positions_df.empty:

            positions_df = positions_df[
                [
                    "ticker",
                    "shares",
                    "current_price",
                    "market_value",
                    "pnl",
                    "pnl_pct"
                ]
            ]

            positions_df.columns = [
                "Ticker",
                "Shares",
                "Price",
                "Market Value",
                "P&L",
                "Return %"
            ]

            st.dataframe(
                positions_df,
                use_container_width=True
            )

with financials_tab:

    st.subheader("📄 Financial Results")

    st.markdown(
        """
Official investor relations pages for your current holdings.
Use these links for quarterly results, B/S, P&L, cash flow statements,
earnings decks, webcasts, and SEC filings.
"""
    )

    holdings = load_portfolio()
    holdings_tickers = list(holdings.keys())

    if is_mobile:
        financial_cols = [st.container()]
    else:
        financial_cols = st.columns(2)

    for i, ticker in enumerate(holdings_tickers):
        links = FINANCIAL_RESULTS_LINKS.get(ticker)

        if links is None:
            links = {
                "name": ticker,
                "category": "Holding",
                "ir": f"https://www.google.com/search?q={ticker}+investor+relations",
                "results": f"https://www.google.com/search?q={ticker}+quarterly+results",
                "sec": f"https://www.sec.gov/edgar/search/#/q={ticker}",
                "note": "No official link saved yet. Search links are shown as fallback."
            }

        with financial_cols[i % len(financial_cols)]:

            st.markdown(
                f"""
<div style="
background:rgba(15,23,42,0.82);
border:1px solid rgba(56,189,248,0.25);
border-radius:18px;
padding:20px;
margin-bottom:18px;
box-shadow:0 0 22px rgba(56,189,248,0.08);
">

<div style="
display:flex;
justify-content:space-between;
align-items:flex-start;
gap:16px;
margin-bottom:12px;
">
<div>
<div style="color:#f8fafc;font-size:26px;font-weight:900;">{ticker}</div>
<div style="color:#94a3b8;font-size:14px;margin-top:4px;">{links['name']}</div>
</div>
<div style="
color:#38bdf8;
font-size:12px;
font-weight:800;
border:1px solid rgba(56,189,248,0.28);
border-radius:999px;
padding:4px 10px;
white-space:nowrap;
">
{links['category']}
</div>
</div>

<div style="
color:#cbd5e1;
font-size:14px;
line-height:1.7;
margin-bottom:16px;
">
{links['note']}
</div>

<div style="
display:grid;
grid-template-columns:repeat(3, minmax(0, 1fr));
gap:10px;
">
<a href="{links['ir']}" target="_blank" style="
text-decoration:none;
text-align:center;
color:#f8fafc;
font-weight:800;
font-size:13px;
border:1px solid rgba(56,189,248,0.35);
border-radius:12px;
padding:10px 8px;
background:rgba(2,6,23,0.45);
">IR</a>

<a href="{links['results']}" target="_blank" style="
text-decoration:none;
text-align:center;
color:#f8fafc;
font-weight:800;
font-size:13px;
border:1px solid rgba(34,197,94,0.35);
border-radius:12px;
padding:10px 8px;
background:rgba(2,6,23,0.45);
">Results</a>

<a href="{links['sec']}" target="_blank" style="
text-decoration:none;
text-align:center;
color:#f8fafc;
font-weight:800;
font-size:13px;
border:1px solid rgba(250,204,21,0.35);
border-radius:12px;
padding:10px 8px;
background:rgba(2,6,23,0.45);
">SEC</a>
</div>

</div>
""",
                unsafe_allow_html=True,
            )

with research_tab:
    st.session_state["active_ticker"] = st.text_input(
        t["search"],
        value=st.session_state["active_ticker"]
    ).upper()

    ticker = st.session_state["active_ticker"]
    stock = yf.Ticker(ticker)

    try:
        info = stock.info

    except:
        st.error("Ticker not found")
        st.stop()

    # =====================================
    # COMPANY HEADER
    # =====================================

    company_name = info.get(
        "longName",
        ticker
    )

    sector = info.get(
        "sector",
        "N/A"
    )

    industry = info.get(
        "industry",
        "N/A"
    )

    market_cap = info.get(
        "marketCap",
        0
    )

    st.markdown(
        f"""
<div style="
background:rgba(15,23,42,0.85);
border:1px solid rgba(56,189,248,0.25);
border-radius:24px;
padding:28px;
margin-bottom:25px;
">

<div style="
font-size:38px;
font-weight:900;
color:#f8fafc;
">
{company_name}
</div>

<div style="
color:#94a3b8;
font-size:18px;
margin-top:8px;
">
{sector} • {industry}
</div>

<div style="
color:#38bdf8;
font-size:24px;
font-weight:700;
margin-top:18px;
">
${market_cap/1_000_000_000_000:.2f}T Market Cap
</div>

</div>
""",
        unsafe_allow_html=True
    )
    if is_mobile:
        popular = [st.container() for _ in range(6)]
    else:
        popular = st.columns(6)

    tickers = [
        "AAPL",
        "TSLA",
        "NVDA",
        "META",
        "PLTR",
        "MSFT"
    ]
    # =====================================================
    # AI ANALYST MODULE
    # =====================================================

    st.subheader("🤖 AI Analyst")

    revenue_growth = info.get("revenueGrowth", 0) or 0
    gross_margin = info.get("grossMargins", 0) or 0
    forward_pe = info.get("forwardPE", 0) or 0
    market_cap = info.get("marketCap", 0) or 0

    bull_case = []
    bear_case = []
    key_risks = []

    if revenue_growth > 0.15:
        bull_case.append("Revenue growth remains strong.")
    elif revenue_growth > 0:
        bull_case.append("Revenue growth remains positive.")

    if gross_margin > 0.50:
        bull_case.append("Profitability remains excellent.")
    elif gross_margin > 0.30:
        bull_case.append("Margins remain healthy.")

    if market_cap > 500_000_000_000:
        bull_case.append("Large-cap scale provides financial stability.")

    if forward_pe > 40:
        bear_case.append("Valuation appears elevated.")
    elif forward_pe > 25:
        bear_case.append("Valuation is not cheap.")

    if revenue_growth <= 0:
        bear_case.append("Revenue growth is slowing or negative.")

    if gross_margin < 0.30:
        bear_case.append("Margins may be under pressure.")

    if forward_pe > 40:
        key_risks.append("High expectations are already priced in.")

    if revenue_growth <= 0:
        key_risks.append("Growth slowdown could pressure investor sentiment.")

    if gross_margin < 0.30:
        key_risks.append("Lower profitability may limit upside.")

    if len(bull_case) == 0:
        bull_case.append("No strong bullish signal detected from current fundamentals.")

    if len(bear_case) == 0:
        bear_case.append("No major bearish signal detected from current fundamentals.")

    if len(key_risks) == 0:
        key_risks.append("Main risk is valuation, competition, or macro pressure.")

    if len(bull_case) > len(bear_case):
        conclusion = "Moderately Bullish"
        conclusion_color = "#22c55e"
    elif len(bear_case) > len(bull_case):
        conclusion = "Cautious"
        conclusion_color = "#f87171"
    else:
        conclusion = "Neutral"
        conclusion_color = "#facc15"
    if is_mobile:
        a1 = st.container()
        a2 = st.container()
        a3 = st.container()
        a4 = st.container()
    else:
        a1, a2, a3, a4 = st.columns(4)

    with a1:
        st.markdown(
            f"""
    <div style="
    background:rgba(15,23,42,0.88);
    border:1px solid #22c55e;
    border-radius:22px;
    padding:22px;
    min-height:220px;
    ">

    <div style="
    color:#22c55e;
    font-size:14px;
    font-weight:800;
    letter-spacing:1px;
    margin-bottom:14px;
    ">
    🟢 BULL CASE
    </div>

    <div style="
    color:#e2e8f0;
    font-size:15px;
    line-height:1.8;
    ">
    {"<br>".join(["• " + x for x in bull_case])}
    </div>

    </div>
    """,
            unsafe_allow_html=True
        )

    with a2:
        st.markdown(
            f"""
    <div style="
    background:rgba(15,23,42,0.88);
    border:1px solid #f87171;
    border-radius:22px;
    padding:22px;
    min-height:260px;
    ">

    <div style="
    color:#f87171;
    font-size:14px;
    font-weight:800;
    letter-spacing:1px;
    margin-bottom:14px;
    ">
    🔴 BEAR CASE
    </div>

    <div style="
    color:#e2e8f0;
    font-size:15px;
    line-height:1.8;
    ">
    {"<br>".join(["• " + x for x in bear_case])}
    </div>

    </div>
    """,
            unsafe_allow_html=True
        )

    with a3:
        st.markdown(
            f"""
    <div style="
    background:rgba(15,23,42,0.88);
    border:1px solid #facc15;
    border-radius:22px;
    padding:22px;
    min-height:260px;
    ">

    <div style="
    color:#facc15;
    font-size:14px;
    font-weight:800;
    letter-spacing:1px;
    margin-bottom:14px;
    ">
    🟡 KEY RISKS
    </div>

    <div style="
    color:#e2e8f0;
    font-size:15px;
    line-height:1.8;
    ">
    {"<br>".join(["• " + x for x in key_risks])}
    </div>

    </div>
    """,
            unsafe_allow_html=True
        )

    with a4:
        st.markdown(
            f"""
    <div style="
    background:rgba(15,23,42,0.88);
    border:1px solid {conclusion_color};
    border-radius:22px;
    padding:22px;
    min-height:260px;
    box-shadow:0 0 24px {conclusion_color}55;
    ">

    <div style="
    color:{conclusion_color};
    font-size:14px;
    font-weight:800;
    letter-spacing:1px;
    margin-bottom:14px;
    ">
    🤖 AI CONCLUSION
    </div>

    <div style="
    color:#f8fafc;
    font-size:36px;
    font-weight:900;
    line-height:1.4;
    ">
    {conclusion}
    </div>

    </div>
    """,
            unsafe_allow_html=True
        )
    for col, symbol in zip(popular, tickers):
        if col.button(symbol):
            st.session_state["active_ticker"] = symbol
    if is_mobile:
        c1 = st.container()
        c2 = st.container()
        c3 = st.container()
        c4 = st.container()
    else:
        c1, c2, c3, c4 = st.columns(4)

    cards = [
        (
            "💰 MARKET CAP",
            f"${info.get('marketCap', 0)/1_000_000_000_000:.2f}T",
            "#facc15"
        ),
        (
            "⚖️ FORWARD PE",
            f"{info.get('forwardPE', 0):.1f}",
            "#38bdf8"
        ),
        (
            "📈 REVENUE GROWTH",
            f"{info.get('revenueGrowth', 0)*100:.1f}%",
            "#22c55e"
        ),
        (
            "🏭 GROSS MARGIN",
            f"{info.get('grossMargins', 0)*100:.1f}%",
            "#a855f7"
        )
    ]

    for col, (title, value, color) in zip(
        [c1, c2, c3, c4],
        cards
    ):

        with col:

            st.markdown(
                f"""
<div style="
background:rgba(15,23,42,0.88);
border:1px solid {color};
border-radius:22px;
padding:24px;
text-align:center;
box-shadow:0 0 24px {color}55;
">

<div style="
color:{color};
font-size:14px;
font-weight:700;
margin-bottom:12px;
letter-spacing:1px;
">
{title}
</div>

<div style="
color:#f8fafc;
font-size:34px;
font-weight:900;
">
{value}
</div>

</div>
""",
                unsafe_allow_html=True
            )
    # =====================================================
    # AI INVESTMENT THESIS
    # =====================================================

    st.subheader("📈 Investment Thesis")

    thesis_points = []

    if revenue_growth > 0.15:
        thesis_points.append(
            "Revenue growth remains a meaningful driver of future earnings expansion."
        )

    if gross_margin > 0.45:
        thesis_points.append(
            "Strong margins suggest durable competitive advantages and pricing power."
        )

    if market_cap > 500_000_000_000:
        thesis_points.append(
            "Large-scale operations provide resilience during economic uncertainty."
        )

    if forward_pe < 25:
        thesis_points.append(
            "Current valuation remains relatively reasonable compared with growth prospects."
        )

    if len(thesis_points) == 0:
        thesis_points.append(
            "Investment case appears balanced with no dominant bullish driver."
        )
    st.markdown(
        f"""
    <div style="
    background:rgba(15,23,42,0.88);
    border:1px solid rgba(56,189,248,0.25);
    border-radius:22px;
    padding:24px;
    margin-bottom:20px;
    ">

    <div style="
    color:#38bdf8;
    font-size:14px;
    font-weight:800;
    letter-spacing:1px;
    margin-bottom:15px;
    ">
    📈 INVESTMENT THESIS
    </div>

    <div style="
    color:#e2e8f0;
    font-size:17px;
    line-height:1.9;
    ">
    {"<br><br>".join(["• " + x for x in thesis_points])}
    </div>

    </div>
    """,
        unsafe_allow_html=True
    )
    # =====================================================
    # THESIS BREAKERS
    # =====================================================

    st.subheader("⚠️ Thesis Breakers")

    thesis_breakers = []

    if revenue_growth > 0:
        thesis_breakers.append(
            "Revenue growth slows materially from current levels."
        )

    if gross_margin > 0.40:
        thesis_breakers.append(
            "Margin compression reduces profitability."
        )

    if market_cap > 500_000_000_000:
        thesis_breakers.append(
            "Large-company growth becomes increasingly difficult."
        )

    if forward_pe > 25:
        thesis_breakers.append(
            "Valuation contracts despite continued business execution."
        )

    if len(thesis_breakers) == 0:
        thesis_breakers.append(
            "No obvious thesis breaker detected from current fundamentals."
        )
    st.markdown(
    f"""
<div style="
background:rgba(15,23,42,0.88);
border:1px solid rgba(248,113,113,0.35);
border-radius:22px;
padding:24px;
margin-bottom:20px;
">

<div style="
color:#f87171;
font-size:14px;
font-weight:800;
letter-spacing:1px;
margin-bottom:15px;
">
⚠️ THESIS BREAKERS
</div>

<div style="
color:#e2e8f0;
font-size:17px;
line-height:1.9;
">
{"<br><br>".join(["• " + x for x in thesis_breakers])}
</div>

</div>
""",
    unsafe_allow_html=True
)
    # =====================================================
    # INVESTMENT QUALITY SCORE
    # =====================================================

    score = 50

    # Growth

    if revenue_growth > 0.20:
        score += 15

    elif revenue_growth > 0.10:
        score += 10

    # Profitability

    if gross_margin > 0.50:
        score += 15

    elif gross_margin > 0.30:
        score += 10

    # Valuation

    if forward_pe < 25:
        score += 10

    elif forward_pe > 40:
        score -= 10

    # Scale

    if market_cap > 500_000_000_000:
        score += 10

    score = max(0, min(score, 100))

    if score >= 80:
        grade = "A"
        score_color = "#22c55e"

    elif score >= 70:
        grade = "B"
        score_color = "#38bdf8"

    elif score >= 60:
        grade = "C"
        score_color = "#facc15"

    else:
        grade = "D"
        score_color = "#f87171"
    st.markdown(
    f"""
<div style="
background:rgba(15,23,42,0.88);
border:1px solid {score_color};
border-radius:22px;
padding:28px;
margin-bottom:20px;
text-align:center;
box-shadow:0 0 24px {score_color}55;
">

<div style="
color:{score_color};
font-size:14px;
font-weight:800;
letter-spacing:1px;
margin-bottom:14px;
">
🏆 INVESTMENT QUALITY SCORE
</div>

<div style="
color:#f8fafc;
font-size:56px;
font-weight:900;
line-height:1;
margin-bottom:10px;
">
{score}
</div>

<div style="
color:{score_color};
font-size:26px;
font-weight:800;
">
GRADE {grade}
</div>

</div>
""",
    unsafe_allow_html=True
)
    st.subheader("🤖 AI Research Summary")

    try:

        revenue_growth = info.get(
            "revenueGrowth",
            0
        )

        gross_margin = info.get(
            "grossMargins",
            0
        )

        summary = []

        if revenue_growth > 0.10:
            summary.append(
                "📈 Revenue growth remains strong."
            )

        elif revenue_growth > 0:
            summary.append(
                "📊 Revenue growth remains positive."
            )

        else:
            summary.append(
                "⚠️ Revenue growth is slowing."
            )

        if gross_margin > 0.50:
            summary.append(
                "💰 Profitability remains excellent."
            )

        elif gross_margin > 0.30:
            summary.append(
                "🟢 Margins remain healthy."
            )

        else:
            summary.append(
                "🔴 Margins are under pressure."
            )

        if info.get(
            "marketCap",
            0
        ) > 500000000000:

            summary.append(
                "🏦 Large-cap balance sheet strength."
            )

        st.info(
            "\n\n".join(summary)
        )

    except:

        pass
    # =====================================================
    # QUARTERLY FINANCIALS
    # =====================================================

    st.subheader("📈 Quarterly Financials")

    try:

        quarterly = stock.quarterly_financials

        revenue = quarterly.loc["Total Revenue"].iloc[0]

        net_income = quarterly.loc["Net Income"].iloc[0]

        if is_mobile:
            f1 = st.container()
            f2 = st.container()
        else:
            f1, f2 = st.columns(2)

        with f1:
            st.metric(
                "Latest Revenue",
                format_billions(revenue)
            )

        with f2:
            st.metric(
                "Latest Net Income",
                format_billions(net_income)
            )

        with st.expander("📋 Full Financial Statement"):

            st.dataframe(
                quarterly,
                use_container_width=True
            )

    except Exception as e:

        st.error(
            f"Could not load financials: {e}"
        )

    # =====================================================
    # BALANCE SHEET
    # =====================================================

    st.subheader("🏦 Balance Sheet")

    try:

        balance = stock.quarterly_balance_sheet

        cash = balance.loc[
            "Cash And Cash Equivalents"
        ].iloc[0]

        debt = balance.loc[
            "Total Debt"
        ].iloc[0]

        if is_mobile:
            b1 = st.container()
            b2 = st.container()
        else:
            b1, b2 = st.columns(2)

        with b1:
            st.metric(
                "Cash",
                format_billions(cash)
            )

        with b2:
            st.metric(
                "Debt",
                format_billions(debt)
            )

        with st.expander(
            "📋 Full Balance Sheet"
        ):

            st.dataframe(
                balance,
                use_container_width=True
            )

    except Exception:

        st.warning(
            "Balance sheet data unavailable."
        )

    # =====================================================
    # CASH FLOW
    # =====================================================

    st.subheader("💵 Cash Flow")

    try:

        cashflow = stock.quarterly_cashflow

        operating_cf = cashflow.loc[
            "Operating Cash Flow"
        ].iloc[0]

        free_cf = cashflow.loc[
            "Free Cash Flow"
        ].iloc[0]

        if is_mobile:
            cf1 = st.container()
            cf2 = st.container()
        else:
            cf1, cf2 = st.columns(2)

        with cf1:
            st.metric(
                "Operating Cash Flow",
                format_billions(
                    operating_cf
                )
            )

        with cf2:
            st.metric(
                "Free Cash Flow",
                format_billions(
                    free_cf
                )
            )

        with st.expander(
            "📋 Full Cash Flow Statement"
        ):

            st.dataframe(
                cashflow,
                use_container_width=True
            )

    except Exception:

        st.warning(
            "Cash flow data unavailable."
        )
with watchlist_tab:

    st.subheader("⭐ Watchlist")

    rows = []

    for ticker in WATCHLIST:

        stock = yf.Ticker(ticker)

        hist = stock.history(period="5d")

        if hist.empty:
            continue

        close_prices = hist["Close"].dropna()

        if len(close_prices) < 2:
            continue

        latest = close_prices.iloc[-1]
        previous = close_prices.iloc[-2]

        pct = (
            (latest - previous)
            / previous
        ) * 100

        rows.append(
            {
                "Ticker": ticker,
                "Price": round(latest, 2),
                "1 Day %": round(pct, 2)
            }
        )
    
    watchlist_df = pd.DataFrame(rows)

    watchlist_df = watchlist_df.dropna(
        subset=["1 Day %"]
    )

    if watchlist_df.empty:
        st.warning("Watchlist data unavailable right now.")
        st.stop()

    strongest = watchlist_df.loc[
        watchlist_df["1 Day %"].idxmax()
    ]

    weakest = watchlist_df.loc[
        watchlist_df["1 Day %"].idxmin()
    ]

    if is_mobile:
        w1 = st.container()
        w2 = st.container()
    else:
        w1, w2 = st.columns(2)

    with w1:
        st.metric(
            "🔥 Strongest",
            strongest["Ticker"],
            f"{strongest['1 Day %']}%"
        )

    with w2:
        st.metric(
            "💀 Weakest",
            weakest["Ticker"],
            f"{weakest['1 Day %']}%"
        )
    if is_mobile:
        watch_cols = [st.container()]
    else:
        watch_cols = st.columns(3)

    for i, row in watchlist_df.iterrows():

        ticker = row["Ticker"]
        price = row["Price"]
        pct = row["1 Day %"]

        color = "#22c55e" if pct >= 0 else "#f87171"
        arrow = "▲" if pct >= 0 else "▼"

        with watch_cols[i % len(watch_cols)]:

            st.markdown(
                f"""
    <div style="
    background:rgba(15,23,42,0.88);
    border:1px solid {color};
    border-radius:22px;
    padding:24px;
    margin-bottom:20px;
    text-align:center;
    box-shadow:0 0 24px {color}55;
    ">

    <div style="
    color:#94a3b8;
    font-size:15px;
    letter-spacing:2px;
    margin-bottom:12px;
    ">
    {ticker}
    </div>

    <div style="
    color:#f8fafc;
    font-size:34px;
    font-weight:900;
    margin-bottom:10px;
    ">
    ${price:.2f}
    </div>

    <div style="
    color:{color};
    font-size:24px;
    font-weight:800;
    ">
    {arrow} {pct:.2f}%
    </div>

    </div>
    """,
                unsafe_allow_html=True,
            )
