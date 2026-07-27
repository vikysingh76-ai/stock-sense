"""Shared SQLite data layer.

This intentionally points at the *same* database used by the
`mcp_server/india_stock_mcp.py` MCP server (`~/StockSenseAI/stocksense.db`).
That way, watchlist edits, saved recommendations, and scored predictions
made through Claude Desktop (via the MCP tools) are immediately visible in
this Streamlit dashboard, and vice versa.

All functions are defensive: if the database or table doesn't exist yet
(e.g. the MCP server has never been run), they return empty results rather
than raising, so the Streamlit app degrades gracefully to its bundled demo
data.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path.home() / "StockSenseAI"
DB_PATH = DATA_DIR / "stocksense.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlist (
    ticker TEXT PRIMARY KEY,
    name TEXT,
    added_date TEXT,
    notes TEXT
);
CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    ticker TEXT,
    signal TEXT,
    cmp REAL,
    target REAL,
    stop_loss REAL,
    horizon TEXT,
    conviction TEXT,
    reasoning TEXT,
    key_risks TEXT
);
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    ticker TEXT,
    predicted_direction TEXT,
    predicted_low REAL,
    predicted_high REAL,
    confidence TEXT,
    actual_close REAL,
    actual_direction TEXT,
    score INTEGER,
    notes TEXT
);
"""


def ensure_schema() -> bool:
    """Create the shared tables if missing. Returns False if the DB is unreachable."""
    try:
        DATA_DIR.mkdir(exist_ok=True)
        with _connect() as conn:
            conn.executescript(_SCHEMA)
        return True
    except Exception:
        return False


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def get_watchlist() -> list[dict]:
    """Returns [] if the DB/table doesn't exist or is empty (caller should fall back to demo data)."""
    if not ensure_schema():
        return []
    try:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT ticker, name, added_date, notes FROM watchlist ORDER BY name"
            ).fetchall()
        return [
            {"ticker": r[0], "name": r[1], "added_date": r[2], "notes": r[3]} for r in rows
        ]
    except Exception:
        return []


def add_to_watchlist(ticker: str, name: str, notes: str = "") -> None:
    """Adds (or updates) a ticker in the shared watchlist."""
    if not ensure_schema():
        return
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO watchlist (ticker, name, added_date, notes) VALUES (?, ?, ?, ?)",
            (ticker.strip().upper(), name, datetime.now().strftime("%Y-%m-%d"), notes),
        )


def remove_from_watchlist(ticker: str) -> None:
    """Removes a ticker from the shared watchlist, if present."""
    if not ensure_schema():
        return
    with _connect() as conn:
        conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker.strip().upper(),))


def save_recommendation(
    ticker: str,
    signal: str,
    cmp: float,
    target: float,
    stop_loss: float,
    reasoning: str,
    horizon: str = "MEDIUM",
    conviction: str = "MEDIUM",
    key_risks: str = "",
) -> bool:
    """Persists a buy/sell recommendation. Returns False if the DB is unreachable."""
    if not ensure_schema():
        return False
    try:
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO recommendations
                (date, ticker, signal, cmp, target, stop_loss, horizon, conviction, reasoning, key_risks)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now().strftime("%Y-%m-%d"),
                    ticker,
                    signal,
                    cmp,
                    target,
                    stop_loss,
                    horizon,
                    conviction,
                    reasoning,
                    key_risks,
                ),
            )
        return True
    except Exception:
        return False


_RECOMMENDATION_COLUMNS = (
    "date, ticker, signal, cmp, target, stop_loss, horizon, conviction, reasoning, key_risks"
)


def get_recommendation_history(ticker: str | None = None, days: int = 90) -> list[dict]:
    """Past recommendations for one ticker, or the most recent across all tickers."""
    if not ensure_schema():
        return []
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        with _connect() as conn:
            if ticker:
                rows = conn.execute(
                    f"SELECT {_RECOMMENDATION_COLUMNS} FROM recommendations "
                    "WHERE ticker = ? AND date >= ? ORDER BY date DESC",
                    (ticker, cutoff),
                ).fetchall()
            else:
                rows = conn.execute(
                    f"SELECT {_RECOMMENDATION_COLUMNS} FROM recommendations "
                    "WHERE date >= ? ORDER BY date DESC LIMIT 20",
                    (cutoff,),
                ).fetchall()
        cols = [
            "date", "ticker", "signal", "cmp", "target", "stop_loss",
            "horizon", "conviction", "reasoning", "key_risks",
        ]
        return [dict(zip(cols, r)) for r in rows]
    except Exception:
        return []


def save_prediction(
    ticker: str,
    predicted_direction: str,
    predicted_low: float | None,
    predicted_high: float | None,
    confidence: str = "MEDIUM",
    notes: str = "",
) -> bool:
    """Upsert today's (unscored) prediction for a ticker.

    Mirrors the MCP server's `save_daily_prediction` tool so entries logged
    from the dashboard's "Daily Run" button and from Claude Desktop share
    the same table and are both visible via `get_scored_predictions` once
    scored.
    """
    if not ensure_schema():
        return False
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        with _connect() as conn:
            conn.execute(
                "DELETE FROM predictions WHERE date = ? AND ticker = ? AND actual_close IS NULL",
                (today, ticker),
            )
            conn.execute(
                """
                INSERT INTO predictions
                (date, ticker, predicted_direction, predicted_low, predicted_high, confidence, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    today, ticker, predicted_direction, predicted_low,
                    predicted_high, confidence, notes,
                ),
            )
        return True
    except Exception:
        return False


def get_scored_predictions(limit: int = 30) -> list[dict]:
    """Predictions that have been scored against actuals, most recent first."""
    if not ensure_schema():
        return []
    try:
        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT date, ticker, predicted_direction, actual_direction, score,
                       predicted_low, predicted_high, actual_close
                FROM predictions
                WHERE actual_close IS NOT NULL
                ORDER BY date DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        cols = [
            "date", "ticker", "predicted_direction", "actual_direction", "score",
            "predicted_low", "predicted_high", "actual_close",
        ]
        return [dict(zip(cols, r)) for r in rows]
    except Exception:
        return []


def get_prediction_accuracy_pct(rows: list[dict] | None = None) -> float | None:
    """Percentage of `rows` (or all scored predictions) whose direction was correct."""
    rows = rows if rows is not None else get_scored_predictions()
    if not rows:
        return None
    correct = sum(1 for r in rows if r["predicted_direction"] == r["actual_direction"])
    return round(correct / len(rows) * 100, 1)
