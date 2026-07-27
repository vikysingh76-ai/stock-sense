"""
India Stock Intelligence — MCP Server
======================================
MCP server for Claude Desktop providing live NSE/BSE stock data,
fundamentals, news, watchlist management, and prediction tracking.

Install dependencies:
    pip install -r mcp_server/requirements.txt
    (or: pip install mcp yfinance pandas requests feedparser)

Run test:
    python india_stock_mcp.py

Note: this process speaks the MCP stdio protocol (JSON-RPC over stdin/stdout).
Running it directly from a terminal will appear to hang -- it is waiting for
an MCP client (e.g. Claude Desktop, or `mcp_server/test_client.py` in this
repo) to connect over stdio. See `mcp_server/README.md` for setup.

The SQLite database created at ~/StockSenseAI/stocksense.db (watchlist,
recommendations, predictions) is intentionally shared with the StockSense AI
Streamlit app (`src/db.py`), so watchlist edits and saved recommendations
made via Claude Desktop show up in the web dashboard, and vice versa.
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import sys

# ── Try importing dependencies gracefully ─────────────────────────────────────
try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance not installed. Run: pip install yfinance", file=sys.stderr)
    sys.exit(1)

try:
    import feedparser
except ImportError:
    feedparser = None  # News will be unavailable but app still works

try:
    # Reserved for future direct HTTP data sources; not yet used elsewhere.
    import requests  # noqa: F401  pylint: disable=unused-import
except ImportError:
    requests = None

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
)

# ── Data directory (stores watchlist, predictions, recommendations) ────────────
DATA_DIR = Path.home() / "StockSenseAI"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "stocksense.db"

# Many of this file's report-formatting f-strings are long by design (fixed-width
# columns/box-drawing characters for aligned CLI-style text output); wrapping them
# would break that alignment without improving readability.
# pylint: disable=line-too-long


# ── Database setup ─────────────────────────────────────────────────────────────
def init_db():
    """Creates the shared watchlist/recommendations/predictions tables if missing."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            ticker TEXT PRIMARY KEY,
            name TEXT,
            added_date TEXT,
            notes TEXT
        )
    """)
    c.execute("""
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
        )
    """)
    c.execute("""
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
        )
    """)
    # Seed default Indian watchlist if empty
    c.execute("SELECT COUNT(*) FROM watchlist")
    if c.fetchone()[0] == 0:
        default_stocks = [
            ("RELIANCE.NS", "Reliance Industries"),
            ("TCS.NS", "Tata Consultancy Services"),
            ("HDFCBANK.NS", "HDFC Bank"),
            ("INFY.NS", "Infosys"),
            ("BAJFINANCE.NS", "Bajaj Finance"),
            # Tata Motors demerged; the commercial-vehicles business kept the
            # legacy TATAMOTORS.NS symbol retired, so we track the passenger
            # vehicles entity that now trades under this ticker.
            ("TMPV.NS", "Tata Motors Passenger Vehicles"),
            # Zomato Ltd was renamed to Eternal Ltd on the NSE; ZOMATO.NS no
            # longer resolves.
            ("ETERNAL.NS", "Eternal (formerly Zomato)"),
            ("WIPRO.NS", "Wipro"),
            ("ICICIBANK.NS", "ICICI Bank"),
            ("ADANIPORTS.NS", "Adani Ports"),
        ]
        for ticker, name in default_stocks:
            c.execute(
                "INSERT OR IGNORE INTO watchlist (ticker, name, added_date) VALUES (?, ?, ?)",
                (ticker, name, datetime.now().strftime("%Y-%m-%d"))
            )
    conn.commit()
    conn.close()

init_db()

# ── Helper: format large numbers ──────────────────────────────────────────────
def fmt_crore(val):
    """Formats a rupee amount in Lakh/Thousand Crore units."""
    if val is None:
        return "N/A"
    crore = val / 1e7
    if crore >= 1e5:
        return f"₹{crore/1e5:.2f} Lakh Cr"
    if crore >= 1e3:
        return f"₹{crore/1e3:.2f} K Cr"
    return f"₹{crore:.2f} Cr"

def safe_round(val, digits=2):
    """Rounds val to digits decimal places, or returns 'N/A' if not numeric."""
    try:
        return round(float(val), digits)
    except (TypeError, ValueError):
        return "N/A"

# ── MCP Server ────────────────────────────────────────────────────────────────
server = Server("india-stock-intelligence")

# ─────────────────────────────────────────────────────────────────────────────
# TOOL 1: Get Market Indices
# ─────────────────────────────────────────────────────────────────────────────
@server.list_tools()
async def list_tools():
    """Declares all tools this MCP server exposes to a connected client."""
    return [
        Tool(
            name="get_market_indices",
            description="Get live values for major Indian market indices: Nifty 50, Sensex, Bank Nifty, Nifty Midcap 150, Nifty Smallcap 250. Use this at the start of every analysis session.",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="get_stock_quote",
            description="Get the live quote for a single NSE/BSE stock. Returns current price, day change, day high/low, 52-week high/low, volume. Always use .NS suffix for NSE stocks (e.g. RELIANCE.NS, TCS.NS, HDFCBANK.NS).",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "NSE ticker with .NS suffix, e.g. RELIANCE.NS"}
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_stock_fundamentals",
            description="Get fundamental data for a stock: P/E ratio, P/B ratio, Market Cap, EPS, Revenue, Net Profit, ROE, Debt-to-Equity, Dividend Yield, Sector, Industry. Essential for fundamental analysis pillar.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "NSE ticker, e.g. RELIANCE.NS"}
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_historical_performance",
            description="Get historical price performance for a stock over multiple periods: 1 week, 1 month, 3 months, 6 months, 1 year, 3 years. Also returns simple moving averages (20d, 50d, 200d) for technical analysis.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "NSE ticker, e.g. TCS.NS"},
                    "period": {"type": "string", "description": "Data period: 1mo, 3mo, 6mo, 1y, 2y, 5y. Default: 1y", "default": "1y"}
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_multiple_quotes",
            description="Get live quotes for all stocks in the watchlist or a custom list. Use to get a market snapshot of multiple stocks at once.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of NSE tickers, e.g. ['RELIANCE.NS', 'TCS.NS']. Leave empty to use saved watchlist."
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_stock_news",
            description="Fetch recent news headlines for a stock or Indian market in general. Searches Google News RSS for the latest articles.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query, e.g. 'Reliance Industries results' or 'Nifty 50 outlook'"},
                    "max_results": {"type": "integer", "description": "Max number of news items to return. Default: 8", "default": 8}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_watchlist",
            description="Get the current saved watchlist of stocks with their live quotes.",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="update_watchlist",
            description="Add or remove a stock from the watchlist.",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["add", "remove"], "description": "add or remove"},
                    "ticker": {"type": "string", "description": "NSE ticker, e.g. BAJFINANCE.NS"},
                    "name": {"type": "string", "description": "Company name (required when adding)"},
                    "notes": {"type": "string", "description": "Optional notes about why added"}
                },
                "required": ["action", "ticker"]
            }
        ),
        Tool(
            name="save_recommendation",
            description="Save a buy/sell recommendation to the local database for record keeping and future reference.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "signal": {"type": "string", "description": "STRONG BUY / BUY / ACCUMULATE / HOLD / REDUCE / SELL"},
                    "cmp": {"type": "number", "description": "Current Market Price at time of recommendation"},
                    "target": {"type": "number", "description": "12-month price target"},
                    "stop_loss": {"type": "number", "description": "Stop loss price"},
                    "horizon": {"type": "string", "description": "Time horizon: SHORT/MEDIUM/LONG"},
                    "conviction": {"type": "string", "description": "HIGH/MEDIUM/LOW"},
                    "reasoning": {"type": "string", "description": "Key buy thesis"},
                    "key_risks": {"type": "string", "description": "Key risks to the thesis"}
                },
                "required": ["ticker", "signal", "cmp", "target", "stop_loss", "reasoning"]
            }
        ),
        Tool(
            name="save_daily_prediction",
            description="Save today's pre-market prediction for a stock (direction, price range, confidence). Call every morning before market opens.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "predicted_direction": {"type": "string", "enum": ["UP", "DOWN", "SIDEWAYS"]},
                    "predicted_low": {"type": "number", "description": "Predicted day low"},
                    "predicted_high": {"type": "number", "description": "Predicted day high"},
                    "confidence": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
                    "notes": {"type": "string", "description": "Key driver of prediction"}
                },
                "required": ["ticker", "predicted_direction", "predicted_low", "predicted_high", "confidence"]
            }
        ),
        Tool(
            name="score_yesterdays_prediction",
            description="After market close, score yesterday's prediction against the actual result. Updates prediction accuracy tracker.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "actual_close": {"type": "number", "description": "Actual closing price"},
                    "actual_direction": {"type": "string", "enum": ["UP", "DOWN", "SIDEWAYS"]},
                    "score": {"type": "integer", "description": "Score 0-10 (10=perfect, 7=partially correct, 0=wrong)"},
                    "notes": {"type": "string", "description": "What was right or wrong about the prediction"}
                },
                "required": ["ticker", "actual_close", "actual_direction", "score"]
            }
        ),
        Tool(
            name="get_prediction_accuracy",
            description="Get the prediction accuracy report: overall accuracy %, last 30 days predictions, score trend.",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="get_recommendation_history",
            description="Get past recommendations for a specific stock or all stocks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "NSE ticker, or leave empty for all stocks"},
                    "days": {"type": "integer", "description": "Look back N days. Default: 90", "default": 90}
                },
                "required": []
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:  # pylint: disable=too-many-return-statements
    """Routes an incoming MCP tool call to its implementation by name."""
    try:
        if name == "get_market_indices":
            return await _get_market_indices()
        if name == "get_stock_quote":
            return await _get_stock_quote(arguments["ticker"])
        if name == "get_stock_fundamentals":
            return await _get_stock_fundamentals(arguments["ticker"])
        if name == "get_historical_performance":
            return await _get_historical_performance(
                arguments["ticker"],
                arguments.get("period", "1y")
            )
        if name == "get_multiple_quotes":
            return await _get_multiple_quotes(arguments.get("tickers", []))
        if name == "get_stock_news":
            return await _get_stock_news(arguments["query"], arguments.get("max_results", 8))
        if name == "get_watchlist":
            return await _get_watchlist()
        if name == "update_watchlist":
            return await _update_watchlist(
                arguments["action"],
                arguments["ticker"],
                arguments.get("name", ""),
                arguments.get("notes", "")
            )
        if name == "save_recommendation":
            return await _save_recommendation(arguments)
        if name == "save_daily_prediction":
            return await _save_daily_prediction(arguments)
        if name == "score_yesterdays_prediction":
            return await _score_prediction(arguments)
        if name == "get_prediction_accuracy":
            return await _get_prediction_accuracy()
        if name == "get_recommendation_history":
            return await _get_recommendation_history(
                arguments.get("ticker", ""),
                arguments.get("days", 90)
            )
        return CallToolResult(content=[TextContent(type="text", text=f"Unknown tool: {name}")])
    except Exception as e:
        return CallToolResult(content=[TextContent(type="text", text=f"Error in {name}: {str(e)}")])


# ── Tool implementations ───────────────────────────────────────────────────────

async def _get_market_indices():
    indices = {
        "Nifty 50":         "^NSEI",
        "Sensex (BSE)":     "^BSESN",
        "Bank Nifty":       "^NSEBANK",
        "Nifty Midcap 150": "NIFTY_MID_SELECT.NS",
        "Nifty IT":         "^CNXIT",
        "Nifty Pharma":     "^CNXPHARMA",
    }
    result = ["═" * 50, "🇮🇳  INDIAN MARKET INDICES", "═" * 50]
    now_ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
    result.append(f"As of: {now_ist.strftime('%d %b %Y  %H:%M IST')}")
    result.append("")

    for name, ticker in indices.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d")
            if len(hist) >= 1:
                current = hist["Close"].iloc[-1]
                prev = hist["Close"].iloc[-2] if len(hist) >= 2 else current
                change = current - prev
                pct = (change / prev) * 100
                arrow = "▲" if change >= 0 else "▼"
                result.append(f"  {name:<22} {current:>10,.2f}  {arrow} {abs(change):,.2f} ({abs(pct):.2f}%)")
        except Exception:
            result.append(f"  {name:<22}  Data unavailable")

    result.append("")
    result.append("Note: Data may be delayed 15 minutes.")
    return CallToolResult(content=[TextContent(type="text", text="\n".join(result))])


async def _get_stock_quote(ticker: str):
    t = yf.Ticker(ticker)
    info = t.info
    hist = t.history(period="2d")

    if hist.empty:
        return CallToolResult(content=[TextContent(type="text", text=f"No data found for {ticker}. Check the ticker symbol.")])

    current = hist["Close"].iloc[-1]
    prev_close = hist["Close"].iloc[-2] if len(hist) >= 2 else current
    day_high = hist["High"].iloc[-1]
    day_low = hist["Low"].iloc[-1]
    volume = hist["Volume"].iloc[-1]
    change = current - prev_close
    pct_change = (change / prev_close) * 100

    week_52_high = info.get("fiftyTwoWeekHigh", "N/A")
    week_52_low = info.get("fiftyTwoWeekLow", "N/A")
    avg_volume = info.get("averageVolume", "N/A")
    company_name = info.get("longName", ticker)

    result = [
        "═" * 50,
        f"📊  {company_name}  ({ticker})",
        "═" * 50,
        f"  CMP (Current Price):   ₹{current:,.2f}",
        f"  Change:                {'▲' if change >= 0 else '▼'} ₹{abs(change):.2f}  ({pct_change:+.2f}%)",
        f"  Day High:              ₹{day_high:,.2f}",
        f"  Day Low:               ₹{day_low:,.2f}",
        f"  Previous Close:        ₹{prev_close:,.2f}",
        f"  52-Week High:          ₹{week_52_high:,.2f}" if isinstance(week_52_high, float) else f"  52-Week High:          {week_52_high}",
        f"  52-Week Low:           ₹{week_52_low:,.2f}" if isinstance(week_52_low, float) else f"  52-Week Low:           {week_52_low}",
        f"  Today's Volume:        {int(volume):,}",
        f"  30D Avg Volume:        {int(avg_volume):,}" if isinstance(avg_volume, int) else f"  30D Avg Volume:        {avg_volume}",
    ]
    return CallToolResult(content=[TextContent(type="text", text="\n".join(result))])


async def _get_stock_fundamentals(ticker: str):
    t = yf.Ticker(ticker)
    info = t.info

    company = info.get("longName", ticker)
    sector = info.get("sector", "N/A")
    industry = info.get("industry", "N/A")
    market_cap = fmt_crore(info.get("marketCap"))
    pe = safe_round(info.get("trailingPE"))
    forward_pe = safe_round(info.get("forwardPE"))
    pb = safe_round(info.get("priceToBook"))
    eps = safe_round(info.get("trailingEps"))
    roe = safe_round(info.get("returnOnEquity", 0) * 100 if info.get("returnOnEquity") else None)
    debt_equity = safe_round(info.get("debtToEquity"))
    div_yield = safe_round(info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0)
    revenue = fmt_crore(info.get("totalRevenue"))
    profit_margin = safe_round(info.get("profitMargins", 0) * 100 if info.get("profitMargins") else None)
    beta = safe_round(info.get("beta"))
    book_value = safe_round(info.get("bookValue"))
    promoter_hold = info.get("heldPercentInsiders")
    inst_hold = info.get("heldPercentInstitutions")

    result = [
        "═" * 55,
        f"📈  FUNDAMENTALS — {company}",
        "═" * 55,
        f"  Sector:               {sector}",
        f"  Industry:             {industry}",
        "",
        "  ── VALUATION ──────────────────────────────",
        f"  Market Cap:           {market_cap}",
        f"  Trailing P/E:         {pe}x",
        f"  Forward P/E:          {forward_pe}x",
        f"  Price-to-Book (P/B):  {pb}x",
        f"  EPS (TTM):            ₹{eps}",
        f"  Book Value/Share:     ₹{book_value}",
        "",
        "  ── PROFITABILITY ───────────────────────────",
        f"  Annual Revenue:       {revenue}",
        f"  Profit Margin:        {profit_margin}%",
        f"  Return on Equity:     {roe}%",
        "",
        "  ── RISK & OWNERSHIP ────────────────────────",
        f"  Debt-to-Equity:       {debt_equity}",
        f"  Beta (Market Risk):   {beta}",
        f"  Dividend Yield:       {div_yield}%",
        f"  Promoter Holding:     {safe_round(promoter_hold * 100) if promoter_hold else 'N/A'}%",
        f"  Institutional Hold:   {safe_round(inst_hold * 100) if inst_hold else 'N/A'}%",
    ]
    return CallToolResult(content=[TextContent(type="text", text="\n".join(result))])


async def _get_historical_performance(ticker: str, period: str = "1y"):
    t = yf.Ticker(ticker)
    hist = t.history(period=period)

    if hist.empty:
        return CallToolResult(content=[TextContent(type="text", text=f"No historical data for {ticker}")])

    current = hist["Close"].iloc[-1]

    def pct_return(days):
        idx = max(0, len(hist) - days)
        past = hist["Close"].iloc[idx]
        return ((current - past) / past) * 100

    # Simple Moving Averages
    ma20  = hist["Close"].tail(20).mean()  if len(hist) >= 20  else None
    ma50  = hist["Close"].tail(50).mean()  if len(hist) >= 50  else None
    ma200 = hist["Close"].tail(200).mean() if len(hist) >= 200 else None

    # RSI (14-period)
    def calc_rsi(prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    rsi = calc_rsi(hist["Close"]).iloc[-1] if len(hist) >= 15 else None

    result = [
        "═" * 55,
        f"📉  HISTORICAL PERFORMANCE — {ticker}",
        "═" * 55,
        "",
        "  ── PRICE RETURNS ───────────────────────────",
        f"  1 Week Return:        {pct_return(5):+.2f}%",
        f"  1 Month Return:       {pct_return(21):+.2f}%",
        f"  3 Month Return:       {pct_return(63):+.2f}%",
        f"  6 Month Return:       {pct_return(126):+.2f}%",
        f"  1 Year Return:        {pct_return(252):+.2f}%",
        "",
        "  ── TECHNICAL INDICATORS ────────────────────",
        f"  Current Price:        ₹{current:,.2f}",
        f"  20-Day SMA:           ₹{ma20:,.2f}  ({'Price ABOVE — Bullish ✅' if current > ma20 else 'Price BELOW — Bearish ⚠️'})" if ma20 else "  20-Day SMA:           Insufficient data",
        f"  50-Day SMA:           ₹{ma50:,.2f}  ({'Price ABOVE — Bullish ✅' if current > ma50 else 'Price BELOW — Bearish ⚠️'})" if ma50 else "  50-Day SMA:           Insufficient data",
        f"  200-Day SMA:          ₹{ma200:,.2f}  ({'Price ABOVE — Long-term Bullish ✅' if current > ma200 else 'Price BELOW — Long-term Bearish ⚠️'})" if ma200 else "  200-Day SMA:          Insufficient data",
        f"  RSI (14-day):         {rsi:.1f}  ({'OVERBOUGHT ⚠️' if rsi > 70 else 'OVERSOLD — Potential Buy 🟢' if rsi < 30 else 'Neutral'})" if rsi else "  RSI:                  N/A",
        "",
        f"  Period high:          ₹{hist['High'].max():,.2f}",
        f"  Period low:           ₹{hist['Low'].min():,.2f}",
        f"  Average volume:       {int(hist['Volume'].mean()):,}",
    ]
    return CallToolResult(content=[TextContent(type="text", text="\n".join(result))])


async def _get_multiple_quotes(tickers: list):
    if not tickers:
        # Use watchlist
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT ticker, name FROM watchlist ORDER BY name")
        rows = c.fetchall()
        conn.close()
        tickers = [r[0] for r in rows]
        names = {r[0]: r[1] for r in rows}
    else:
        names = {}

    result = ["═" * 65, "📋  WATCHLIST MARKET SNAPSHOT", "═" * 65,
              f"{'STOCK':<25} {'CMP':>10} {'CHANGE':>10} {'%CHG':>8} {'52W H':>10} {'52W L':>10}",
              "─" * 65]

    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d")
            info = t.info
            if hist.empty:
                continue
            cur = hist["Close"].iloc[-1]
            prev = hist["Close"].iloc[-2] if len(hist) >= 2 else cur
            chg = cur - prev
            pct = (chg / prev) * 100
            h52 = info.get("fiftyTwoWeekHigh", 0)
            l52 = info.get("fiftyTwoWeekLow", 0)
            name = names.get(ticker, info.get("shortName", ticker))[:22]
            arrow = "▲" if chg >= 0 else "▼"
            result.append(
                f"  {name:<23} ₹{cur:>8,.2f} {arrow}{abs(chg):>8.2f} {pct:>+7.2f}% ₹{h52:>8,.2f} ₹{l52:>8,.2f}"
            )
        except Exception:
            result.append(f"  {ticker:<23} Data unavailable")

    now_ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
    result.append("─" * 65)
    result.append(f"  Updated: {now_ist.strftime('%d %b %Y %H:%M IST')}  |  Data may be delayed 15 min")
    return CallToolResult(content=[TextContent(type="text", text="\n".join(result))])


async def _get_stock_news(query: str, max_results: int = 8):
    if feedparser is None:
        return CallToolResult(content=[TextContent(type="text",
            text="feedparser not installed. Run: pip install feedparser\nAlternatively, search manually on Economic Times, MoneyControl, or Business Standard.")])

    url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}+India+stock&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(url)

    result = [f"📰  NEWS: {query.upper()}", "═" * 60]
    count = 0
    for entry in feed.entries[:max_results]:
        title = entry.get("title", "No title")
        pub = entry.get("published", "")[:16]
        link = entry.get("link", "")
        result.append(f"\n  [{count+1}] {title}")
        result.append(f"      {pub}")
        result.append(f"      {link}")
        count += 1

    if count == 0:
        result.append("  No recent news found. Try a different search term.")

    return CallToolResult(content=[TextContent(type="text", text="\n".join(result))])


async def _get_watchlist():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT ticker, name, added_date, notes FROM watchlist ORDER BY name")
    rows = c.fetchall()
    conn.close()

    if not rows:
        return CallToolResult(content=[TextContent(type="text", text="Watchlist is empty. Add stocks using update_watchlist.")])

    result = ["📋  YOUR WATCHLIST", "═" * 55]
    for ticker, name, _added, notes in rows:
        result.append(f"  • {name:<30} ({ticker})")
        if notes:
            result.append(f"    Note: {notes}")
    result.append(f"\n  Total: {len(rows)} stocks")
    return CallToolResult(content=[TextContent(type="text", text="\n".join(result))])


async def _update_watchlist(action: str, ticker: str, name: str = "", notes: str = ""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if action == "add":
        if not name:
            try:
                info = yf.Ticker(ticker).info
                name = info.get("longName", ticker)
            except Exception:
                name = ticker
        c.execute(
            "INSERT OR REPLACE INTO watchlist (ticker, name, added_date, notes) VALUES (?, ?, ?, ?)",
            (ticker, name, datetime.now().strftime("%Y-%m-%d"), notes)
        )
        msg = f"✅ Added {name} ({ticker}) to watchlist."
    else:
        c.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker,))
        msg = f"🗑️ Removed {ticker} from watchlist."
    conn.commit()
    conn.close()
    return CallToolResult(content=[TextContent(type="text", text=msg)])


async def _save_recommendation(args: dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO recommendations
        (date, ticker, signal, cmp, target, stop_loss, horizon, conviction, reasoning, key_risks)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d"),
        args["ticker"], args["signal"], args["cmp"],
        args["target"], args["stop_loss"],
        args.get("horizon", "MEDIUM"), args.get("conviction", "MEDIUM"),
        args["reasoning"], args.get("key_risks", "")
    ))
    conn.commit()
    conn.close()
    exp_return = ((args["target"] - args["cmp"]) / args["cmp"]) * 100
    return CallToolResult(content=[TextContent(type="text",
        text=f"✅ Recommendation saved!\n"
             f"   {args['ticker']} — {args['signal']}\n"
             f"   CMP: ₹{args['cmp']:,.2f}  →  Target: ₹{args['target']:,.2f}  (+{exp_return:.1f}%)\n"
             f"   Stop Loss: ₹{args['stop_loss']:,.2f}  |  Conviction: {args.get('conviction','MEDIUM')}"
    )])


async def _save_daily_prediction(args: dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("DELETE FROM predictions WHERE date = ? AND ticker = ? AND actual_close IS NULL",
              (today, args["ticker"]))
    c.execute("""
        INSERT INTO predictions
        (date, ticker, predicted_direction, predicted_low, predicted_high, confidence, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        today, args["ticker"], args["predicted_direction"],
        args["predicted_low"], args["predicted_high"],
        args["confidence"], args.get("notes", "")
    ))
    conn.commit()
    conn.close()
    return CallToolResult(content=[TextContent(type="text",
        text=f"✅ Prediction saved for {args['ticker']} on {today}\n"
             f"   Direction: {args['predicted_direction']}  |  Range: ₹{args['predicted_low']:,.2f} – ₹{args['predicted_high']:,.2f}\n"
             f"   Confidence: {args['confidence']}"
    )])


