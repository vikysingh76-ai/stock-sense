"""Shared custom CSS for the light / corporate "StockSense AI" theme.

Palette:
- App background:      #F4F6F8 (cool light gray)
- Card/surface:        #FFFFFF, bordered with #E2E8F0
- Text:                #1E293B (primary), #64748B (secondary)
- Brand/interactive:   #123C63 (navy) / #2563EB (corporate blue)
- Signal colors:       green #15803D / red #B91C1C / amber #B45309,
                       each on a soft tinted background for a clean,
                       "tag"-style look rather than neon-on-dark.
"""

CUSTOM_CSS = """
<style>
    #MainMenu, footer {visibility: hidden;}

    .stApp {
        background: radial-gradient(circle at top left, #eef3f8 0%, #f4f6f8 55%) fixed;
    }

    /* ---------- Login page ---------- */
    .login-wrapper { display: flex; justify-content: center; margin-top: 2rem; }
    .login-card { text-align: center; max-width: 520px; }
    .login-logo {
        font-size: 3.2rem; line-height: 1;
        width: 84px; height: 84px; margin: 0 auto 0.75rem auto;
        display: flex; align-items: center; justify-content: center;
        background: linear-gradient(135deg, #123c63, #2563eb);
        border-radius: 20px;
        box-shadow: 0 8px 24px rgba(37, 99, 235, 0.25);
    }
    .login-title { font-size: 2.1rem; font-weight: 800; margin-bottom: 0.15rem; color: #1e293b; }
    .login-title span { color: #2563eb; }
    .login-tagline { color: #64748b; font-size: 1.02rem; margin-bottom: 1.6rem; }
    .login-hint {
        text-align: center; font-size: 0.85rem; color: #475569; margin-top: 0.9rem;
        background: #eff6ff; border: 1px solid #bfdbfe;
        border-radius: 8px; padding: 0.6rem 0.8rem;
    }
    .login-disclaimer {
        text-align: center; font-size: 0.78rem; color: #94a3b8; margin-top: 1.4rem;
        font-style: italic;
    }

    /* ---------- Header ---------- */
    .app-header {
        display: flex; justify-content: space-between; align-items: center;
        flex-wrap: wrap; gap: 0.75rem;
        padding: 0.9rem 1.3rem; margin-bottom: 1.1rem;
        background: #ffffff;
        border: 1px solid #e2e8f0; border-radius: 14px;
    }
    .app-brand { display: flex; align-items: center; gap: 0.6rem; }
    .app-brand-badge {
        font-size: 1.4rem; width: 42px; height: 42px; border-radius: 10px;
        background: linear-gradient(135deg, #123c63, #2563eb);
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 6px 16px rgba(37, 99, 235, 0.25);
    }
    .app-brand-text { font-size: 1.25rem; font-weight: 800; color: #1e293b; }
    .app-brand-text span { color: #2563eb; }
    .app-datetime { text-align: right; font-size: 0.85rem; color: #64748b; }
    .app-datetime b { color: #1e293b; }

    .index-card {
        background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 0.9rem 1.1rem; text-align: left;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .index-card .idx-name { font-size: 0.82rem; color: #64748b; font-weight: 600; letter-spacing: 0.02em; }
    .index-card .idx-value { font-size: 1.55rem; font-weight: 800; color: #1e293b; margin: 0.15rem 0; }
    .idx-up { color: #15803d; font-weight: 700; }
    .idx-down { color: #b91c1c; font-weight: 700; }

    .market-pill {
        display: inline-flex; align-items: center; gap: 0.4rem;
        padding: 0.32rem 0.8rem; border-radius: 999px; font-weight: 700; font-size: 0.82rem;
    }
    .market-open { background: #dcfce7; color: #15803d; border: 1px solid #86efac; }
    .market-closed { background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }
    .dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; display: inline-block; }

    /* ---------- Top AI picks ---------- */
    .picks-banner {
        background: #ffffff;
        border: 1px solid #e2e8f0; border-left: 4px solid #2563eb;
        border-radius: 12px; padding: 1.1rem 1.3rem 1.3rem 1.3rem; margin-bottom: 1.4rem;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
    }
    .picks-banner h3 { margin: 0 0 0.9rem 0; color: #123c63; font-weight: 800; }
    .pick-card {
        background: #f8fafc; border: 1px solid #e2e8f0;
        border-radius: 12px; padding: 0.95rem 1.05rem; height: 100%;
    }
    .pick-stock { font-weight: 800; font-size: 1.05rem; color: #1e293b; }
    .pick-signal {
        display: inline-block; margin: 0.35rem 0 0.6rem 0; padding: 0.2rem 0.6rem;
        border-radius: 6px; font-size: 0.74rem; font-weight: 800; letter-spacing: 0.03em;
        background: #dcfce7; color: #15803d;
    }
    .pick-row { display: flex; justify-content: space-between; font-size: 0.85rem; color: #475569; padding: 0.12rem 0; }
    .pick-row b { color: #1e293b; }
    .pick-return { color: #15803d; font-weight: 800; }

    /* ---------- Section headers ---------- */
    .section-title {
        font-size: 1.15rem; font-weight: 800; color: #1e293b;
        margin: 1.6rem 0 0.8rem 0; padding-bottom: 0.4rem;
        border-bottom: 2px solid #2563eb;
    }

    .stat-box {
        background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px;
        padding: 0.75rem 0.9rem; text-align: center;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .stat-box .stat-label { font-size: 0.75rem; color: #64748b; }
    .stat-box .stat-value { font-size: 1.15rem; font-weight: 800; color: #1e293b; }

    .rec-card {
        background: #ffffff; border: 1px solid #e2e8f0; border-radius: 14px;
        padding: 1.1rem 1.3rem; margin-top: 0.6rem;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
    }
    .badge-buy, .badge-strongbuy { background: #dcfce7; color: #15803d; }
    .badge-sell, .badge-strongsell { background: #fee2e2; color: #b91c1c; }
    .badge-hold { background: #fef3c7; color: #b45309; }
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
        border-top: 1px solid #e2e8f0; color: #94a3b8; font-size: 0.82rem;
    }
    .app-footer .disclaimer { color: #b45309; font-weight: 600; margin-bottom: 0.25rem; }

    .accuracy-hero {
        display: flex; align-items: center; gap: 1rem;
        background: #ffffff;
        border: 1px solid #e2e8f0; border-left: 4px solid #15803d;
        border-radius: 12px; padding: 1rem 1.2rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
    }
    .accuracy-hero .big-num { font-size: 2.3rem; font-weight: 900; color: #15803d; }

    /* ---------- Sidebar control panel ---------- */
    [data-testid="stSidebar"] {
        background: #ffffff; border-right: 1px solid #e2e8f0;
    }
    [data-testid="stSidebar"] .sidebar-brand {
        font-size: 1.05rem; font-weight: 800; color: #123c63; margin-bottom: 0.2rem;
    }
    [data-testid="stSidebar"] .sidebar-section-title {
        font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em;
        color: #2563eb; font-weight: 800; margin: 1.1rem 0 0.4rem 0;
    }
    [data-testid="stSidebar"] .stButton button {
        text-align: left; justify-content: flex-start;
    }

    /* ---------- Compact "Top Picks" list rows ---------- */
    .top-pick-row {
        display: flex; align-items: center; gap: 0.7rem; flex-wrap: wrap;
        background: #f8fafc; border: 1px solid #e2e8f0;
        border-radius: 10px; padding: 0.55rem 0.9rem; margin-bottom: 0.5rem;
    }
    .top-pick-rank {
        width: 22px; height: 22px; border-radius: 50%; flex-shrink: 0;
        background: #dbeafe; color: #123c63; font-weight: 800; font-size: 0.78rem;
        display: flex; align-items: center; justify-content: center;
    }
    .top-pick-name { font-weight: 800; color: #1e293b; min-width: 130px; }
    .top-pick-price { color: #475569; font-size: 0.88rem; }
    .top-pick-target { color: #64748b; font-size: 0.85rem; }
    .top-pick-horizon {
        margin-left: auto; color: #64748b; font-size: 0.78rem;
        background: #eef2f6; border-radius: 6px; padding: 0.15rem 0.5rem;
    }

    /* ---------- Compact analysed-stock quote line ---------- */
    .quick-quote-line {
        font-size: 1.15rem; margin: 0.4rem 0 0.8rem 0; color: #1e293b;
        display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap;
    }
    .quick-quote-price { font-weight: 800; font-size: 1.3rem; }

    .ai-summary-row {
        display: flex; align-items: center; gap: 1.1rem; flex-wrap: wrap;
        margin-bottom: 0.55rem; font-size: 0.95rem; color: #334155;
    }
    .tf-inline-row { gap: 0.9rem; }
    .tf-inline { display: inline-flex; align-items: center; gap: 0.35rem; font-size: 0.85rem; color: #475569; }
</style>
"""


def signal_badge_class(signal: str) -> str:
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
