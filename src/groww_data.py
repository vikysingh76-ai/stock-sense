"""Optional live NSE/BSE market data via the user's own Groww account.

Groww offers an official Trading API (https://groww.in/trade-api) that
provides genuinely live quotes, LTP, OHLC, and historical candles for NSE
and BSE instruments -- unlike `yfinance` (Yahoo Finance), which is free but
typically ~15 minutes delayed and unofficial/unsupported. Using it requires:

- A Groww account
- An active Groww Trading API subscription (paid; see https://groww.in/trade-api)
- A generated TOTP-flow API key + secret from the Groww Cloud API Keys page
  (the TOTP flow is used here rather than the API-key/secret flow because it
  does not require daily manual re-approval, which matters for an
  unattended server app)

Configure via `GROWW_API_KEY` (the TOTP token from the Groww Cloud API Keys
page) and `GROWW_TOTP_SECRET` (the TOTP secret shown alongside it), through
`.streamlit/secrets.toml`, environment variables, or a local `.env` file --
same mechanism as `ANTHROPIC_API_KEY` elsewhere in this app.

Everything here is defensive: if `growwapi`/`pyotp` aren't installed, no
credentials are configured, or any call fails for any reason (auth,
network, rate limit, unrecognized symbol, etc.), every function returns
`None` so callers in `market_data.py` fall back to `yfinance`. Groww is
purely an optional upgrade for genuinely live data, never a hard dependency.

NOTE: this integration was built directly against Groww's published API
docs (https://groww.in/trade-api/docs) but has not been exercised against a
real Groww account/subscription during development here. Please verify it
behaves as expected once you add real credentials, and report back if the
symbol mapping or response parsing needs adjusting for your account.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

try:
    from growwapi import GrowwAPI
    import pyotp
except ImportError:
    GrowwAPI = None
    pyotp = None

# Access tokens aren't documented as having a fixed TTL; refreshing every
# few hours is cheap (the TOTP flow has no daily-approval friction) and
# keeps us safely ahead of any expiry.
_ACCESS_TOKEN_TTL_SECONDS = 6 * 60 * 60

# Yahoo-style index tickers used elsewhere in this app -> Groww (trading_symbol, exchange).
# NIFTY on NSE/CASH is confirmed directly in Groww's docs examples; SENSEX
# on BSE/CASH follows the same convention but is not explicitly confirmed
# in the docs -- if it's wrong, fetch_quote/fetch_historical simply fail
# and the caller falls back to yfinance, so it's safe either way.
_INDEX_SYMBOL_MAP = {
    "^NSEI": ("NIFTY", "NSE"),
    "^BSESN": ("SENSEX", "BSE"),
}

_PERIOD_TO_DAYS = {
    "1d": 2, "2d": 3, "5d": 7, "1mo": 32, "3mo": 93,
    "6mo": 186, "1y": 366, "2y": 732, "5y": 1830,
}


def _get_credential(key: str) -> str | None:
    try:
        if key in st.secrets and st.secrets[key]:
            return str(st.secrets[key]).strip()
    except Exception:
        pass
    val = os.environ.get(key)
    return val.strip() if val else None


def is_groww_configured() -> bool:
    """True if the growwapi/pyotp packages and both required credentials are available."""
    return bool(
        GrowwAPI is not None
        and pyotp is not None
        and _get_credential("GROWW_API_KEY")
        and _get_credential("GROWW_TOTP_SECRET")
    )


def _authenticate() -> tuple[str | None, str | None]:
    """Returns (access_token, error_message)."""
    if not is_groww_configured():
        return None, "Not configured (missing package or credentials)."
    try:
        api_key = _get_credential("GROWW_API_KEY")
        totp_secret = _get_credential("GROWW_TOTP_SECRET")
        totp_code = pyotp.TOTP(totp_secret).now()
        token = GrowwAPI.get_access_token(api_key=api_key, totp=totp_code)
        if not token:
            return None, "Authentication returned no token."
        return token, None
    except Exception as exc:
        return None, str(exc)


@st.cache_resource(ttl=_ACCESS_TOKEN_TTL_SECONDS, show_spinner=False)
def _get_access_token() -> str | None:
    token, _ = _authenticate()
    return token


def get_client():
    """Returns an authenticated GrowwAPI client, or None if unavailable."""
    token = _get_access_token()
    if not token:
        return None
    try:
        return GrowwAPI(token)
    except Exception:
        return None


def clear_session():
    """Forces a fresh access token on next use (e.g. after an auth error)."""
    _get_access_token.clear()


def get_diagnostics() -> dict:
    """Non-secret status info for a UI diagnostics panel."""
    info = {
        "package_installed": GrowwAPI is not None and pyotp is not None,
        "credentials_found": bool(
            _get_credential("GROWW_API_KEY") and _get_credential("GROWW_TOTP_SECRET")
        ),
        "authenticated": False,
        "error": None,
    }
    if not info["package_installed"] or not info["credentials_found"]:
        return info
    token, error = _authenticate()
    info["authenticated"] = bool(token)
    info["error"] = error
    return info


def _map_symbol(ticker: str) -> tuple[str, str] | None:
    """Yahoo-style ticker (e.g. 'RELIANCE.NS', '^NSEI') -> (trading_symbol, exchange)."""
    if ticker in _INDEX_SYMBOL_MAP:
        return _INDEX_SYMBOL_MAP[ticker]
    if ticker.endswith(".NS"):
        return ticker[:-3], "NSE"
    if ticker.endswith(".BO"):
        return ticker[:-3], "BSE"
    return None


@dataclass
class GrowwQuote:
    """Normalized quote data returned by Groww's get_quote endpoint."""

    last_price: float | None = None
    prev_close: float | None = None
    change: float | None = None
    change_pct: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    volume: float | None = None
    week_52_high: float | None = None
    week_52_low: float | None = None
    market_cap: float | None = None