async def _score_prediction(args: dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    c.execute("""
        UPDATE predictions
        SET actual_close = ?, actual_direction = ?, score = ?, notes = COALESCE(notes, '') || ' | Post: ' || ?
        WHERE ticker = ? AND date = ? AND actual_close IS NULL
    """, (
        args["actual_close"], args["actual_direction"],
        args["score"], args.get("notes", ""),
        args["ticker"], yesterday
    ))
    conn.commit()
    conn.close()
    return CallToolResult(content=[TextContent(type="text",
        text=f"✅ Prediction scored for {args['ticker']} ({yesterday})\n"
             f"   Actual: {args['actual_direction']} @ ₹{args['actual_close']:,.2f}  |  Score: {args['score']}/10"
    )])


async def _get_prediction_accuracy():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT ticker, date, predicted_direction, actual_direction, score, predicted_low, predicted_high, actual_close
        FROM predictions WHERE actual_close IS NOT NULL
        ORDER BY date DESC LIMIT 30
    """)
    rows = c.fetchall()
    conn.close()

    if not rows:
        return CallToolResult(content=[TextContent(type="text",
            text="No scored predictions yet. Start by saving daily predictions and scoring them after market close.")])

    total = len(rows)
    correct = sum(1 for r in rows if r[2] == r[3])
    avg_score = sum(r[4] for r in rows if r[4]) / total

    result = [
        "═" * 60,
        "🎯  PREDICTION ACCURACY REPORT (Last 30 days)",
        "═" * 60,
        f"  Total Predictions Scored:  {total}",
        f"  Direction Accuracy:        {(correct/total)*100:.1f}%  ({correct}/{total} correct)",
        f"  Average Score:             {avg_score:.1f}/10",
        "",
        f"  {'DATE':<12} {'TICKER':<15} {'PREDICTED':>10} {'ACTUAL':>10} {'SCORE':>6}",
        "  " + "─" * 55
    ]
    for ticker, date, pred_dir, act_dir, score, _p_low, _p_high, _act_close in rows[:15]:
        match = "✅" if pred_dir == act_dir else "❌"
        result.append(f"  {date:<12} {ticker:<15} {pred_dir:>10} {act_dir:>10} {score:>5}/10 {match}")

    return CallToolResult(content=[TextContent(type="text", text="\n".join(result))])


async def _get_recommendation_history(ticker: str = "", days: int = 90):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    if ticker:
        c.execute("SELECT * FROM recommendations WHERE ticker = ? AND date >= ? ORDER BY date DESC", (ticker, cutoff))
    else:
        c.execute("SELECT * FROM recommendations WHERE date >= ? ORDER BY date DESC LIMIT 20", (cutoff,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        return CallToolResult(content=[TextContent(type="text", text="No past recommendations found.")])

    result = [f"📚  RECOMMENDATION HISTORY {'— ' + ticker if ticker else '(All Stocks)'}",
              "═" * 60]
    for row in rows:
        _, date, t, signal, cmp, target, sl, _horizon, conviction, reasoning, _risks = row
        exp = ((target - cmp) / cmp) * 100
        result.extend([
            f"\n  [{date}] {t} — {signal}  ({conviction} conviction)",
            f"  CMP: ₹{cmp:,.2f}  Target: ₹{target:,.2f} (+{exp:.1f}%)  SL: ₹{sl:,.2f}",
            f"  Thesis: {reasoning[:120]}...",
        ])

    return CallToolResult(content=[TextContent(type="text", text="\n".join(result))])


# ── Entry point ───────────────────────────────────────────────────────────────
async def main():
    """Run the MCP server over stdio until the client disconnects."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
