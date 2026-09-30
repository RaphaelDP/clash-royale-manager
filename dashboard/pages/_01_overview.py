"""
================================================================================
Filename: _01_overview.py
Description: Streamlit page for displaying clan overview and aggregated KPIs.
Author: Raphael Smilet
Date Created: 2026-07-03
Last Modified: 2026-09-30
Version: 0.6.2
Python Version: 3.12
Dependencies: streamlit, dashboard.functions
================================================================================
"""

import streamlit as st

from dashboard.functions import (
    dashboard_action_running,
    execute_dashboard_action,
    get_overview_page_data,
    recalculate_scores,
    refresh_clan_members_data,
    refresh_war_data,
)

st.set_page_config(page_title="Clan Overview", layout="wide")
st.title("📊 Clan Overview")

data = get_overview_page_data()

if data["sync_warning"]:
    st.warning(data["sync_warning"])

# Refresh Data
st.header("🔄 Refresh Data")
st.info(
    "Click the buttons below to manually refresh clan members, war data, "
    "or recalculate contribution scores. This will fetch the latest data "
    "from the Clash Royale API and update the database."
)

running = dashboard_action_running()
refresh_buttons = [
    (
        "Refresh Clan Members",
        refresh_clan_members_data,
        "⏳ Refreshing clan members...",
    ),
    ("Refresh War Data", refresh_war_data, "⏳ Refreshing war data..."),
    (
        "Recalculate Contribution Scores",
        recalculate_scores,
        "⏳ Recalculating scores...",
    ),
]
for label, action, message in refresh_buttons:
    st.button(
        label,
        on_click=execute_dashboard_action,
        args=(action, message),
        disabled=running,
    )

# ==========================================================================
# Clan KPIs
# ==========================================================================

st.header("📈 Clan Statistics")
col1, col2, col3, col4, col5, col6 = st.columns(6)
overview = data["overview"]
for column, label, key in zip(
    (col1, col2, col3, col4, col5, col6),
    (
        "Overall Members",
        "Active Members",
        "Actual Members",
        "Average Trophies",
        "Total Donations",
        "Average Promotion Score",
    ),
    (
        "overall_members",
        "active_members",
        "actual_members",
        "average_trophies",
        "total_donations",
        "average_promotion_score",
    ),
):
    with column:
        st.metric(label, overview[key])

# ==========================================================================
# Clan Health
# ==========================================================================

st.header("🩺 Clan Health Score")
health = data["health"]
col1, col2 = st.columns([1, 2])
with col1:
    st.metric("Overall Health", f"{health['final_score']:.1f} / 100")
with col2:
    st.bar_chart(data["health_components"], x="Component", y="Score")
st.caption(
    "Leadership Depth is a fixed placeholder (100) until scoring thresholds "
    "are defined. Participation/Efficiency are scoped to the most recent race."
)

# ==========================================================================
# Activity Ranking
# ==========================================================================

st.header("😴 Inactivity Ranking")
if not data["activity"].empty:
    st.dataframe(data["activity"], hide_index=True, width="stretch")
else:
    st.info("No active members to rank.")

# ==========================================================================
# Database status
# ==========================================================================

database = data["database"]
st.header("🗄️ Database Overview")
col1, col2, col3, col4, col5, col6 = st.columns(6)
for column, label, key in zip(
    (col1, col2, col3, col4, col5, col6),
    (
        "Members",
        "Snapshots",
        "Promotion Scores",
        "War Seasons",
        "River Races",
        "War Participations",
    ),
    (
        "members",
        "snapshots",
        "promotion_scores",
        "war_seasons",
        "river_races",
        "participations",
    ),
):
    with column:
        st.metric(label, database[key])

# ==========================================================================
# Activity trends
# ==========================================================================

st.header("📉 Activity Trends")
if not data["snapshot_history"].empty:
    st.line_chart(
        data["snapshot_history"], x="date", y=["avg_trophies", "avg_donations"]
    )
else:
    st.warning("No snapshot history available.")

# ==========================================================================
# Role distribution
# ==========================================================================

st.header("👥 Role Distribution")
if not data["roles"].empty:
    st.bar_chart(data["roles"], x="role", y="count")
else:
    st.warning("No role data available.")

# ==========================================================================
# War summary
# ==========================================================================

war = data["war"]
st.header("⚔️ War Summary")
col1, col2, col3, col4, col5 = st.columns(5)
for column, label, key in zip(
    (col1, col2, col3, col4, col5),
    ("Seasons", "Races", "Total Fame", "Repair Points", "Decks Used"),
    (
        "season_count",
        "race_count",
        "total_fame",
        "total_repair_points",
        "total_decks_used",
    ),
):
    with column:
        st.metric(label, war[key])

# ==========================================================================
# Top players
# ==========================================================================

st.header("🏆 Top Players")
col1, col2 = st.columns(2)
with col1:
    st.subheader("Highest Trophies")
    if not data["top_trophies"].empty:
        st.dataframe(data["top_trophies"], width="stretch")
with col2:
    st.subheader("Highest Donations")
    if not data["top_donations"].empty:
        st.dataframe(data["top_donations"], width="stretch")

# ==========================================================================
# Top war performers
# ==========================================================================

st.header("⚔️ Top War Performers")
if not data["top_war_players"].empty:
    st.dataframe(data["top_war_players"], width="stretch")
else:
    st.warning("No war participation data available.")

# ==========================================================================
# Data freshness
# ==========================================================================

st.header("🕒 Data Freshness")
snapshots = data["snapshots"]
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Latest Snapshot", snapshots["latest_display"])
with col2:
    st.metric("Oldest Snapshot", snapshots["oldest_display"])
with col3:
    st.metric("Days Since Update", snapshots["days_since_update"])
