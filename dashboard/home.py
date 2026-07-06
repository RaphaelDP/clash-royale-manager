"""
================================================================================
Filename: home.py
Description: Main Streamlit dashboard page for the Clan Manager.
Author: Raphael Smilet
Date Created: 2026-07-03
Last Modified: 2026-07-03
Version: 0.5.0
Python Version: 3.12
Dependencies: streamlit
================================================================================
"""

import streamlit as st

st.set_page_config(
    page_title="Clash Royale Manager",
    page_icon="🏆",
    layout="wide",
)

st.title("🏆 Clash Royale Clan Manager")
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
