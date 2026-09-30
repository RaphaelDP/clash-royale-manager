"""
================================================================================
Filename: _02_members.py
Description: Streamlit page for displaying clan members and aggregated member statistics.
Author: Raphael Smilet
Date Created: 2026-07-03
Last Modified: 2026-09-30
Version: 0.5.2
Python Version: 3.12
Dependencies: streamlit, dashboard.functions
================================================================================
"""

import streamlit as st

from dashboard.functions import (
    dashboard_action_running,
    execute_dashboard_action,
    get_member_filter_options,
    get_members_page_data,
    refresh_clan_members_data,
)

st.set_page_config(
    page_title="Clan Members",
    layout="wide",
)

st.title("👥 Clan Members")


filter_options = get_member_filter_options()
if not filter_options["has_members"]:
    st.warning("No members found in database.")
    st.stop()

# ==========================================================================
# Filters
# ==========================================================================

st.sidebar.header("🔎 Filters")

selected_roles = st.sidebar.multiselect(
    "Role",
    options=filter_options["roles"],
    default=filter_options["roles"],
)

min_trophies = st.sidebar.slider(
    "Minimum Trophies",
    min_value=0,
    max_value=filter_options["trophy_slider_max"],
    value=0,
)

min_donations = st.sidebar.slider(
    "Minimum Donations",
    min_value=0,
    max_value=filter_options["donation_slider_max"],
    value=0,
)

has_contribution_score = st.sidebar.checkbox(
    "Only members with contribution score",
    value=False,
)

# ==========================================================================
# Filtering
# ==========================================================================

data = get_members_page_data(
    roles=selected_roles,
    min_trophies=min_trophies,
    min_donations=min_donations,
    has_contribution_score=has_contribution_score,
)

# ==========================================================================
# Summary
# ==========================================================================

st.header("📊 Member Summary")

st.button(
    "🔄 Refresh Clash Royale profile",
    on_click=execute_dashboard_action,
    args=(refresh_clan_members_data, "Refreshing clan members..."),
    disabled=dashboard_action_running(),
)

summary = data["summary"]
col1, col2, col3, col4 = st.columns(4)
for column, label, key in zip(
    (col1, col2, col3, col4),
    ("Displayed Members", "Average Trophies", "Total Donations", "Average Score"),
    (
        "displayed_members",
        "average_trophies",
        "total_donations",
        "average_score",
    ),  # =label.case().replace(" ", "_"),
):
    with column:
        st.metric(label, summary[key])

# ==========================================================================
# Member table
# ==========================================================================

st.header("👥 Members")

st.dataframe(data["members_df"], width="stretch")

# ==========================================================================
# Rankings
# ==========================================================================

st.header("🏆 Rankings")

col1, col2, col3 = st.columns(3)
for column, title, key in (
    (col1, "Trophies", "trophies_df"),
    (col2, "Donations", "donations_df"),
    (col3, "Contribution Score", "contribution_df"),
):
    with column:
        st.subheader(title)
        st.dataframe(data[key], width="stretch")


# ==========================================================================
# Role distribution
# ==========================================================================

st.header("📌 Role Distribution")

role_df = data["role_distribution"]
if not role_df.empty:
    st.bar_chart(role_df, x="role", y="count")
