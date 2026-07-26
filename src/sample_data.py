"""Hardcoded/demo data used across the app.

Everything in this module is sample data for demo purposes only -- it is
NOT generated from a live model and must never be presented as real
investment advice.
"""

from __future__ import annotations

TOP_AI_PICKS = [
    {
        "stock": "TATA MOTORS",
        "ticker": "TATAMOTORS.NS",
        "signal": "STRONG BUY",
        "cmp": 987.40,
        "target": 1120.00,
        "expected_return": 13.5,
        "horizon": "3-6 Months",
    },
    {
        "stock": "ICICI BANK",
        "ticker": "ICICIBANK.NS",
        "signal": "BUY",
        "cmp": 1284.15,
        "target": 1410.00,
        "expected_return": 9.8,
        "horizon": "6-12 Months",
    },
    {
        "stock": "SUN PHARMA",
        "ticker": "SUNPHARMA.NS",
        "signal": "STRONG BUY",
        "cmp": 1742.60,
        "target": 1985.00,
        "expected_return": 13.9,
        "horizon": "3-6 Months",
    },
]

# Last 7 days of demo predictions vs. actual outcome.
PREDICTION_HISTORY = [
    {"date": "2026-07-19", "stock": "RELIANCE.NS", "predicted": "BUY", "actual": "UP", "correct": True},
    {"date": "2026-07-20", "stock": "TCS.NS", "predicted": "HOLD", "actual": "FLAT", "correct": True},
    {"date": "2026-07-21", "stock": "HDFCBANK.NS", "predicted": "BUY", "actual": "UP", "correct": True},
    {"date": "2026-07-22", "stock": "INFY.NS", "predicted": "SELL", "actual": "UP", "correct": False},
    {"date": "2026-07-23", "stock": "ZOMATO.NS", "predicted": "BUY", "actual": "DOWN", "correct": False},
    {"date": "2026-07-24", "stock": "TATAMOTORS.NS", "predicted": "STRONG BUY", "actual": "UP", "correct": True},
    {"date": "2026-07-25", "stock": "SUNPHARMA.NS", "predicted": "BUY", "actual": "UP", "correct": True},
]

OVERALL_ACCURACY = 71  # percent, hardcoded demo headline figure

WATCHLIST_TICKERS = [
    "RELIANCE.NS",
    "TCS.NS",
    "HDFCBANK.NS",
    "INFY.NS",
    # Zomato Ltd was renamed to Eternal Ltd on the NSE; the old ZOMATO.NS
    # symbol no longer resolves, so we track it under its current ticker.
    "ETERNAL.NS",
]

WATCHLIST_DISPLAY_NAMES = {
    "ETERNAL.NS": "ETERNAL.NS (formerly Zomato)",
}
