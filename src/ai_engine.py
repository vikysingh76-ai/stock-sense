"""Claude-powered stock analysis.

Requires an Anthropic API key, supplied via `st.secrets["ANTHROPIC_API_KEY"]`
or the `ANTHROPIC_API_KEY` environment variable. If no key is configured (or
a call fails for any reason -- rate limit, network, bad model name, etc.)
every function here falls back to a clearly-labelled heuristic "demo" result
so the rest of the app keeps working.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import streamlit as st

try:
    from dotenv import load_dotenv

    # Makes a local `.env` file (ANTHROPIC_API_KEY=...) work too, not just
    # `.streamlit/secrets.toml` or a real shell-exported env var. Safe no-op
    # if no .env file exists, and never overrides an already-set env var.
    load_dotenv(override=False)
except ImportError:
    pass

DEFAULT_MODEL = "claude-sonnet-5"

ANALYSIS_SYSTEM_PROMPT = """You are StockSense AI, an equity-research assistant that analyses \
Indian (NSE/BSE) listed stocks for a demo investment-intelligence product.

You will be given recent price/volume history and fundamental snapshot data for one stock. \
Using ONLY the data provided (plus your general knowledge of the company/sector), produce a \
structured trading view.

Respond with ONLY a single valid JSON object (no markdown fences, no commentary) matching \
exactly this schema:

{
  "signal": "STRONG BUY" | "BUY" | "HOLD" | "SELL" | "STRONG SELL",
  "target_price": <number, INR>,
  "stop_loss": <number, INR>,
  "buy_reasons": [<string>, <string>, <string>],
  "risks": [<string>, <string>],
  "timeframe_signals": {
    "daily": "BUY" | "HOLD" | "SELL",
    "weekly": "BUY" | "HOLD" | "SELL",
    "monthly": "BUY" | "HOLD" | "SELL",
    "yearly": "BUY" | "HOLD" | "SELL"
  }
}

Rules:
- buy_reasons must contain exactly 3 short, specific bullet points (max ~15 words each).
- risks must contain exactly 2 short, specific bullet points (max ~15 words each).
- target_price and stop_loss must be plausible numeric INR price levels near the current market price.
- This is clearly a demo tool. Do not include disclaimers inside the JSON fields themselves; \
the app will render its own disclaimer.
- Never respond with anything other than the JSON object.
"""

WATCHLIST_SYSTEM_PROMPT = """You are StockSense AI. Given a short snapshot of one Indian stock's \
recent price action, respond with ONLY one word: BUY, HOLD, or SELL. No punctuation, no \
explanation, no markdown."""


def get_api_key() -> str | None:
    try:
        if "ANTHROPIC_API_KEY" in st.secrets:
            key = st.secrets["ANTHROPIC_API_KEY"]
            if key:
                return str(key).strip()
    except Exception:
        pass
    key = os.environ.get("ANTHROPIC_API_KEY")
    return key.strip() if key else None


def get_api_key_debug_info() -> dict:
    """Non-secret diagnostics for the "no key detected" UI message.

    Never returns the key itself -- only where it looked and whether it
    found *something* in each location, plus a couple of common-mistake
    checks (wrong secret name, empty/placeholder value, etc.).
    """
    info = {
        "found_in_secrets": False,
        "found_in_env": False,
        "secrets_file_exists": False,
        "looks_like_placeholder": False,
        "secrets_error": None,
    }

    secrets_path = Path(".streamlit/secrets.toml")
    info["secrets_file_exists"] = secrets_path.exists()

    try:
        info["found_in_secrets"] = bool(st.secrets.get("ANTHROPIC_API_KEY"))
    except Exception as exc:
        info["secrets_error"] = str(exc)

    env_val = os.environ.get("ANTHROPIC_API_KEY")
    info["found_in_env"] = bool(env_val)

    candidate = None
    try:
        candidate = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        pass
    candidate = candidate or env_val
    if candidate:
        stripped = str(candidate).strip()
        info["looks_like_placeholder"] = (
            stripped in {"", "sk-ant-...", "sk-ant-your-real-key-here", "your-key-here"}
            or not stripped.startswith("sk-ant-")
        )

    return info


