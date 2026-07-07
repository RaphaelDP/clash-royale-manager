"""
================================================================================
Filename: 05_settings.py
Description: Streamlit page for configuring dashboard settings.
Author: Raphael Smilet
Date Created: 2026-07-03
Last Modified: 2026-07-03
Version: 0.5.0
Python Version: 3.12
Dependencies: streamlit, app.core.config
================================================================================
"""

import streamlit as st
from app.core.config import settings

st.set_page_config(page_title="Settings", layout="wide")
st.title("⚙️ Settings")

st.header("Dashboard Configuration")
st.write("Configure your dashboard settings here.")

# --- API Settings ---
st.subheader("Clash Royale API")
api_token = st.text_input(
    "API Token",
    type="password",
    value=settings.CR_API_TOKEN or "",
    help="Your Clash Royale API token. Get it from the Clash Royale Developer Portal.",
)
if api_token:
    st.success("API token configured.")

clan_tag = st.text_input(
    "Clan Tag",
    value=settings.CLAN_TAG or "",
    help="Your clan tag (e.g., #Q8YG902J).",
)
if clan_tag:
    st.success("Clan tag configured.")

# --- Database Settings ---
st.subheader("Database")
db_url = st.text_input(
    "Database URL",
    value=settings.DATABASE_URL or "sqlite:///data/clan_manager.db",
    help="Database connection URL (e.g., sqlite:///data/clan_manager.db).",
)
if db_url:
    st.success("Database URL configured.")

# --- Logging Settings ---
st.subheader("Logging")
log_level = st.selectbox(
    "Log Level",
    options=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    index=(
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"].index(settings.LOG_LEVEL)
        if settings.LOG_LEVEL
        else 1
    ),
    help="Set the logging level for the application.",
)
if log_level:
    st.success(f"Log level set to {log_level}.")

# --- Save Settings ---
if st.button("Save Settings"):
    st.success(
        "Settings saved! (Note: This is a demo. Actual saving requires backend integration.)"
    )
