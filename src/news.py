"""Lightweight news headline fetching (Google News RSS) used to ground the
Claude stock recommendation in real, current events -- financial results,
government/policy decisions, and geopolitical developments -- rather than
relying solely on the model's training-data knowledge.

Mirrors the approach used by `mcp_server/india_stock_mcp.py`'s
`get_stock_news` tool, kept independent here so each stays self-contained.
"""

from __future__ import annotations

import streamlit as st

try:
    import feedparser
except ImportError:
    feedparser = None


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_news_headlines(query: str, max_results: int = 5) -> list[dict]:
    """Returns [{'title':..., 'published':...}], or [] if unavailable."""
    if feedparser is None or not query:
        return []
    try:
        query_param = query.replace(" ", "+")
        url = f"https://news.google.com/rss/search?q={query_param}&hl=en-IN&gl=IN&ceid=IN:en"
        feed = feedparser.parse(url)
        return [
            {"title": entry.get("title", ""), "published": entry.get("published", "")[:16]}
            for entry in feed.entries[:max_results]
            if entry.get("title")
        ]
    except Exception:
        return []


def summarize_headlines(headlines: list[dict]) -> str:
    """Renders headlines as a simple bulleted list for embedding in a prompt."""
    if not headlines:
        return "No recent headlines available."
    return "\n".join(f"- {h['title']}" for h in headlines)