def fetch_quote(ticker: str) -> GrowwQuote | None:
    """Live quote for `ticker` via Groww, or None if unavailable/unconfigured/failed."""
    client = get_client()
    mapped = _map_symbol(ticker)
    if not client or not mapped:
        return None
    trading_symbol, exchange = mapped
    try:
        resp = client.get_quote(
            trading_symbol=trading_symbol,
            exchange=getattr(client, f"EXCHANGE_{exchange}"),
            segment=client.SEGMENT_CASH,
        )
        ohlc = resp.get("ohlc") or {}
        return GrowwQuote(
            last_price=resp.get("last_price"),
            prev_close=ohlc.get("close"),
            change=resp.get("day_change"),
            change_pct=resp.get("day_change_perc"),
            day_high=ohlc.get("high"),
            day_low=ohlc.get("low"),
            volume=resp.get("volume"),
            week_52_high=resp.get("week_52_high"),
            week_52_low=resp.get("week_52_low"),
            market_cap=resp.get("market_cap"),
        )
    except Exception:
        return None


def fetch_ltp(ticker: str) -> float | None:
    """Last traded price for `ticker` via Groww, or None if unavailable."""
    client = get_client()
    mapped = _map_symbol(ticker)
    if not client or not mapped:
        return None
    trading_symbol, exchange = mapped
    try:
        key = f"{exchange}_{trading_symbol}"
        resp = client.get_ltp(exchange_trading_symbols=(key,), segment=client.SEGMENT_CASH)
        return resp.get(key)
    except Exception:
        return None


def fetch_historical(ticker: str, period: str = "1y") -> pd.DataFrame | None:
    """Daily OHLCV candles, shaped like yfinance's history() output
    (DatetimeIndex named appropriately, Open/High/Low/Close/Volume columns)
    so it's a drop-in replacement for the yfinance-backed path."""
    client = get_client()
    mapped = _map_symbol(ticker)
    if not client or not mapped:
        return None
    trading_symbol, exchange = mapped
    days = _PERIOD_TO_DAYS.get(period, 366)
    end = datetime.now()
    start = end - timedelta(days=days)
    try:
        resp = client.get_historical_candle_data(
            trading_symbol=trading_symbol,
            exchange=getattr(client, f"EXCHANGE_{exchange}"),
            segment=client.SEGMENT_CASH,
            start_time=start.strftime("%Y-%m-%d %H:%M:%S"),
            end_time=end.strftime("%Y-%m-%d %H:%M:%S"),
            interval_in_minutes=1440,  # daily candles
        )
        candles = resp.get("candles") or []
        if not candles:
            return None
        df = pd.DataFrame(candles, columns=["Timestamp", "Open", "High", "Low", "Close", "Volume"])
        df.index = pd.to_datetime(df["Timestamp"], unit="s")
        return df.drop(columns=["Timestamp"])
    except Exception:
        return None
