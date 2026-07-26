"""Market data helpers backed by yfinance.

All functions are defensive about network/API failures (yfinance can be
flaky or rate-limited) and return `None` / empty structures instead of
raising, so the UI can degrade gracefully.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time as dtime

import pandas as pd
import pytz
import streamlit as st
import yfinance as yf

IST = pytz.timezone("Asia/Kolkata")

INDEX_TICKERS = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
}

MARKET_OPEN_TIME = dtime(9, 15)
MARKET_CLOSE_TIME = dtime(15, 30)


def now_ist() -> datetime:
    return datetime.now(IST)


def is_market_open(now: datetime | None = None) -> bool:
    """Rough NSE/BSE trading-hours check (Mon-Fri, 9:15-15:30 IST).

    Does not account for exchange holidays -- good enough for a demo.
    """
    now = now or now_ist()
    if now.weekday() >= 5:  # Saturday / Sunday
        return False
    return MARKET_OPEN_TIME <= now.time() <= MARKET_CLOSE_TIME


@dataclass
class IndexQuote:
    name: str
    ticker: str
    last_price: float | None
    prev_close: float | None
    change: float | None
    change_pct: float | None
    as_of: datetime | None


@st.cache_data(ttl=60, show_spinner=False)
def fetch_index_quote(name: str, ticker: str) -> IndexQuote:
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="5d", interval="1d")
        if hist.empty:
            return IndexQuote(name, ticker, None, None, None, None, None)

        last_price = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else last_price
        change = last_price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0.0
        as_of = hist.index[-1].to_pydatetime()
        return IndexQuote(name, ticker, last_price, prev_close, change, change_pct, as_of)
    except Exception:
        return IndexQuote(name, ticker, None, None, None, None, None)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_price_history(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period=period, interval=interval)
        return hist
    except Exception:
        return pd.DataFrame()


@dataclass
class StockStats:
    ticker: str
    cmp: float | None = None
    week52_high: float | None = None
    week52_low: float | None = None
    market_cap: float | None = None
    pe_ratio: float | None = None
    name: str | None = None
    currency: str = "INR"


@st.cache_data(ttl=300, show_spinner=False)
def fetch_stock_stats(ticker: str) -> StockStats:
    stats = StockStats(ticker=ticker)
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="1y")
        if not hist.empty:
            stats.cmp = float(hist["Close"].iloc[-1])
            stats.week52_high = float(hist["High"].max())
            stats.week52_low = float(hist["Low"].min())

        info = {}
        try:
            info = tk.get_info()
        except Exception:
            try:
                info = tk.info
            except Exception:
                info = {}

        stats.market_cap = info.get("marketCap")
        stats.pe_ratio = info.get("trailingPE")
        stats.name = info.get("longName") or info.get("shortName") or ticker
        stats.currency = info.get("currency", "INR")
    except Exception:
        pass
    return stats


@st.cache_data(ttl=90, show_spinner=False)
def fetch_live_price(ticker: str) -> float | None:
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="2d", interval="1d")
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception:
        return None


def format_inr(value: float | None, prefix: str = "\u20b9") -> str:
    if value is None:
        return "N/A"
    if abs(value) >= 1e7:
        return f"{prefix}{value / 1e7:,.2f} Cr"
    if abs(value) >= 1e5:
        return f"{prefix}{value / 1e5:,.2f} L"
    return f"{prefix}{value:,.2f}"


def format_market_cap(value: float | None) -> str:
    if value is None:
        return "N/A"
    # yfinance market cap is usually in absolute currency units.
    crore = value / 1e7
    if crore >= 1e5:
        return f"\u20b9{crore / 1e5:,.2f} Lakh Cr"
    return f"\u20b9{crore:,.0f} Cr"
