# =====================================================
# PORTFOLIO ENGINE
# =====================================================

import json
from pathlib import Path
import yfinance as yf
import pandas as pd
# =====================================================
# PORTFOLIO FILE
# =====================================================

PORTFOLIO_FILE = Path("data/portfolio.json")

# =====================================================
# LOAD PORTFOLIO
# =====================================================

def load_portfolio():

    if PORTFOLIO_FILE.exists():

        with open(PORTFOLIO_FILE, "r") as f:

            return json.load(f)

    return {}

# =====================================================
# CALCULATE PORTFOLIO METRICS
# =====================================================

def get_latest_price(ticker):

    stock = yf.Ticker(ticker)

    regular_history = stock.history(period="5d")

    if regular_history.empty:
        return None

    regular_closes = regular_history["Close"].dropna()

    if regular_closes.empty:
        return None

    latest_price = regular_closes.iloc[-1]

    extended_history = stock.history(
        period="5d",
        interval="1m",
        prepost=True
    )

    if not extended_history.empty:
        extended_closes = extended_history["Close"].dropna()

        if not extended_closes.empty:
            latest_price = extended_closes.iloc[-1]

    return latest_price


def calculate_portfolio():

    portfolio = load_portfolio()

    total_market_value = 0
    total_cost_basis = 0

    positions = []

    for ticker, data in portfolio.items():

        shares = data["shares"]
        cost_basis = data["cost_basis"]

        current_price = get_latest_price(ticker)

        if current_price is None:
            continue

        market_value = current_price * shares
        cost_value = cost_basis * shares

        pnl = market_value - cost_value

        pnl_pct = 0

        if cost_value > 0:
            pnl_pct = (pnl / cost_value) * 100

        total_market_value += market_value
        total_cost_basis += cost_value

        positions.append({
            "ticker": ticker,
            "shares": shares,
            "current_price": current_price,
            "market_value": market_value,
            "cost_value": cost_value,
            "pnl": pnl,
            "pnl_pct": pnl_pct
        })

    total_pnl = total_market_value - total_cost_basis

    total_return_pct = 0

    if total_cost_basis > 0:
        total_return_pct = (
            total_pnl / total_cost_basis
        ) * 100

    return {
        "market_value": total_market_value,
        "cost_basis": total_cost_basis,
        "pnl": total_pnl,
        "return_pct": total_return_pct,
        "positions": positions
    }
