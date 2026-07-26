# India Stock Intelligence — MCP Server

An [MCP](https://modelcontextprotocol.io) server that gives Claude Desktop
(or any other MCP client) live tools for Indian (NSE/BSE) stock research:
market indices, quotes, fundamentals, historical performance/technicals,
news, watchlist management, and recommendation/prediction tracking.

It shares its SQLite database (`~/StockSenseAI/stocksense.db`) with the
StockSense AI Streamlit app in this repo (see `src/db.py`), so:

- Stocks added to the watchlist from Claude Desktop show up in the
  **Watchlist** section of the web dashboard, and vice versa.
- Recommendations saved via `save_recommendation` (from either Claude
  Desktop or the "💾 Save this recommendation" button in the Stock Analyser)
  are visible from both places via `get_recommendation_history`.
- Predictions saved/scored via `save_daily_prediction` /
  `score_yesterdays_prediction` feed the **Prediction Accuracy Tracker** on
  the dashboard once at least one prediction has been scored; until then the
  dashboard shows its bundled demo data.

## Tools

| Tool | Description |
|---|---|
| `get_market_indices` | Nifty 50, Sensex, Bank Nifty, Nifty Midcap 150, Nifty IT, Nifty Pharma |
| `get_stock_quote` | Live quote for one ticker (CMP, day/52W high-low, volume) |
| `get_stock_fundamentals` | P/E, P/B, market cap, EPS, ROE, D/E, dividend yield, sector, etc. |
| `get_historical_performance` | Returns over 1w/1m/3m/6m/1y + SMA20/50/200 + RSI(14) |
| `get_multiple_quotes` | Snapshot for a list of tickers, or the saved watchlist |
| `get_stock_news` | Google News RSS search for a stock or market topic |
| `get_watchlist` | List the saved watchlist |
| `update_watchlist` | Add/remove a ticker from the watchlist |
| `save_recommendation` | Persist a buy/sell call (signal, target, stop loss, thesis, risks) |
| `save_daily_prediction` | Log a pre-market direction/range prediction |
| `score_yesterdays_prediction` | Score a prior prediction against the actual result |
| `get_prediction_accuracy` | Accuracy report over the last 30 scored predictions |
| `get_recommendation_history` | Past recommendations for a ticker or all stocks |

## Setup

Dependencies are included in the repo's top-level `requirements.txt`
(`mcp`, `yfinance`, `pandas`, `requests`, `feedparser`). If you only want to
run the MCP server in isolation:

```bash
pip install mcp yfinance pandas requests feedparser
```

### Smoke test (no Claude Desktop required)

```bash
python mcp_server/test_client.py
```

This spawns the server as a subprocess, lists its tools, and exercises a
few of them (indices, a stock quote, watchlist add/remove) over the real
MCP stdio protocol.

### Configure Claude Desktop

Add an entry to Claude Desktop's `claude_desktop_config.json` (macOS:
`~/Library/Application Support/Claude/claude_desktop_config.json`; Windows:
`%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "india-stock-intelligence": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_server/india_stock_mcp.py"]
    }
  }
}
```

Use the absolute path to your Python interpreter (ideally the one in this
project's virtualenv, e.g. `/absolute/path/to/.venv/bin/python`) if `mcp`/
`yfinance`/etc. aren't installed globally. Restart Claude Desktop afterwards.

## Notes

- Running `python mcp_server/india_stock_mcp.py` directly from a terminal
  will appear to hang — it's waiting for an MCP client to connect over
  stdin/stdout. That's expected; use `test_client.py` or Claude Desktop to
  actually talk to it.
- The default seeded watchlist tracks `TMPV.NS` (Tata Motors Passenger
  Vehicles) and `ETERNAL.NS` rather than the legacy `TATAMOTORS.NS` /
  `ZOMATO.NS` symbols, since both companies' NSE tickers changed (Tata
  Motors demerged; Zomato Ltd was renamed to Eternal Ltd).
- Like the Streamlit app, this is a demo tool — not SEBI-registered
  investment advice.
