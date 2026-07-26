"""Minimal username/password gate for the demo app.

This is intentionally simple (single shared demo account, credentials
readable in this file / secrets). It is NOT a real authentication system
and should never be used to protect anything beyond a sales/investor demo.
"""

from __future__ import annotations

import os

import streamlit as st

DEFAULT_USERNAME = "demo"
DEFAULT_PASSWORD = "stocksense2026"


def _get_credential(key: str, default: str) -> str:
    try:
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.environ.get(key, default)


def get_valid_credentials() -> tuple[str, str]:
    username = _get_credential("APP_USERNAME", DEFAULT_USERNAME)
    password = _get_credential("APP_PASSWORD", DEFAULT_PASSWORD)
    return username, password


def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated", False))


def log_out() -> None:
    st.session_state["authenticated"] = False
    st.session_state.pop("username", None)


def render_login_page() -> None:
    """Render the login screen. Sets st.session_state.authenticated=True on success."""

    st.markdown(
        """
        <div class="login-wrapper">
            <div class="login-card">
                <div class="login-logo">📈</div>
                <h1 class="login-title">StockSense <span>AI</span></h1>
                <p class="login-tagline">AI-Powered Stock Intelligence for Indian Markets</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, center, _ = st.columns([1, 1.1, 1])
    with center:
        with st.form("login_form", clear_on_submit=False):
            st.markdown("#### Sign in to your account")
            username = st.text_input("Username", placeholder="demo")
            password = st.text_input("Password", type="password", placeholder="••••••••••")
            submitted = st.form_submit_button("Log In", width="stretch", type="primary")

            if submitted:
                valid_user, valid_pass = get_valid_credentials()
                if username == valid_user and password == valid_pass:
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username
                    st.rerun()
                else:
                    st.error("Invalid username or password. Try the demo credentials below.")

        st.markdown(
            """
            <div class="login-hint">
                Demo credentials &nbsp;·&nbsp; Username: <code>demo</code>
                &nbsp;·&nbsp; Password: <code>stocksense2026</code>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="login-disclaimer">
                This is a demo. Not SEBI-registered investment advice.
            </div>
            """,
            unsafe_allow_html=True,
        )
