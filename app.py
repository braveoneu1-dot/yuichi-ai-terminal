import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
import json
from datetime import datetime, date, timedelta

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


def get_latest_change(symbol):

    stock = yf.Ticker(symbol)

    regular_history = stock.history(period="5d")

    if regular_history.empty:
        return None

    regular_closes = regular_history["Close"].dropna()

    if len(regular_closes) < 2:
        return None

    regular_close = regular_closes.iloc[-1]
    previous_close = regular_closes.iloc[-2]

    if previous_close == 0 or regular_close == 0:
        return None

    daily_pct_change = (
        (regular_close - previous_close)
        / previous_close
    ) * 100

    latest_price = regular_close
    extended_pct_change = None
    price_type = "REG"

    extended_history = stock.history(
        period="5d",
        interval="1m",
        prepost=True
    )

    if not extended_history.empty:
        extended_closes = extended_history["Close"].dropna()

        if not extended_closes.empty:
            latest_price = extended_closes.iloc[-1]
            extended_pct_change = (
                (latest_price - regular_close)
                / regular_close
            ) * 100

            if abs(extended_pct_change) >= 0.01:
                price_type = "EXT"

    if pd.isna(daily_pct_change):
        return None

    return {
        "latest": latest_price,
        "previous": previous_close,
        "regular_close": regular_close,
        "pct_change": daily_pct_change,
        "daily_pct_change": daily_pct_change,
        "extended_pct_change": extended_pct_change,
        "price_type": price_type
    }

is_mobile = False

HEATMAP_TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "AVGO",
    "JPM", "V", "LLY", "MA", "NFLX", "XOM", "COST", "WMT",
    "UNH", "ORCL", "HD", "PG", "JNJ", "BAC", "ABBV", "KO",
    "PLTR", "AMD", "CRM", "CSCO", "CVX", "MRK", "MCD", "DIS",
    "ADBE", "PEP", "TMO", "ABT", "ACN", "WFC", "QCOM", "INTC",
    "TXN", "IBM", "GE", "NOW", "ISRG", "AMGN", "PM", "UBER",
    "GS", "RTX", "SPGI", "CAT", "BKNG", "AXP", "MS", "NEE",
    "PFE", "LOW", "HON", "UNP"
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


def build_calendar_insight(events, language="English"):
    if not events:
        if language == "日本語":
            return "現在のカレンダーファイルには、重要なマーケットイベントは登録されていません。"

        return "No major market events are scheduled in the current calendar file."

    critical_events = [
        event for event in events
        if event["level"].lower() == "critical"
    ]
    focus_events = critical_events if critical_events else events[:3]
    event_types = []
    for event in events:
        if event["type"] not in event_types:
            event_types.append(event["type"])

    if language == "日本語":
        top_events = "、".join(
            jp_event_name(event["event"]) for event in focus_events[:3]
        )
        main_types = "、".join(jp_event_type(event_type) for event_type in event_types[:3])

        return (
            f"今週の注目イベントは、{top_events}です。"
            f"特に{main_types}がマーケットの焦点になりやすく、"
            f"金利、ハイテク大型株、投資家のリスク許容度に影響する可能性があります。"
        )

    top_events = ", ".join(event["event"] for event in focus_events[:3])
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


def jp_market_term(text):
    translations = {
        "RISK_ON": "リスクオン",
        "RISK_OFF": "リスクオフ",
        "NEUTRAL": "中立",
        "greed": "強気",
        "fear": "警戒",
        "uncertain": "様子見",
        "Tech strength": "ハイテク株の強さ",
        "Tech weakness": "ハイテク株の弱さ",
        "Fear rising": "市場の警戒感上昇",
        "Fear easing": "市場の警戒感後退",
        "Oil spike": "原油価格の急騰",
        "Oil collapse easing inflation fears": "原油安によるインフレ懸念の後退",
        "Crypto strength": "暗号資産の強さ",
        "Crypto weakness": "暗号資産の弱さ",
        "No direct calendar catalyst": "直接関係する予定は少なめ",
        "HIGH": "高",
        "MEDIUM": "中",
        "LOW": "低",
    }

    return translations.get(text, text)


