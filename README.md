# StockSense AI

A Streamlit demo app for AI-powered analysis of Indian (NSE/BSE) stocks —
live index/stock prices via `yfinance`, candlestick charts via `plotly`,
and structured buy/sell recommendations from the Claude API.

> **Demo only.** Not SEBI-registered investment advice. All AI output,
> "Top Picks", and the accuracy tracker are for demonstration purposes.

## Features

- **Login page** — simple demo gate (`demo` / `stocksense2026`).
- **Dashboard header** — live Nifty 50 (`^NSEI`) and Sensex (`^BSESN`)
  values, market open/closed status, and current IST date/time.
- **Top AI Picks Today** — 3 highlighted sample picks (signal, CMP, target,
  expected return, horizon).
- **Stock Analyser** — enter any NSE ticker (e.g. `RELIANCE.NS`), see a
  1-year candlestick chart, key stats (CMP, 52W high/low, market cap, P/E),
  and a Claude-generated recommendation (signal, target, stop loss, buy
  reasons, risks, and daily/weekly/monthly/yearly signals).
- **Prediction Accuracy Tracker** — sample table of the last 7 days'
  predictions vs. actual outcomes, with a headline 71% accuracy figure.
- **Watchlist** — live prices for RELIANCE.NS, TCS.NS, HDFCBANK.NS,
  INFY.NS, and ETERNAL.NS (formerly Zomato — the NSE symbol was renamed
  from `ZOMATO.NS`), each with a quick Claude-generated BUY/HOLD/SELL
  signal.
- **Footer** — demo/legal disclaimer.

The whole UI uses a custom dark theme with green accents.

## India Stock Intelligence MCP server

This repo also includes `mcp_server/india_stock_mcp.py`, an MCP server for
Claude Desktop that exposes live NSE/BSE data, fundamentals, news, watchlist
management, and recommendation/prediction tracking as tools. It shares its
SQLite database (`~/StockSenseAI/stocksense.db`) with this Streamlit app, so:

- The **Watchlist** section automatically uses the shared database once it
  has entries (editable in-app via the "⚙️ Manage Watchlist" panel, or from
  Claude Desktop), falling back to the bundled demo tickers otherwise.
- The **Stock Analyser**'s "💾 Save this recommendation" button and the
  MCP server's `save_recommendation` tool write to the same
  `recommendations` table, so either surface can review the other's calls.
- The **Prediction Accuracy Tracker** shows real numbers once predictions
  have been logged and scored via the MCP server; otherwise it shows the
  bundled 7-day demo data.

See `mcp_server/README.md` for the full tool list and Claude Desktop setup
instructions.

## Live NSE/BSE data via Groww (optional)

