"""
================================================================================
Filename: home.py
Description: Main Streamlit dashboard page for the Clan Manager.
Author: Raphael Smilet
Date Created: 2026-07-03
Last Modified: 2026-09-30
Version: 0.5.2
Python Version: 3.12
Dependencies: streamlit, dashboard.functions
================================================================================
"""

import streamlit as st

from dashboard.functions import get_home_page_data

st.set_page_config(
    page_title="Clash Royale Manager",
    page_icon="🏆",
    layout="wide",
)

st.title("🏆 Clash Royale Clan Manager")

missing_config = get_home_page_data()["missing_config"]
if missing_config:
    st.error("⚠️ Missing configuration")

    st.write("The following values are missing from your .env file:")

    for item in missing_config:
        st.write(f"- `{item}`")

    st.info("Fill these values in .env, then restart the application.")

    st.stop()

st.markdown("""
    Welcome to the **Clan Manager Dashboard**!
    Use the sidebar to navigate to different sections.
    ### Features:
    - 📊 **Overview**: Clan statistics and trends.
    - 👥 **Members**: Member details and activity.
    - ⚔️ **Wars**: War performance and participation.
    - 📈 **Promotions**: Promotion and kick candidates.
    - ⚙️ **Settings**: Configure your dashboard.
""")