def jp_event_type(event_type):
    translations = {
        "Macro / Labor": "マクロ / 雇用",
        "Labor Market": "雇用統計",
        "Business Activity": "景況感",
        "Earnings": "決算",
        "Labor Costs": "労働コスト",
        "Federal Reserve": "FRB",
        "Inflation": "インフレ",
        "Consumer / Sentiment": "消費 / 景況感",
    }

    return translations.get(event_type, event_type)


def jp_event_name(event_name):
    translations = {
        "Trade Balance + JOLTS + Factory Orders": "貿易収支 + JOLTS求人件数 + 製造業受注",
        "Major Earnings: CAT, AMD, MCD, SHOP, SPOT": "主要決算: CAT, AMD, MCD, SHOP, SPOT",
        "ADP Employment Report": "ADP雇用レポート",
        "S&P Global Services PMI + ISM Services PMI": "サービス業PMI + ISMサービス業景況指数",
        "Major Earnings: LLY, UBER, DIS, GFS": "主要決算: LLY, UBER, DIS, GFS",
        "Weekly Jobless Claims": "週間 新規失業保険申請件数",
        "Productivity and Labor Costs": "生産性・労働コスト",
        "Fed Speaker: Alberto Musalem": "FRB要人発言: Alberto Musalem",
        "Major Earnings: DDOG, ABNB, COP, CEG": "主要決算: DDOG, ABNB, COP, CEG",
        "Nonfarm Payrolls Report": "米雇用統計",
        "Fed Speaker: Thomas Barkin": "FRB要人発言: Thomas Barkin",
        "Major Earnings: OKLO, TTWO, ENB, UAA": "主要決算: OKLO, TTWO, ENB, UAA",
        "Consumer Price Index": "消費者物価指数 CPI",
        "Producer Price Index": "生産者物価指数 PPI",
        "Retail Sales + Michigan Consumer Sentiment": "小売売上高 + ミシガン大学消費者信頼感",
    }

    return translations.get(event_name, event_name)


def jp_assets(assets):
    translations = {
        "Stocks": "株式",
        "Bonds": "債券",
        "Gold": "金",
        "Growth": "成長株",
        "Growth Stocks": "成長株",
        "Market Sentiment": "市場心理",
        "Consumer Stocks": "消費関連株",
        "Rates": "金利",
        "Healthcare": "ヘルスケア",
        "Consumer": "消費関連",
        "Semiconductors": "半導体",
        "Industrials": "工業株",
        "Software": "ソフトウェア",
        "Travel": "旅行関連",
        "Energy": "エネルギー",
        "Utilities": "公益株",
        "Nuclear": "原子力",
        "Gaming": "ゲーム",
    }

    translated = assets
    for english, japanese in translations.items():
        translated = translated.replace(english, japanese)

    return translated


