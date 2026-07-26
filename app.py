"""StockSense AI -- Indian Stock Market AI Analysis (Streamlit demo app).

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import ai_engine, auth, db, market_data, sample_data
from src.styling import CUSTOM_CSS, signal_badge_class

st.set_page_config(
    page_title="StockSense AI | Indian Stock Market Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

DIRECTION_FROM_SIGNAL = {
    "STRONG BUY": "UP",
    "BUY": "UP",
    "STRONG SELL": "DOWN",
    "SELL": "DOWN",
    "HOLD": "SIDEWAYS",
}


def _current_watchlist() -> tuple[list[str], dict[str, str]]:
    """Returns (tickers, display_names), preferring the shared DB watchlist."""
    db_watchlist = db.get_watchlist()
    if db_watchlist:
        tickers = [row["ticker"] for row in db_watchlist]
        display_names = {row["ticker"]: row["name"] or row["ticker"] for row in db_watchlist}
        return tickers, display_names
    return sample_data.WATCHLIST_TICKERS, sample_data.WATCHLIST_DISPLAY_NAMES


# --------------------------------------------------------------------------
# Top header (title, market status, indices)
# --------------------------------------------------------------------------
def render_top_header() -> None:
    now = market_data.now_ist()
    market_open = market_data.is_market_open(now)

    header_left, header_right = st.columns([2.4, 1.3])
    with header_left:
        st.markdown(
            """
            <div class="app-brand">
                <div class="app-brand-badge">🇮🇳</div>
                <div>
                    <div class="app-brand-text">India Stock Intelligence <span>Agent</span></div>
                    <div style="font-size:0.78rem;color:#9aa5a1;">
                        AI-Powered Stock Intelligence for Indian Markets
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with header_right:
        pill_class = "market-open" if market_open else "market-closed"
        pill_label = "MARKET OPEN" if market_open else "MARKET CLOSED"
        st.markdown(
            f"""
            <div style="text-align:right;">
                <span class="market-pill {pill_class}"><span class="dot"></span>{pill_label}</span>
                <div class="app-datetime" style="margin-top:0.4rem;">
                    <b>{now.strftime('%d %b %Y, %I:%M:%S %p')}</b> IST<br/>
                    Last updated: {now.strftime('%I:%M:%S %p')} IST
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    idx_cols = st.columns(2)
    for col, (name, ticker) in zip(idx_cols, market_data.INDEX_TICKERS.items()):
        with col:
            quote = market_data.fetch_index_quote(name, ticker)
            if quote.last_price is None:
                st.markdown(
                    f"""<div class="index-card"><div class="idx-name">{name} ({ticker})</div>
                    <div class="idx-value">Data unavailable</div></div>""",
                    unsafe_allow_html=True,
                )
                continue
            up = (quote.change or 0) >= 0
            arrow = "▲" if up else "▼"
            change_class = "idx-up" if up else "idx-down"
            st.markdown(
                f"""
                <div class="index-card">
                    <div class="idx-name">{name} &nbsp;·&nbsp; {ticker}</div>
                    <div class="idx-value">{quote.last_price:,.2f}</div>
                    <div class="{change_class}">{arrow} {quote.change:,.2f} ({quote.change_pct:+.2f}%)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# --------------------------------------------------------------------------
# Top picks (compact list)
# --------------------------------------------------------------------------
def render_top_picks() -> None:
    st.markdown('<div class="picks-banner">', unsafe_allow_html=True)
    st.markdown("<h3>⭐ Top Picks Today</h3>", unsafe_allow_html=True)
    for i, pick in enumerate(sample_data.TOP_AI_PICKS, start=1):
        badge_cls = signal_badge_class(pick["signal"])
        st.markdown(
            f"""
            <div class="top-pick-row">
                <div class="top-pick-rank">{i}</div>
                <div class="top-pick-name">{pick['stock']}</div>
                <span class="tf-badge {badge_cls}">{pick['signal']}</span>
                <div class="top-pick-price">CMP ₹{pick['cmp']:,.2f} &nbsp;→&nbsp; Target ₹{pick['target']:,.2f}</div>
                <span class="pick-return">+{pick['expected_return']}%</span>
                <div class="top-pick-horizon">{pick['horizon']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Stock analysis (chart, stats, AI recommendation)
# --------------------------------------------------------------------------
def render_candlestick(hist: pd.DataFrame, ticker: str) -> None:
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=hist.index,
                open=hist["Open"],
                high=hist["High"],
                low=hist["Low"],
                close=hist["Close"],
                increasing_line_color="#00e676",
                decreasing_line_color="#ff5252",
                name=ticker,
            )
        ]
    )
    fig.update_layout(
        height=460,
        margin=dict(l=10, r=10, t=30, b=10),
        template="plotly_dark",
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        xaxis_rangeslider_visible=False,
        title=f"{ticker} — 1 Year Price History",
    )
    st.plotly_chart(fig, width="stretch")


def summarize_recent_history(hist: pd.DataFrame) -> str:
    if hist.empty:
        return "No historical data available."
    recent = hist.tail(10)
    lines = [
        f"{idx.strftime('%Y-%m-%d')}: close={row['Close']:.2f}, volume={int(row['Volume'])}"
        for idx, row in recent.iterrows()
    ]
    return "\n".join(lines)


def render_timeframe_signals_inline(signals: dict) -> None:
    order = [("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly"), ("yearly", "Yearly")]
    spans = []
    for key, label in order:
        sig = signals.get(key, "HOLD")
        cls = signal_badge_class(sig)
        spans.append(
            f'<span class="tf-inline"><b>{label}:</b> <span class="tf-badge {cls}">{sig}</span></span>'
        )
    st.markdown(f'<div class="ai-summary-row tf-inline-row">{"".join(spans)}</div>', unsafe_allow_html=True)


def render_api_key_diagnostics() -> None:
    info = ai_engine.get_api_key_debug_info()
    with st.expander("🔧 Why isn't my Anthropic API key being detected?"):
        st.markdown(
            f"""
- Found in `st.secrets["ANTHROPIC_API_KEY"]`: {"✅ yes" if info["found_in_secrets"] else "❌ no"}
- Found in environment variable `ANTHROPIC_API_KEY`: {"✅ yes" if info["found_in_env"] else "❌ no"}
- `.streamlit/secrets.toml` file exists here: {"✅ yes" if info["secrets_file_exists"] else "❌ no"}
"""
        )
        if info["secrets_error"]:
            st.caption(f"Note: reading `st.secrets` raised: `{info['secrets_error']}`")
        if info["looks_like_placeholder"]:
            st.warning(
                "The value found doesn't look like a real Anthropic key (real keys start "
                "with `sk-ant-`). You may still have the example placeholder in place, "
                "or a typo/extra quotes around the value.",
                icon="⚠️",
            )
        st.markdown(
            """
**Common causes, in order of likelihood:**

1. **Wrong file name/location.** It must be `.streamlit/secrets.toml` (copied from
   `.streamlit/secrets.toml.example`), sitting next to `app.py`'s `.streamlit/` folder —
   not `secrets.toml.example` itself, and not in the repo root.
2. **Wrong key name.** Must be exactly `ANTHROPIC_API_KEY` (all caps, with underscores),
   e.g. `ANTHROPIC_API_KEY = "sk-ant-..."`.
3. **Deployed on Streamlit Community Cloud?** Secrets must be pasted into
   **App → Settings → Secrets** in TOML format, then the app needs a **reboot**
   (Manage app → Reboot) — editing secrets doesn't always auto-restart the app.
4. **Set as a shell env var?** It only applies to processes started *after* you
   ran `export ANTHROPIC_API_KEY=...` — restart `streamlit run app.py` in that
   same terminal session.
5. **Cursor Cloud Agent secret?** Secrets are injected when a new agent VM
   boots, not into an already-running session. Added it just now? Start a new
   Cloud Agent conversation/run for it to take effect there.
6. **`.env` file?** Supported (loaded automatically), but only if it's in the
   same directory you run `streamlit run app.py` from, with a line like
   `ANTHROPIC_API_KEY=sk-ant-...` (no quotes needed in `.env` files).
"""
        )


def _run_analysis(ticker: str) -> None:
    """Fetches data + AI recommendation for `ticker` and stores it in session_state."""
    ticker = (ticker or "").strip().upper()
    if not ticker:
        st.session_state["analysis_error"] = "Please choose or type a valid NSE ticker (e.g. RELIANCE.NS)."
        return

    with st.spinner(f"Fetching 1-year price history for {ticker}..."):
        hist = market_data.fetch_price_history(ticker, period="1y")

    if hist.empty:
        st.session_state["analysis_error"] = f"Could not fetch data for '{ticker}'. Check the ticker symbol."
        st.session_state.pop("analysis", None)
        return

    with st.spinner("Fetching fundamentals..."):
        stats = market_data.fetch_stock_stats(ticker)

    with st.spinner("Asking Claude for a structured recommendation..."):
        rec = ai_engine.get_stock_recommendation(
            ticker=ticker,
            company_name=stats.name or ticker,
            cmp=stats.cmp,
            week52_high=stats.week52_high,
            week52_low=stats.week52_low,
            market_cap=stats.market_cap,
            pe_ratio=stats.pe_ratio,
            recent_history_summary=summarize_recent_history(hist),
        )

    # Cache results in session_state so subsequent reruns (e.g. clicking
    # "Save this recommendation" or expanding history below) keep showing
    # this analysis instead of resetting, and so we don't re-call Claude
    # on every unrelated widget interaction.
    st.session_state["analysis_error"] = None
    st.session_state["analysis"] = {
        "ticker": ticker,
        "hist": hist,
        "stats": stats,
        "rec": rec,
    }


def render_analysis_results() -> None:
    st.markdown('<div class="section-title">🔍 Stock Analysis</div>', unsafe_allow_html=True)

    if not ai_engine.is_ai_configured():
        st.info(
            "No Anthropic API key detected. Set `ANTHROPIC_API_KEY` in `.streamlit/secrets.toml` "
            "or as an environment variable to enable live Claude-powered recommendations. "
            "Showing a heuristic demo analysis in the meantime.",
            icon="ℹ️",
        )
        render_api_key_diagnostics()

    if st.session_state.get("analysis_error"):
        st.error(st.session_state["analysis_error"])

    analysis = st.session_state.get("analysis")
    if not analysis:
        st.caption(
            "👈 Pick a stock (or type a custom NSE ticker) in the sidebar and click "
            "**🔍 Analyze** to see the chart, stats, and AI recommendation here."
        )
        return

    ticker = analysis["ticker"]
    hist = analysis["hist"]
    stats = analysis["stats"]
    rec = analysis["rec"]

    if len(hist) > 1:
        day_change = hist["Close"].iloc[-1] - hist["Close"].iloc[-2]
        day_change_pct = (day_change / hist["Close"].iloc[-2] * 100) if hist["Close"].iloc[-2] else 0.0
    else:
        day_change = day_change_pct = 0.0
    up = day_change >= 0
    arrow = "▲" if up else "▼"
    change_cls = "idx-up" if up else "idx-down"
    cmp_display = f"₹{stats.cmp:,.2f}" if stats.cmp else "N/A"
    st.markdown(
        f"""
        <div class="quick-quote-line">
            📊 <b>{ticker}</b>
            <span class="quick-quote-price">{cmp_display}</span>
            <span class="{change_cls}">{arrow} {abs(day_change_pct):.2f}%</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_candlestick(hist, ticker)

    stat_cols = st.columns(5)
    stat_items = [
        ("CMP", cmp_display),
        ("52W High", f"₹{stats.week52_high:,.2f}" if stats.week52_high else "N/A"),
        ("52W Low", f"₹{stats.week52_low:,.2f}" if stats.week52_low else "N/A"),
        ("Market Cap", market_data.format_market_cap(stats.market_cap)),
        ("P/E Ratio", f"{stats.pe_ratio:.2f}" if stats.pe_ratio else "N/A"),
    ]
    for col, (label, value) in zip(stat_cols, stat_items):
        with col:
            st.markdown(
                f"""<div class="stat-box"><div class="stat-label">{label}</div>
                <div class="stat-value">{value}</div></div>""",
                unsafe_allow_html=True,
            )

    st.markdown("#### 🤖 AI Analysis")
    if rec.is_fallback:
        st.warning(
            "Showing a heuristic fallback recommendation (Claude API unavailable"
            + (f": {rec.error}" if rec.error else "")
            + "). Configure a valid ANTHROPIC_API_KEY to get real AI analysis.",
            icon="⚠️",
        )

    badge_cls = signal_badge_class(rec.signal)
    conviction_cls = {
        "HIGH": "badge-strongbuy",
        "MEDIUM": "badge-hold",
        "LOW": "badge-sell",
    }.get(rec.conviction, "badge-hold")

    st.markdown('<div class="rec-card">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="ai-summary-row">
            <span class="signal-badge {badge_cls}">SIGNAL: {rec.signal}</span>
            <span class="signal-badge {conviction_cls}">CONVICTION: {rec.conviction}</span>
        </div>
        <div class="ai-summary-row">
            <span><b>TARGET:</b> {f"₹{rec.target_price:,.2f}" if rec.target_price else "N/A"}</span>
            <span><b>STOP LOSS:</b> {f"₹{rec.stop_loss:,.2f}" if rec.stop_loss else "N/A"}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_timeframe_signals_inline(rec.timeframe_signals)

    reason_col, risk_col = st.columns(2)
    with reason_col:
        st.markdown("**✅ Key Buy Reasons**")
        for reason in rec.buy_reasons:
            st.markdown(f"- {reason}")
    with risk_col:
        st.markdown("**⚠️ Key Risks**")
        for risk in rec.risks:
            st.markdown(f"- {risk}")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("")
    if st.button("💾 Save this recommendation", key=f"save_rec_{ticker}"):
        saved = db.save_recommendation(
            ticker=ticker,
            signal=rec.signal,
            cmp=stats.cmp or 0.0,
            target=rec.target_price or 0.0,
            stop_loss=rec.stop_loss or 0.0,
            reasoning=" | ".join(rec.buy_reasons),
            conviction=rec.conviction,
            key_risks=" | ".join(rec.risks),
        )
        if saved:
            st.success(
                "Saved to the shared StockSense database — also visible from "
                "Claude Desktop via the `get_recommendation_history` MCP tool."
            )
        else:
            st.error("Could not save recommendation (local database unavailable).")

    past_recs = db.get_recommendation_history(ticker=ticker, days=180)
    if past_recs:
        with st.expander(f"📚 Past AI Recommendations for {ticker} ({len(past_recs)})"):
            past_df = pd.DataFrame(past_recs)[
                ["date", "signal", "cmp", "target", "stop_loss", "conviction"]
            ].rename(
                columns={
                    "date": "Date",
                    "signal": "Signal",
                    "cmp": "CMP",
                    "target": "Target",
                    "stop_loss": "Stop Loss",
                    "conviction": "Conviction",
                }
            )
            st.dataframe(past_df, width="stretch", hide_index=True)


# --------------------------------------------------------------------------
# Prediction accuracy tracker
# --------------------------------------------------------------------------
def render_accuracy_tracker() -> None:
    st.markdown('<div class="section-title">📈 Prediction Accuracy</div>', unsafe_allow_html=True)

    live_predictions = db.get_scored_predictions(limit=30)
    live_accuracy = db.get_prediction_accuracy_pct(live_predictions)

    if live_predictions and live_accuracy is not None:
        accuracy_pct = live_accuracy
        caption = f"Based on the last {len(live_predictions)} predictions scored (up to 30 days)"
        df_display = pd.DataFrame(live_predictions).rename(
            columns={
                "date": "Date",
                "ticker": "Stock",
                "predicted_direction": "Predicted Direction",
                "actual_direction": "Actual Direction",
                "score": "Score (/10)",
            }
        )[["Date", "Stock", "Predicted Direction", "Actual Direction", "Score (/10)"]]
    else:
        accuracy_pct = sample_data.OVERALL_ACCURACY
        caption = "Based on the last 7 trading days (demo data)"
        df = pd.DataFrame(sample_data.PREDICTION_HISTORY)
        df_display = df.rename(
            columns={
                "date": "Date",
                "stock": "Stock",
                "predicted": "Predicted Signal",
                "actual": "Actual Move",
                "correct": "Correct?",
            }
        ).copy()
        df_display["Correct?"] = df_display["Correct?"].map({True: "✅ Yes", False: "❌ No"})

    st.markdown(
        f"""
        <div class="accuracy-hero">
            <div class="big-num">{accuracy_pct}%</div>
            <div>
                <b>Overall Accuracy</b><br/>
                <span style="color:#9aa5a1;font-size:0.85rem;">{caption}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("View prediction log"):
        st.dataframe(df_display, width="stretch", hide_index=True)


# --------------------------------------------------------------------------
# Watchlist (detailed table)
# --------------------------------------------------------------------------
def render_watchlist() -> None:
    st.markdown('<div class="section-title">⭐ Watchlist</div>', unsafe_allow_html=True)

    tickers, display_names = _current_watchlist()
    if db.get_watchlist():
        st.caption(
            "📡 Synced with the shared StockSense database — edits from the sidebar are also "
            "visible from Claude Desktop via the India Stock Intelligence MCP server."
        )

    daily_run_results = st.session_state.get("daily_run_results")
    if daily_run_results:
        with st.expander(f"📅 Last Daily Run results ({len(daily_run_results)} stocks)", expanded=True):
            st.dataframe(pd.DataFrame(daily_run_results), width="stretch", hide_index=True)

    rows = []
    for ticker in tickers:
        hist = market_data.fetch_price_history(ticker, period="5d")
        price = market_data.fetch_live_price(ticker)

        if not hist.empty and len(hist) > 1:
            change_pct = (hist["Close"].iloc[-1] / hist["Close"].iloc[-2] - 1) * 100
            summary = f"price moved {change_pct:+.2f}% over the last session"
        else:
            change_pct = None
            summary = "insufficient recent data"

        signal = ai_engine.get_quick_signal(ticker, summary)
        display_name = display_names.get(ticker, ticker)
        rows.append(
            {
                "Ticker": display_name,
                "Live Price": f"₹{price:,.2f}" if price else "N/A",
                "Today's Change": f"{change_pct:+.2f}%" if change_pct is not None else "N/A",
                "AI Signal": signal,
            }
        )

    wl_df = pd.DataFrame(rows)

    def _style_signal(val: str) -> str:
        colors = {"BUY": "#00e676", "STRONG BUY": "#00e676", "HOLD": "#ffc107", "SELL": "#ff5252"}
        color = colors.get(val, "#e6e6e6")
        return f"color: {color}; font-weight: 700;"

    styled = wl_df.style.map(_style_signal, subset=["AI Signal"])
    st.dataframe(styled, width="stretch", hide_index=True)


# --------------------------------------------------------------------------
# Footer
# --------------------------------------------------------------------------
def render_footer() -> None:
    st.markdown(
        """
        <div class="app-footer">
            <div class="disclaimer">This is a demo. Not SEBI-registered investment advice.</div>
            <div>© 2026 StockSense AI — For Investor Demo Only</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------
# Sidebar (control panel)
# --------------------------------------------------------------------------
def _run_daily_batch(tickers: list[str]) -> None:
    results = []
    with st.spinner(f"Running daily AI scan for {len(tickers)} watchlist stocks..."):
        for ticker in tickers:
            hist = market_data.fetch_price_history(ticker, period="5d")
            price = market_data.fetch_live_price(ticker)

            if not hist.empty and len(hist) > 1:
                change_pct = (hist["Close"].iloc[-1] / hist["Close"].iloc[-2] - 1) * 100
                summary = f"price moved {change_pct:+.2f}% over the last session"
            else:
                summary = "insufficient recent data"

            signal = ai_engine.get_quick_signal(ticker, summary)
            direction = DIRECTION_FROM_SIGNAL.get(signal, "SIDEWAYS")
            low = round(price * 0.99, 2) if price else None
            high = round(price * 1.01, 2) if price else None
            saved = db.save_prediction(
                ticker,
                predicted_direction=direction,
                predicted_low=low,
                predicted_high=high,
                confidence="MEDIUM",
                notes=f"Auto-logged by dashboard Daily Run (signal: {signal})",
            )
            results.append(
                {
                    "Ticker": ticker,
                    "AI Signal": signal,
                    "Predicted Direction": direction,
                    "Logged": "✅" if saved else "❌",
                }
            )
    st.session_state["daily_run_results"] = results


def render_sidebar() -> None:
    st.sidebar.markdown('<div class="sidebar-brand">🇮🇳 Control Panel</div>', unsafe_allow_html=True)

    tickers, display_names = _current_watchlist()

    st.sidebar.markdown('<div class="sidebar-section-title">Add Stock</div>', unsafe_allow_html=True)
    custom_option = "✏️ Custom ticker..."
    choice = st.sidebar.selectbox(
        "Add Stock", options=tickers + [custom_option], label_visibility="collapsed"
    )
    if choice == custom_option:
        active_ticker = st.sidebar.text_input(
            "Custom ticker", placeholder="e.g. BAJFINANCE.NS", label_visibility="collapsed"
        )
    else:
        active_ticker = choice

    if st.sidebar.button("🔍 Analyze", type="primary", width="stretch"):
        _run_analysis(active_ticker)

    st.sidebar.markdown('<div class="sidebar-section-title">⭐ Watchlist</div>', unsafe_allow_html=True)
    for ticker in tickers:
        label = display_names.get(ticker, ticker)
        if st.sidebar.button(f"• {label}", key=f"wl_nav_{ticker}", width="stretch"):
            _run_analysis(ticker)

    with st.sidebar.expander("⚙️ Manage Watchlist"):
        new_ticker = st.text_input("Add ticker", placeholder="e.g. BAJFINANCE.NS", key="wl_add_ticker")
        new_name = st.text_input("Company name (optional)", key="wl_add_name")
        if st.button("Add to watchlist", width="stretch", key="wl_add_btn"):
            if new_ticker.strip():
                db.add_to_watchlist(new_ticker.strip().upper(), new_name.strip() or new_ticker.strip().upper())
                st.rerun()
        if tickers:
            remove_ticker = st.selectbox("Remove ticker", options=tickers, key="wl_remove_select")
            if st.button("Remove from watchlist", width="stretch", key="wl_remove_btn"):
                db.remove_from_watchlist(remove_ticker)
                st.rerun()

    st.sidebar.markdown('<div class="sidebar-section-title">Batch Actions</div>', unsafe_allow_html=True)
    if st.sidebar.button("🔄 Refresh AI Signals", width="stretch", help="Clears the hourly signal cache."):
        ai_engine.get_quick_signal.clear()
        st.sidebar.success("Signals will refresh on next load.")
    if st.sidebar.button(
        "📅 Daily Run",
        width="stretch",
        help="Generate and log today's AI signal + predicted direction for every watchlist stock.",
    ):
        _run_daily_batch(tickers)
        st.sidebar.success(f"Daily Run complete for {len(tickers)} stocks — see Watchlist section.")

    st.sidebar.divider()
    if st.sidebar.button("Log Out", width="stretch"):
        auth.log_out()
        st.rerun()


# --------------------------------------------------------------------------
# Page routing
# --------------------------------------------------------------------------
def render_dashboard() -> None:
    render_sidebar()
    render_top_header()
    render_top_picks()
    render_analysis_results()
    render_accuracy_tracker()
    render_watchlist()
    render_footer()


def main() -> None:
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if auth.is_authenticated():
        render_dashboard()
    else:
        # No sidebar content is rendered on the login page, so hide the
        # (otherwise empty) sidebar panel and its collapse toggle entirely.
        st.markdown(
            "<style>[data-testid='stSidebar'], [data-testid='collapsedControl'] "
            "{display: none;}</style>",
            unsafe_allow_html=True,
        )
        auth.render_login_page()


if __name__ == "__main__":
    main()
