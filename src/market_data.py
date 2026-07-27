"""Market data helpers, preferring live Groww data when configured and
falling back to yfinance (Yahoo Finance) otherwise.

All functions are defensive about network/API failures (both Groww and
yfinance can be flaky or rate-limited) and return `None` / empty structures
instead of raising, so the UI can degrade gracefully.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time as dtime

import pandas as pd
import pytz
import streamlit as st
import yfinance as yf

from src import groww_data

IST = pytz.timezone("Asia/Kolkata")

INDEX_TICKERS = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
}

# Global/"foreign exchange" cues used to ground the AI recommendation's
# cross-market analysis (US markets, crude, and USD/INR all commonly move
# Indian markets at the next NSE/BSE open).
GLOBAL_MARKET_TICKERS = {
    "Dow Jones": "^DJI",
    "Nasdaq": "^IXIC",
    "Crude Oil (WTI)": "CL=F",
    "USD/INR": "INR=X",
}

LIVE_QUOTE_TTL = 20  # seconds -- short so the dashboard feels close to live

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
    source: str = "yfinance"


def _fetch_index_quote_groww(name: str, ticker: str) -> IndexQuote | None:
    quote = groww_data.fetch_quote(ticker)
    if not quote or quote.last_price is None:
        return None
    change = quote.change
    change_pct = quote.change_pct
    if change is None and quote.prev_close:
        change = quote.last_price - quote.prev_close
    if change_pct is None and quote.prev_close:
        change_pct = (change / quote.prev_close * 100) if change else 0.0
    return IndexQuote(
        name, ticker, quote.last_price, quote.prev_close, change or 0.0,
        change_pct or 0.0, now_ist(), source="groww",
    )


@st.cache_data(ttl=LIVE_QUOTE_TTL, show_spinner=False)
def fetch_index_quote(name: str, ticker: str) -> IndexQuote:
    if groww_data.is_groww_configured():
        groww_quote = _fetch_index_quote_groww(name, ticker)
        if groww_quote:
            return groww_quote

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


def fetch_global_markets() -> list[IndexQuote]:
    """Quick snapshot of a few global markets/commodities/FX that typically
    influence the next NSE/BSE session, for the AI's "foreign exchange"
    analysis dimension."""
    return [fetch_index_quote(name, ticker) for name, ticker in GLOBAL_MARKET_TICKERS.items()]


def summarize_global_markets(quotes: list[IndexQuote] | None = None) -> str:
    quotes = quotes if quotes is not None else fetch_global_markets()
    lines = []
    for q in quotes:
        if q.last_price is None:
            lines.append(f"{q.name}: data unavailable")
        else:
            lines.append(f"{q.name}: {q.last_price:,.2f} ({q.change_pct:+.2f}%)")
    return "; ".join(lines) if lines else "No global market data available."


@st.cache_data(ttl=300, show_spinner=False)
def fetch_price_history(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    if interval == "1d" and groww_data.is_groww_configured():
        groww_hist = groww_data.fetch_historical(ticker, period=period)
        if groww_hist is not None and not groww_hist.empty:
            return groww_hist

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
    latest_volume: float | None = None
    avg_volume_10d: float | None = None
    avg_volume_3m: float | None = None


@st.cache_data(ttl=300, show_spinner=False)
def fetch_stock_stats(ticker: str) -> StockStats:
    stats = StockStats(ticker=ticker)

    # yfinance is still used for fields Groww's quote doesn't provide
    # (P/E ratio, company name/sector, longer-window average volume), and
    # as the sole source of truth if Groww isn't configured or fails.
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="1y")
        if not hist.empty:
            stats.cmp = float(hist["Close"].iloc[-1])
            stats.week52_high = float(hist["High"].max())
            stats.week52_low = float(hist["Low"].min())
            stats.latest_volume = float(hist["Volume"].iloc[-1])
            stats.avg_volume_10d = float(hist["Volume"].tail(10).mean())

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
        stats.avg_volume_3m = info.get("averageVolume") or info.get("averageVolume10days")
    except Exception:
        pass

    if groww_data.is_groww_configured():
        groww_quote = groww_data.fetch_quote(ticker)
        if groww_quote and groww_quote.last_price is not None:
            stats.cmp = groww_quote.last_price
            stats.latest_volume = groww_quote.volume if groww_quote.volume is not None else stats.latest_volume
            stats.week52_high = groww_quote.week_52_high or stats.week52_high
            stats.week52_low = groww_quote.week_52_low or stats.week52_low
            stats.market_cap = groww_quote.market_cap or stats.market_cap

    return stats


@st.cache_data(ttl=LIVE_QUOTE_TTL, show_spinner=False)
def fetch_live_price(ticker: str) -> float | None:
    if groww_data.is_groww_configured():
        ltp = groww_data.fetch_ltp(ticker)
        if ltp is not None:
            return ltp

    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="2d", interval="1d")
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception:
        return None


@st.cache_data(ttl=LIVE_QUOTE_TTL, show_spinner=False)
def fetch_live_volume(ticker: str) -> float | None:
    if groww_data.is_groww_configured():
        quote = groww_data.fetch_quote(ticker)
        if quote and quote.volume is not None:
            return quote.volume

    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="2d", interval="1d")
        if hist.empty:
            return None
        return float(hist["Volume"].iloc[-1])
    except Exception:
        return None


def get_data_source_label() -> str:
    """Human-readable label for which live-data backend is currently active,
    for UI transparency (e.g. next to the market status pill)."""
    if groww_data.is_groww_configured():
        return "📡 Live via Groww"
    return "🕒 Yahoo Finance (~15 min delayed)"


def format_inr(value: float | None, prefix: str = "\u20b9") -> str:
    if value is None:
        return "N/A"
    if abs(value) >= 1e7:
        return f"{prefix}{value / 1e7:,.2f} Cr"
    if abs(value) >= 1e5:
        return f"{prefix}{value / 1e5:,.2f} L"
    return f"{prefix}{value:,.2f}"


def format_volume(value: float | None) -> str:
    if value is None:
        return "N/A"
    if value >= 1e7:
        return f"{value / 1e7:,.2f} Cr"
    if value >= 1e5:
        return f"{value / 1e5:,.2f} L"
    return f"{value:,.0f}"


def format_market_cap(value: float | None) -> str:
    if value is None:
        return "N/A"
    # yfinance market cap is usually in absolute currency units.
    crore = value / 1e7
    if crore >= 1e5:
        return f"\u20b9{crore / 1e5:,.2f} Lakh Cr"
    return f"\u20b9{crore:,.0f} Cr"
