"""StockSense AI -- Indian Stock Market AI Analysis (Streamlit demo app).

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import ai_engine, auth, market_data, sample_data
from src.styling import CUSTOM_CSS, signal_badge_class

st.set_page_config(
    page_title="StockSense AI | Indian Stock Market Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------
def render_header() -> None:
    now = market_data.now_ist()
    market_open = market_data.is_market_open(now)

    header_left, header_right = st.columns([2.4, 1.3])
    with header_left:
        st.markdown(
            """
            <div class="app-brand">
                <div class="app-brand-badge">📈</div>
                <div>
                    <div class="app-brand-text">StockSense <span>AI</span></div>
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
# Top AI picks
# --------------------------------------------------------------------------
def render_top_picks() -> None:
    st.markdown('<div class="picks-banner">', unsafe_allow_html=True)
    st.markdown("<h3>🎯 Top AI Picks Today</h3>", unsafe_allow_html=True)
    cols = st.columns(3)
    for col, pick in zip(cols, sample_data.TOP_AI_PICKS):
        with col:
            st.markdown(
                f"""
                <div class="pick-card">
                    <div class="pick-stock">{pick['stock']}</div>
                    <div class="pick-signal">{pick['signal']}</div>
                    <div class="pick-row"><span>CMP</span><b>₹{pick['cmp']:,.2f}</b></div>
                    <div class="pick-row"><span>Target</span><b>₹{pick['target']:,.2f}</b></div>
                    <div class="pick-row"><span>Expected Return</span>
                        <span class="pick-return">+{pick['expected_return']}%</span></div>
                    <div class="pick-row"><span>Horizon</span><b>{pick['horizon']}</b></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Stock analyser
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


def render_timeframe_signals(signals: dict) -> None:
    order = [("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly"), ("yearly", "Yearly")]
    cols = st.columns(4)
    for col, (key, label) in zip(cols, order):
        sig = signals.get(key, "HOLD")
        cls = signal_badge_class(sig)
        with col:
            st.markdown(
                f"""<div class="stat-box"><div class="stat-label">{label}</div>
                <span class="tf-badge {cls}">{sig}</span></div>""",
                unsafe_allow_html=True,
            )


def render_stock_analyser() -> None:
    st.markdown('<div class="section-title">🔍 Stock Analyser</div>', unsafe_allow_html=True)

    if not ai_engine.is_ai_configured():
        st.info(
            "No Anthropic API key detected. Set `ANTHROPIC_API_KEY` in `.streamlit/secrets.toml` "
            "or as an environment variable to enable live Claude-powered recommendations. "
            "Showing a heuristic demo analysis in the meantime.",
            icon="ℹ️",
        )

    with st.form("analyser_form"):
        col1, col2 = st.columns([3, 1])
        with col1:
            ticker_input = st.text_input(
                "NSE Ticker", value="RELIANCE.NS", placeholder="e.g. RELIANCE.NS"
            )
        with col2:
            st.write("")
            st.write("")
            submitted = st.form_submit_button("Analyse", type="primary", width="stretch")

    if not submitted:
        return

    ticker = ticker_input.strip().upper()
    if not ticker:
        st.warning("Please enter a valid NSE ticker (e.g. RELIANCE.NS).")
        return

    with st.spinner(f"Fetching 1-year price history for {ticker}..."):
        hist = market_data.fetch_price_history(ticker, period="1y")

    if hist.empty:
        st.error(f"Could not fetch data for '{ticker}'. Check the ticker symbol and try again.")
        return

    render_candlestick(hist, ticker)

    with st.spinner("Fetching fundamentals..."):
        stats = market_data.fetch_stock_stats(ticker)

    stat_cols = st.columns(5)
    stat_items = [
        ("CMP", f"₹{stats.cmp:,.2f}" if stats.cmp else "N/A"),
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

    st.markdown("#### 🤖 Claude AI Recommendation")
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

    if rec.is_fallback:
        st.warning(
            "Showing a heuristic fallback recommendation (Claude API unavailable"
            + (f": {rec.error}" if rec.error else "")
            + "). Configure a valid ANTHROPIC_API_KEY to get real AI analysis.",
            icon="⚠️",
        )

    badge_cls = signal_badge_class(rec.signal)
    st.markdown('<div class="rec-card">', unsafe_allow_html=True)
    top_cols = st.columns([1, 1, 1])
    with top_cols[0]:
        st.markdown(
            f'<span class="signal-badge {badge_cls}">{rec.signal}</span>', unsafe_allow_html=True
        )
    with top_cols[1]:
        st.markdown(
            f"**Target Price:** ₹{rec.target_price:,.2f}" if rec.target_price else "**Target Price:** N/A"
        )
    with top_cols[2]:
        st.markdown(
            f"**Stop Loss:** ₹{rec.stop_loss:,.2f}" if rec.stop_loss else "**Stop Loss:** N/A"
        )

    reason_col, risk_col = st.columns(2)
    with reason_col:
        st.markdown("**✅ Key Buy Reasons**")
        for reason in rec.buy_reasons:
            st.markdown(f"- {reason}")
    with risk_col:
        st.markdown("**⚠️ Key Risks**")
        for risk in rec.risks:
            st.markdown(f"- {risk}")

    st.markdown("**📅 Signal by Timeframe**")
    render_timeframe_signals(rec.timeframe_signals)
    st.markdown("</div>", unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Prediction accuracy tracker
# --------------------------------------------------------------------------
def render_accuracy_tracker() -> None:
    st.markdown('<div class="section-title">📊 Prediction Accuracy Tracker</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="accuracy-hero">
            <div class="big-num">{sample_data.OVERALL_ACCURACY}%</div>
            <div>
                <b>Overall Accuracy</b><br/>
                <span style="color:#9aa5a1;font-size:0.85rem;">Based on the last 7 trading days (demo data)</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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

    st.dataframe(df_display, width="stretch", hide_index=True)


# --------------------------------------------------------------------------
# Watchlist
# --------------------------------------------------------------------------
def render_watchlist() -> None:
    st.markdown('<div class="section-title">⭐ Watchlist</div>', unsafe_allow_html=True)

    refresh = st.button("🔄 Refresh AI Signals", help="AI signals are cached for up to an hour per ticker.")
    if refresh:
        ai_engine.get_quick_signal.clear()

    rows = []
    for ticker in sample_data.WATCHLIST_TICKERS:
        hist = market_data.fetch_price_history(ticker, period="5d")
        price = market_data.fetch_live_price(ticker)

        if not hist.empty and len(hist) > 1:
            change_pct = (hist["Close"].iloc[-1] / hist["Close"].iloc[-2] - 1) * 100
            summary = f"price moved {change_pct:+.2f}% over the last session"
        else:
            change_pct = None
            summary = "insufficient recent data"

        signal = ai_engine.get_quick_signal(ticker, summary)
        display_name = sample_data.WATCHLIST_DISPLAY_NAMES.get(ticker, ticker)
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
# Page routing
# --------------------------------------------------------------------------
def render_dashboard() -> None:
    top_bar = st.columns([6, 1])
    with top_bar[1]:
        if st.button("Log Out", width="stretch"):
            auth.log_out()
            st.rerun()

    render_header()
    render_top_picks()
    render_stock_analyser()
    render_accuracy_tracker()
    render_watchlist()
    render_footer()


def main() -> None:
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if auth.is_authenticated():
        render_dashboard()
    else:
        auth.render_login_page()


if __name__ == "__main__":
    main()
