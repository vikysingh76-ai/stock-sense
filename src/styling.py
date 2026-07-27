"""Shared custom CSS for the dark / green "StockSense AI" theme."""

CUSTOM_CSS = """
<style>
    #MainMenu, footer {visibility: hidden;}

    .stApp {
        background: radial-gradient(circle at top left, #10241a 0%, #0e1117 45%) fixed;
    }

    /* ---------- Login page ---------- */
    .login-wrapper { display: flex; justify-content: center; margin-top: 2rem; }
    .login-card { text-align: center; max-width: 520px; }
    .login-logo {
        font-size: 3.2rem; line-height: 1;
        width: 84px; height: 84px; margin: 0 auto 0.75rem auto;
        display: flex; align-items: center; justify-content: center;
        background: linear-gradient(135deg, #00c853, #00e676);
        border-radius: 20px;
        box-shadow: 0 0 32px rgba(0, 200, 83, 0.45);
    }
    .login-title { font-size: 2.1rem; font-weight: 800; margin-bottom: 0.15rem; color: #f1f5f2; }
    .login-title span { color: #00e676; }
    .login-tagline { color: #9aa5a1; font-size: 1.02rem; margin-bottom: 1.6rem; }
    .login-hint {
        text-align: center; font-size: 0.85rem; color: #8a938f; margin-top: 0.9rem;
        background: rgba(0, 200, 83, 0.08); border: 1px solid rgba(0, 200, 83, 0.25);
        border-radius: 8px; padding: 0.6rem 0.8rem;
    }
    .login-disclaimer {
        text-align: center; font-size: 0.78rem; color: #6b7570; margin-top: 1.4rem;
        font-style: italic;
    }

    /* ---------- Header ---------- */
    .app-header {
        display: flex; justify-content: space-between; align-items: center;
        flex-wrap: wrap; gap: 0.75rem;
        padding: 0.9rem 1.3rem; margin-bottom: 1.1rem;
        background: linear-gradient(135deg, #131a15 0%, #10201580 100%);
        border: 1px solid #1f2b23; border-radius: 14px;
    }
    .app-brand { display: flex; align-items: center; gap: 0.6rem; }
    .app-brand-badge {
        font-size: 1.4rem; width: 42px; height: 42px; border-radius: 10px;
        background: linear-gradient(135deg, #00c853, #00e676);
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 0 18px rgba(0, 200, 83, 0.4);
    }
    .app-brand-text { font-size: 1.25rem; font-weight: 800; color: #f1f5f2; }
    .app-brand-text span { color: #00e676; }
    .app-datetime { text-align: right; font-size: 0.85rem; color: #9aa5a1; }
    .app-datetime b { color: #e6e6e6; }

    .index-card {
        background: #131a15; border: 1px solid #1f2b23; border-radius: 12px;
        padding: 0.9rem 1.1rem; text-align: left;
    }
    .index-card .idx-name { font-size: 0.82rem; color: #9aa5a1; font-weight: 600; letter-spacing: 0.02em; }
    .index-card .idx-value { font-size: 1.55rem; font-weight: 800; color: #f1f5f2; margin: 0.15rem 0; }
    .idx-up { color: #00e676; font-weight: 700; }
    .idx-down { color: #ff5252; font-weight: 700; }

    .market-pill {
        display: inline-flex; align-items: center; gap: 0.4rem;
        padding: 0.32rem 0.8rem; border-radius: 999px; font-weight: 700; font-size: 0.82rem;
    }
    .market-open { background: rgba(0, 230, 118, 0.15); color: #00e676; border: 1px solid rgba(0,230,118,0.4); }
    .market-closed { background: rgba(255, 82, 82, 0.15); color: #ff5252; border: 1px solid rgba(255,82,82,0.4); }
    .dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; display: inline-block; }

    /* ---------- Top AI picks ---------- */
    .picks-banner {
        background: linear-gradient(135deg, rgba(0,200,83,0.14), rgba(0,230,118,0.03));
        border: 1px solid rgba(0, 230, 118, 0.35);
        border-radius: 16px; padding: 1.1rem 1.3rem 1.3rem 1.3rem; margin-bottom: 1.4rem;
    }
    .picks-banner h3 { margin: 0 0 0.9rem 0; color: #00e676; font-weight: 800; }
    .pick-card {
        background: #10201a; border: 1px solid rgba(0, 230, 118, 0.28);
        border-radius: 12px; padding: 0.95rem 1.05rem; height: 100%;
    }
    .pick-stock { font-weight: 800; font-size: 1.05rem; color: #f1f5f2; }
    .pick-signal {
        display: inline-block; margin: 0.35rem 0 0.6rem 0; padding: 0.2rem 0.6rem;
        border-radius: 6px; font-size: 0.74rem; font-weight: 800; letter-spacing: 0.03em;
        background: rgba(0, 230, 118, 0.18); color: #00e676;
    }
    .pick-row { display: flex; justify-content: space-between; font-size: 0.85rem; color: #b7c0bb; padding: 0.12rem 0; }
    .pick-row b { color: #f1f5f2; }
    .pick-return { color: #00e676; font-weight: 800; }

    /* ---------- Section headers ---------- */
    .section-title {
        font-size: 1.15rem; font-weight: 800; color: #f1f5f2;
        margin: 1.6rem 0 0.8rem 0; padding-bottom: 0.4rem;
        border-bottom: 2px solid rgba(0, 230, 118, 0.3);
    }

    .stat-box {
        background: #131a15; border: 1px solid #1f2b23; border-radius: 10px;
        padding: 0.75rem 0.9rem; text-align: center;
    }
    .stat-box .stat-label { font-size: 0.75rem; color: #9aa5a1; }
    .stat-box .stat-value { font-size: 1.15rem; font-weight: 800; color: #f1f5f2; }

    .rec-card {
        background: #10201a; border: 1px solid rgba(0,230,118,0.3); border-radius: 14px;
        padding: 1.1rem 1.3rem; margin-top: 0.6rem;
    }
    .badge-buy, .badge-strongbuy { background: rgba(0,230,118,0.18); color: #00e676; }
    .badge-sell, .badge-strongsell { background: rgba(255,82,82,0.18); color: #ff5252; }
    .badge-hold { background: rgba(255,193,7,0.18); color: #ffc107; }
    .signal-badge {
        display: inline-block; padding: 0.32rem 0.85rem; border-radius: 7px;
        font-weight: 800; font-size: 0.95rem; letter-spacing: 0.03em;
    }
    .tf-badge {
        display: inline-block; padding: 0.2rem 0.55rem; border-radius: 6px;
        font-size: 0.72rem; font-weight: 700; margin-right: 0.3rem;
    }

    .app-footer {
        text-align: center; margin-top: 2.5rem; padding: 1.2rem 0 0.6rem 0;
        border-top: 1px solid #1f2b23; color: #7b847f; font-size: 0.82rem;
    }
    .app-footer .disclaimer { color: #ffb74d; font-weight: 600; margin-bottom: 0.25rem; }

    .accuracy-hero {
        display: flex; align-items: center; gap: 1rem;
        background: linear-gradient(135deg, rgba(0,200,83,0.14), transparent);
        border: 1px solid rgba(0,230,118,0.3); border-radius: 12px; padding: 1rem 1.2rem;
        margin-bottom: 1rem;
    }
    .accuracy-hero .big-num { font-size: 2.3rem; font-weight: 900; color: #00e676; }

    /* ---------- Sidebar control panel ---------- */
    [data-testid="stSidebar"] {
        background: #10151a; border-right: 1px solid #1f2b23;
    }
    [data-testid="stSidebar"] .sidebar-brand {
        font-size: 1.05rem; font-weight: 800; color: #f1f5f2; margin-bottom: 0.2rem;
    }
    [data-testid="stSidebar"] .sidebar-section-title {
        font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em;
        color: #6fbf8b; font-weight: 800; margin: 1.1rem 0 0.4rem 0;
    }
    [data-testid="stSidebar"] .stButton button {
        text-align: left; justify-content: flex-start;
    }

    /* ---------- Compact "Top Picks" list rows ---------- */
    .top-pick-row {
        display: flex; align-items: center; gap: 0.7rem; flex-wrap: wrap;
        background: #10201a; border: 1px solid rgba(0, 230, 118, 0.22);
        border-radius: 10px; padding: 0.55rem 0.9rem; margin-bottom: 0.5rem;
    }
    .top-pick-rank {
        width: 22px; height: 22px; border-radius: 50%; flex-shrink: 0;
        background: rgba(0, 230, 118, 0.18); color: #00e676; font-weight: 800; font-size: 0.78rem;
        display: flex; align-items: center; justify-content: center;
    }
    .top-pick-name { font-weight: 800; color: #f1f5f2; min-width: 130px; }
    .top-pick-price { color: #b7c0bb; font-size: 0.88rem; }
    .top-pick-target { color: #9aa5a1; font-size: 0.85rem; }
    .top-pick-horizon {
        margin-left: auto; color: #7b847f; font-size: 0.78rem;
        background: rgba(255,255,255,0.04); border-radius: 6px; padding: 0.15rem 0.5rem;
    }

    /* ---------- Compact analysed-stock quote line ---------- */
    .quick-quote-line {
        font-size: 1.15rem; margin: 0.4rem 0 0.8rem 0; color: #f1f5f2;
        display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap;
    }
    .quick-quote-price { font-weight: 800; font-size: 1.3rem; }

    .ai-summary-row {
        display: flex; align-items: center; gap: 1.1rem; flex-wrap: wrap;
        margin-bottom: 0.55rem; font-size: 0.95rem; color: #d7ddd9;
    }
    .tf-inline-row { gap: 0.9rem; }
    .tf-inline { display: inline-flex; align-items: center; gap: 0.35rem; font-size: 0.85rem; color: #b7c0bb; }
</style>
"""


def signal_badge_class(signal: str) -> str:
    """Maps a signal string (e.g. 'STRONG BUY') to its CSS badge class."""
    s = signal.upper().replace(" ", "").replace("_", "")
    if "STRONGBUY" in s:
        return "badge-strongbuy"
    if "BUY" in s:
        return "badge-buy"
    if "STRONGSELL" in s:
        return "badge-strongsell"
    if "SELL" in s:
        return "badge-sell"
    return "badge-hold"
