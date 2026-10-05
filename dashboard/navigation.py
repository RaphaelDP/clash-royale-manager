"""
================================================================================
Filename: navigation.py
Description: Explicit navigation and page-scoped rendering for the dashboard.
Author: Raphael Smilet
Date Created: 2026-10-06
Last Modified: 2026-10-06
Version: 0.1.0
Python Version: 3.12
================================================================================
"""

import streamlit as st

from dashboard.controls import render_close_button

st.set_page_config(page_title="Clash Royale Manager", page_icon="🏆", layout="wide")
page = st.navigation(
    [
        st.Page("home.py", title="Home", default=True),
        st.Page("pages/_01_overview.py", title="Overview", url_path="01_overview"),
        st.Page("pages/_02_members.py", title="Members", url_path="02_members"),
        st.Page("pages/_03_player.py", title="Player", url_path="03_player"),
        st.Page(
            "pages/_04_promotions.py", title="Promotions", url_path="04_promotions"
        ),
        st.Page("pages/_05_wars.py", title="Wars", url_path="05_wars"),
        st.Page("pages/_06_settings.py", title="Settings", url_path="06_settings"),
    ]
)
with st.sidebar:
    render_close_button()
# Give each page a distinct root rather than reconciling long and short page trees.
with st.container(key=f"page_{page.url_path or 'home'}"):
    page.run()