def jp_reason_text(reason):
    if reason == "No direct calendar catalyst":
        return jp_market_term(reason)

    parts = [part.strip() for part in reason.split("+")]
    translated_parts = []

    for part in parts:
        translated_parts.append(jp_event_name(jp_event_type(part)))

    return " + ".join(translated_parts)

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
        "heatmap": "🔥 Heatmap",
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
        "refresh_data": "↻ Refresh data",
        "regime_history": "📈 Regime History",
    },
    "日本語": {
        "search": "🔎 企業を検索",
        "dashboard": "🌎 ダッシュボード",
        "portfolio": "💼 ポートフォリオ",
        "financial_results": "📄 決算資料",
        "research": "📑 企業分析",
        "heatmap": "🔥 ヒートマップ",
        "market_command_center": "🌎 マーケット司令室",
        "market_calendar": "### 📅 今週の重要イベント",
        "calendar_insight": "### 🤖 今週の見どころ",
        "portfolio_impact": "### 💼 保有銘柄への影響",
        "market_regime": "現在の市場環境",
        "emotion": "投資家心理",
        "drivers": "主な理由",
        "no_drivers": "大きなマクロ要因は検出されていません",
        "market_narrative": "市場コメント",
        "portfolio_snapshot": "📊 ポートフォリオ概要",
        "portfolio_value": "現在の評価額",
        "largest_position": "最大保有銘柄",
        "total_gain_loss": "含み益 / 含み損",
        "refresh_data": "↻ データを更新",
        "regime_history": "📈 市場環境の履歴",
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

if st.button(t["refresh_data"]):
    st.cache_data.clear()
    st.rerun()

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600;700&family=Inter:wght@400;500;600;700;800;900&display=swap');
    

    section[data-testid="stSidebar"] {
        background-color: #111827;
    }
    .stApp {
        background-color: #050816;
        color: #e2e8f0;
    }

    html, body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        letter-spacing: 0;
    }

    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        letter-spacing: 0;
    }

    code, pre,
    div[data-testid="stMetricValue"],
    .financial-number,
    .ticker-label,
    .ticker-card,
    .dashboard-card-value {
        font-family: 'IBM Plex Mono', 'SFMono-Regular', Menlo, Monaco, Consolas, monospace !important;
        letter-spacing: 0 !important;
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
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: 0 !important;
    }

    div[data-testid="metric-container"] div {
        color: #f8fafc !important;
    }

    div[data-testid="stMetricValue"] {
        font-weight: 500 !important;
        line-height: 1.05 !important;
        color: #f8fafc !important;
        text-shadow: 0 0 16px rgba(248,250,252,0.08);
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
status_html = f"""
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
"""
# =====================================================
# LIVE MACRO DATA
# =====================================================

macro_tickers = {
    "NASDAQ": "^IXIC",
    "S&P 500": "^GSPC",
    "GOLD": "GC=F",
    "OIL": "CL=F",
    "USD/JPY": "JPY=X",
    "BTC": "BTC-USD",
    "NVDA": "NVDA",
    "TSLA": "TSLA",
    "AAPL": "AAPL",
    "MU": "MU"
}

macro_changes = {}

ticker_cards = []

for label, symbol in macro_tickers.items():

    price_data = get_latest_change(symbol)

    if price_data is None:
        continue

    pct_change = price_data["pct_change"]
    macro_changes[label] = pct_change

    color = "#22c55e" if pct_change >= 0 else "#f87171"
    arrow = "▲" if pct_change >= 0 else "▼"
    extended_pct = price_data["extended_pct_change"]
    extended_color = "#94a3b8"
    extended_arrow = ""
    extended_display = "EXT N/A"

    if extended_pct is not None and not pd.isna(extended_pct):
        extended_color = "#22c55e" if extended_pct >= 0 else "#f87171"
        extended_arrow = "▲" if extended_pct >= 0 else "▼"

        if "PRE-MARKET" in market_status:
            extended_label = "PRE"
        elif "AFTER HOURS" in market_status:
            extended_label = "AH"
        else:
            extended_label = price_data["price_type"]

        extended_display = f"{extended_label} {extended_arrow} {extended_pct:.2f}%"

    price_prefix = "" if label in ["NASDAQ", "S&P 500", "USD/JPY"] else "$"
    price_display = f"{price_prefix}{price_data['latest']:,.2f}"

    ticker_cards.append({
        "label": label,
        "price_display": price_display,
        "pct_change": pct_change,
        "color": color,
        "arrow": arrow,
        "extended_color": extended_color,
        "extended_display": extended_display,
        "price_type": price_data["price_type"],
    })

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
# MARKET CONTEXT OBJECT
# =====================================================

market_context = {
    "NASDAQ": round(macro_changes.get("NASDAQ", 0), 2),
    "S&P 500": round(macro_changes.get("S&P 500", 0), 2),
    "BTC": round(macro_changes.get("BTC", 0), 2),
    "OIL": round(macro_changes.get("OIL", 0), 2),
    "VIX": round(macro_changes.get("VIX", 0), 2),
    "USD/JPY": round(macro_changes.get("USD/JPY", 0), 2),
    "GOLD": round(macro_changes.get("GOLD", 0), 2),
    "NVDA": round(macro_changes.get("NVDA", 0), 2),
    "TSLA": round(macro_changes.get("TSLA", 0), 2),
    "AAPL": round(macro_changes.get("AAPL", 0), 2),
    "MU": round(macro_changes.get("MU", 0), 2),
    "market_stress": market_stress,
    "ai_momentum": ai_momentum,
    "tesla_sentiment": tesla_sentiment,
}
dashboard_tab, portfolio_tab, financials_tab, research_tab, heatmap_tab = st.tabs(
    [
        t["dashboard"],
        t["portfolio"],
        t["financial_results"],
        t["research"],
        t["heatmap"]
    ]
)
with dashboard_tab:

    st.markdown(status_html, unsafe_allow_html=True)

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

    regime_name_display = regime["name"]
    emotion_display = regime["emotion"]
    drivers_display = ", ".join(regime["drivers"]) if regime["drivers"] else t["no_drivers"]

    if language == "日本語":
        regime_name_display = jp_market_term(regime["name"])
        emotion_display = jp_market_term(regime["emotion"])
        drivers_display = (
            "、".join(jp_market_term(driver) for driver in regime["drivers"])
            if regime["drivers"]
            else t["no_drivers"]
        )

    with summary2:

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
    {regime_name_display}
    </div>

    <div class="dashboard-card-body" style="
    color:#e2e8f0;
    font-size:18px;
    line-height:1.8;
    ">
    {t['emotion']}: {emotion_display}
    </div>

    <div class="dashboard-card-body" style="
    color:#94a3b8;
    font-size:15px;
    margin-top:10px;
    line-height:1.7;
    ">
    {t['drivers']}: {drivers_display}
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

            if language == "日本語":
                market_narrative = (
                    f"VIXが{vix_move:.1f}%動いており、市場の警戒感はまだ高めです。"
                    f"成長株はやや守りの姿勢になりやすい局面です。"
                )
            else:
                market_narrative = (
                    f"Volatility remains elevated with VIX moving "
                    f"{vix_move:.1f}% while growth assets face defensive positioning."
                )

        elif regime["name"] == "RISK_ON":

            if language == "日本語":
                market_narrative = (
                    f"NASDAQが{nasdaq_move:.1f}%上昇しており、"
                    f"投資家はリスクを取りにいくムードです。"
                    f"成長株やハイテク株には追い風になりやすい流れです。"
                )
            else:
                market_narrative = (
                    f"Risk appetite remains constructive as NASDAQ advances "
                    f"{nasdaq_move:.1f}% and speculative activity improves."
                )

        else:

            if language == "日本語":
                market_narrative = (
                    f"NASDAQは{nasdaq_move:.1f}%、Bitcoinは{btc_move:.1f}%で、"
                    f"市場全体の方向感はまだややまちまちです。"
                    f"大きく攻めるより、次の材料を確認したい局面です。"
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

    with summary3:

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

    ticker_items = ticker_cards
    ticker_rows = [ticker_items[i:i + 5] for i in range(0, len(ticker_items), 5)]

    for ticker_row in ticker_rows:

        if is_mobile:
            macro_cols = [st.container() for _ in ticker_row]
        else:
            macro_cols = st.columns(len(ticker_row))

        for col, ticker_card in zip(macro_cols, ticker_row):

            with col:

                st.markdown(
                    f"""
<div class="ticker-card" style="
background:rgba(15,23,42,0.78);
border:1px solid {ticker_card['color']};
border-radius:16px;
padding:12px 10px;
text-align:center;
box-shadow:0 0 18px {ticker_card['color']}33;
margin-bottom:12px;
min-height:86px;
display:flex;
align-items:center;
justify-content:center;
">

<div class="ticker-label" style="
color:{ticker_card['color']};
font-size:20px;
font-weight:800;
line-height:1.2;
">
{ticker_card['label']}<br>
<span style="color:#f8fafc;font-size:15px;font-weight:800;">{ticker_card['price_display']}</span><br>
<span style="font-size:13px;">DAY {ticker_card['arrow']} {ticker_card['pct_change']:.2f}%</span><br>
<span style="font-size:12px;color:{ticker_card['extended_color']};">{ticker_card['extended_display']}</span>
</div>

</div>
""",
                    unsafe_allow_html=True
                )

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
            event_name_display = event["event"]
            event_type_display = event["type"]
            event_assets_display = event["assets"]

            if language == "日本語":
                event_name_display = jp_event_name(event["event"])
                event_type_display = jp_event_type(event["type"])
                event_assets_display = jp_assets(event["assets"])
                impact_label = (
                    impact_label
                    .replace("Critical", "最重要")
                    .replace("High", "重要")
                    .replace("Medium", "中")
                    .replace("Low", "低")
                )

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
    {event_name_display}
    </div>

    <div style="
    color:#38bdf8;
    font-size:13px;
    font-weight:700;
    margin-top:6px;
    ">
    {event_type_display}
    </div>

    <div style="
    color:#94a3b8;
    font-size:13px;
    margin-top:6px;
    ">
    {event_assets_display}
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

        st.markdown(build_calendar_insight(events, language))
        st.markdown(t["portfolio_impact"])

        impact_html = ""
        portfolio_tickers = list(load_portfolio().keys())

        for ticker, level, color, reason in portfolio_impact_rows(
            events,
            portfolio_tickers
        ):
            level_display = level
            reason_display = reason

            if language == "日本語":
                level_display = jp_market_term(level)
                reason_display = jp_reason_text(reason)

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
    <div style="color:#94a3b8;font-size:12px;margin-top:3px;">{reason_display}</div>
    </div>
    <div style="color:{color};font-weight:800;white-space:nowrap;">{level_display}</div>
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

    logo_colors = {
        "TSLA": "#ef4444",
        "META": "#3b82f6",
        "PLTR": "#e5e7eb",
        "AAPL": "#94a3b8",
        "MU": "#8b5cf6",
        "SPCX": "#22c55e",
    }

    total_value = sum(p["market_value"] for p in positions)
    sorted_positions = sorted(
        positions,
        key=lambda x: x["market_value"],
        reverse=True
    )

    allocation_html = ""

    for position in sorted_positions:
        ticker = position["ticker"]
        value = position["market_value"]
        allocation = (value / total_value) * 100 if total_value else 0
        color = logo_colors.get(ticker, "#38bdf8")

        allocation_html += f"""
<div style="
display:grid;
grid-template-columns:72px 1fr auto;
gap:16px;
align-items:center;
background:rgba(15,23,42,0.78);
border:1px solid rgba(56,189,248,0.22);
border-radius:18px;
padding:16px;
margin-bottom:12px;
box-shadow:0 0 20px rgba(56,189,248,0.06);
">

<div style="
width:56px;
height:56px;
border-radius:16px;
display:flex;
align-items:center;
justify-content:center;
background:linear-gradient(145deg, rgba(248,250,252,0.08), rgba(15,23,42,0.88));
border:1px solid {color};
box-shadow:0 0 18px {color}44;
color:{color};
font-size:16px;
font-weight:900;
letter-spacing:0;
">
{ticker[:4]}
</div>

<div>
<div style="
display:flex;
justify-content:space-between;
gap:12px;
margin-bottom:8px;
">
<div style="color:#f8fafc;font-size:18px;font-weight:900;">{ticker}</div>
<div style="color:#e2e8f0;font-size:15px;font-weight:800;">${value:,.0f}</div>
</div>

<div style="
height:10px;
background:rgba(148,163,184,0.16);
border-radius:999px;
overflow:hidden;
">
<div style="
height:100%;
width:{allocation:.1f}%;
background:{color};
border-radius:999px;
box-shadow:0 0 16px {color}88;
"></div>
</div>
</div>

<div style="
color:{color};
font-size:22px;
font-weight:900;
min-width:76px;
text-align:right;
">
{allocation:.1f}%
</div>

</div>
"""

    st.markdown(
        allocation_html,
        unsafe_allow_html=True
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
with heatmap_tab:

    st.subheader("🔥 S&P 500 Heatmap")

    rows = []

    for ticker in HEATMAP_TICKERS:

        price_data = get_latest_change(ticker)

        if price_data is None:
            continue

        rows.append({
            "Ticker": ticker,
            "Price": round(price_data["latest"], 2),
            "Day Change": round(price_data["daily_pct_change"], 2),
            "Extended Change": (
                round(price_data["extended_pct_change"], 2)
                if price_data["extended_pct_change"] is not None
                else None
            ),
            "Session": price_data["price_type"]
        })

    heatmap_df = pd.DataFrame(rows)

    if heatmap_df.empty:
        st.warning("Heatmap data unavailable right now.")
        st.stop()

    heatmap_df = heatmap_df.sort_values("Day Change", ascending=False)

    strongest = heatmap_df.iloc[0]
    weakest = heatmap_df.iloc[-1]

    if is_mobile:
        h1 = st.container()
        h2 = st.container()
    else:
        h1, h2 = st.columns(2)

    with h1:
        st.metric(
            "🔥 Strongest",
            strongest["Ticker"],
            f"{strongest['Day Change']}% DAY"
        )

    with h2:
        st.metric(
            "🧊 Weakest",
            weakest["Ticker"],
            f"{weakest['Day Change']}% DAY"
        )

    if is_mobile:
        heat_cols = st.columns(2)
    else:
        heat_cols = st.columns(5)

    for i, row in heatmap_df.iterrows():

        ticker = row["Ticker"]
        price = row["Price"]
        change = row["Day Change"]
        extended_change = row["Extended Change"]
        session = row["Session"]

        intensity = min(abs(change) / 3, 1)

        if change >= 0:
            color = f"rgba(34,197,94,{0.22 + intensity * 0.58:.2f})"
            border = "#22c55e"
            text_color = "#dcfce7"
            arrow = "▲"
        else:
            color = f"rgba(239,68,68,{0.22 + intensity * 0.58:.2f})"
            border = "#ef4444"
            text_color = "#fee2e2"
            arrow = "▼"

        extended_html = """
<div style="
display:inline-flex;
align-items:center;
margin-top:6px;
padding:4px 7px;
border-radius:999px;
background:rgba(2,6,23,0.46);
border:1px solid rgba(148,163,184,0.28);
color:#cbd5e1;
font-size:11px;
font-weight:900;
letter-spacing:0;
">
EXT N/A
</div>
"""

        if extended_change is not None and not pd.isna(extended_change):
            extended_color = "#22c55e" if extended_change >= 0 else "#ef4444"
            extended_arrow = "▲" if extended_change >= 0 else "▼"

            if "PRE-MARKET" in market_status:
                extended_label = "PRE"
            elif "AFTER HOURS" in market_status:
                extended_label = "AH"
            else:
                extended_label = session

            extended_html = f"""
<div style="
display:inline-flex;
align-items:center;
margin-top:6px;
padding:4px 7px;
border-radius:999px;
background:rgba(2,6,23,0.58);
border:1px solid {extended_color};
box-shadow:0 0 10px {extended_color}66;
color:{extended_color};
font-size:11px;
font-weight:900;
letter-spacing:0;
text-shadow:0 1px 2px rgba(0,0,0,0.65);
">
{extended_label} {extended_arrow} {extended_change:.2f}%
</div>
"""

        with heat_cols[i % len(heat_cols)]:

            st.markdown(
                f"""
<div style="
background:{color};
border:1px solid {border};
border-radius:14px;
padding:14px 10px;
margin-bottom:12px;
min-height:112px;
display:flex;
flex-direction:column;
justify-content:space-between;
box-shadow:0 0 18px {border}44;
">

<div style="
color:{text_color};
font-size:20px;
font-weight:900;
line-height:1.1;
">
{ticker}
</div>

<div>
<div style="color:#f8fafc;font-size:13px;font-weight:700;">${price:,.2f}</div>
<div style="color:{text_color};font-size:18px;font-weight:900;margin-top:4px;">
DAY {arrow} {change:.2f}%
</div>
{extended_html}
</div>

</div>
""",
                unsafe_allow_html=True
            )