By default, all market data comes from `yfinance` (Yahoo Finance) — free,
no account needed, but typically ~15 minutes delayed. If you have a
[Groww](https://groww.in) account with an active
[Trading API subscription](https://groww.in/trade-api) (paid), you can
configure this app to pull genuinely live quotes, OHLC, and historical
candles from Groww's official API instead — see `src/groww_data.py`.

**Setup:**

1. Get a Groww Trading API subscription: https://groww.in/trade-api
2. Go to the [Groww Cloud API Keys page](https://groww.in/trade-api), log
   in, and click the dropdown next to "Generate API Key" → **"Generate
   TOTP token"** (the TOTP flow is used here rather than the API key/secret
   flow because it doesn't expire and doesn't need daily manual
   re-approval, which matters for an always-on web app).
3. Copy the **TOTP token** and **TOTP secret** it gives you.
4. Add both to `.streamlit/secrets.toml` (or as environment variables):

```toml
GROWW_API_KEY = "your-totp-token-here"
GROWW_TOTP_SECRET = "your-totp-secret-here"
```

5. Restart the app. The header will show "📡 Live via Groww" instead of
   "🕒 Yahoo Finance (~15 min delayed)" once connected. Use the sidebar's
   "📡 Live Data Source (Groww)" panel to check connection status or force
   a reconnect.

If Groww isn't configured, or any individual call to it fails for any
reason, the app automatically and silently falls back to `yfinance` — Groww
is purely an optional upgrade, never a hard requirement.

**Important caveats:**
- This integration was built directly against
  [Groww's published API docs](https://groww.in/trade-api/docs) but has
  not been tested against a real Groww account/subscription during
  development (no test credentials were available). Please verify it
  behaves as expected with your own account, particularly the Sensex
  (`^BSESN` → `SENSEX` on BSE) symbol mapping, which isn't explicitly
  confirmed in Groww's docs.
- Data fetched this way is tied to your personal Groww account and its API
  subscription/rate limits (per Groww's docs: Live Data calls are limited
  to 10/second and 300/minute). Review Groww's API terms of service before
  relying on this for anything beyond personal/demo use, especially if you
  deploy this app somewhere other people can access it.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure your Anthropic API key

The app calls the Claude API for stock recommendations. **No API key is
committed to this repository** — you need to provide your own:

**Option A — Streamlit secrets file (recommended for local runs)**

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit **`.streamlit/secrets.toml`** (the copy you just created, *not*
`secrets.toml.example`) and set:

```toml
ANTHROPIC_API_KEY = "sk-ant-your-real-key-here"
```

`.streamlit/secrets.toml` is git-ignored, so your key will never be
committed. Editing `secrets.toml.example` (or this README) does **not**
configure anything -- the app never reads those files, only the real
`secrets.toml` you create locally, an actual environment variable, a local
`.env` file, or (if deployed) Streamlit Community Cloud's Secrets UI.

**Option B — Environment variable**

```bash
export ANTHROPIC_API_KEY="sk-ant-your-real-key-here"
```

**Running as a Cursor Cloud Agent:** add `ANTHROPIC_API_KEY` as a secret in
the Cursor Dashboard (Cloud Agents → Secrets) so it's injected automatically.

If no key is configured, the Stock Analyser and Watchlist still work, but
fall back to a clearly-labelled heuristic (non-AI) demo recommendation
instead of calling Claude.

By default the app calls the `claude-sonnet-5` model. You can override this
by setting `CLAUDE_MODEL` (as a secret or environment variable) if you need
to point at a different model id.

## Run

```bash
streamlit run app.py
```

Then open the URL Streamlit prints (typically http://localhost:8501) and
log in with:

- **Username:** `demo`
- **Password:** `stocksense2026`

## Project structure

```
app.py                        # Main Streamlit app / page layout
src/
  auth.py                     # Login gate
  market_data.py              # yfinance helpers (indices, history, stats, volume, global markets)
  ai_engine.py                # Claude API integration + heuristic fallback
  news.py                     # Real news headline fetching (grounds the AI analysis)
  db.py                       # Shared SQLite data layer (see mcp_server/)
  sample_data.py              # Hardcoded demo data (top picks, accuracy log)
  styling.py                  # Shared custom CSS for the dark/green theme
mcp_server/
  india_stock_mcp.py          # MCP server for Claude Desktop
  requirements.txt            # MCP-server-only dependencies (see note below)
  test_client.py              # Standalone smoke test for the MCP server
  README.md                   # MCP server tool list + Claude Desktop setup
.streamlit/
  config.toml                 # Streamlit dark theme config
  secrets.toml.example        # Template for local secrets (copy, don't commit)
requirements.txt              # Web app dependencies only (see note below)
```

**Note on dependencies:** the top-level `requirements.txt` (installed above)
covers only what `app.py` actually needs. `mcp_server/` has its own
`mcp_server/requirements.txt` and is intentionally **not** part of the web
app's dependency list — its `mcp` package requires Python >=3.10 and pulls
in a heavy dependency chain that has no reason to risk breaking the web
app's deploy if it ever fails to install. If you're only running/deploying
`app.py` (e.g. on Streamlit Community Cloud), you never need
`mcp_server/requirements.txt` at all.

## Notes & limitations

- Market data comes from Yahoo Finance via `yfinance`; it can occasionally
  be delayed, rate-limited, or briefly unavailable — the UI degrades
  gracefully (shows "N/A"/"Data unavailable") rather than crashing.
- The "Top AI Picks" and "Prediction Accuracy Tracker" use hardcoded sample
  data, as requested, and are not derived from a live model.
- Watchlist AI signals are cached for up to an hour per ticker to limit
  Claude API usage; use the "Refresh AI Signals" button to force a refresh.
- This app is not connected to any broker and does not place trades.