def get_model_name() -> str:
    try:
        if "CLAUDE_MODEL" in st.secrets and st.secrets["CLAUDE_MODEL"]:
            return str(st.secrets["CLAUDE_MODEL"])
    except Exception:
        pass
    return os.environ.get("CLAUDE_MODEL", DEFAULT_MODEL)


def is_ai_configured() -> bool:
    return bool(get_api_key())


@dataclass
class StockRecommendation:
    signal: str
    target_price: float | None
    stop_loss: float | None
    buy_reasons: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    timeframe_signals: dict[str, str] = field(default_factory=dict)
    is_fallback: bool = False
    error: str | None = None


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    return json.loads(text)


def _heuristic_recommendation(ticker: str, cmp: float | None, week52_high, week52_low, error: str | None = None) -> StockRecommendation:
    """Deterministic, non-AI fallback so the UI still functions without a live API key."""
    if cmp and week52_high and week52_low and week52_high != week52_low:
        position = (cmp - week52_low) / (week52_high - week52_low)
    else:
        position = 0.5

    if position < 0.35:
        signal = "BUY"
    elif position > 0.85:
        signal = "SELL"
    else:
        signal = "HOLD"

    base = cmp or 100.0
    return StockRecommendation(
        signal=signal,
        target_price=round(base * 1.10, 2),
        stop_loss=round(base * 0.94, 2),
        buy_reasons=[
            "Demo heuristic view based on 52-week price positioning.",
            "Configure ANTHROPIC_API_KEY to enable real AI-generated analysis.",
            f"{ticker} data shown is illustrative for this offline demo.",
        ],
        risks=[
            "No live AI model was queried for this result.",
            "Market conditions can change rapidly; verify independently.",
        ],
        timeframe_signals={"daily": "HOLD", "weekly": "HOLD", "monthly": signal, "yearly": signal},
        is_fallback=True,
        error=error,
    )


def get_stock_recommendation(
    ticker: str,
    company_name: str,
    cmp: float | None,
    week52_high: float | None,
    week52_low: float | None,
    market_cap: float | None,
    pe_ratio: float | None,
    recent_history_summary: str,
) -> StockRecommendation:
    api_key = get_api_key()
    if not api_key:
        return _heuristic_recommendation(
            ticker, cmp, week52_high, week52_low,
            error="No ANTHROPIC_API_KEY configured.",
        )

    user_prompt = f"""Stock: {company_name} ({ticker})
Current Market Price (CMP): INR {cmp}
52-Week High: INR {week52_high}
52-Week Low: INR {week52_low}
Market Cap: {market_cap}
Trailing P/E: {pe_ratio}

Recent price/volume behaviour (most recent last):
{recent_history_summary}

Provide your structured recommendation as specified in the system prompt."""

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=get_model_name(),
            max_tokens=1024,
            system=ANALYSIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw_text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        data = _extract_json(raw_text)
        return StockRecommendation(
            signal=str(data.get("signal", "HOLD")).upper(),
            target_price=data.get("target_price"),
            stop_loss=data.get("stop_loss"),
            buy_reasons=list(data.get("buy_reasons", []))[:3],
            risks=list(data.get("risks", []))[:2],
            timeframe_signals={
                k: str(v).upper() for k, v in dict(data.get("timeframe_signals", {})).items()
            },
            is_fallback=False,
        )
    except Exception as exc:  # noqa: BLE001 - surface any failure as a graceful fallback
        return _heuristic_recommendation(ticker, cmp, week52_high, week52_low, error=str(exc))


@st.cache_data(ttl=3600, show_spinner=False)
def get_quick_signal(ticker: str, price_change_summary: str) -> str:
    """Lightweight BUY/HOLD/SELL call used for the watchlist. Cached for an hour per ticker."""
    api_key = get_api_key()
    if not api_key:
        return "HOLD"

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=get_model_name(),
            max_tokens=8,
            system=WATCHLIST_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"{ticker}: {price_change_summary}"}],
        )
        raw_text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        ).strip().upper()
        for candidate in ("STRONG BUY", "BUY", "HOLD", "SELL"):
            if candidate in raw_text:
                return candidate
        return "HOLD"
    except Exception:
        return "HOLD"
