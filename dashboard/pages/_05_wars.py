"""
================================================================================
Filename: _05_wars.py
Description: Streamlit page for displaying clan war performance.
Author: Raphael Smilet
Date Created: 2026-07-03
Last Modified: 2026-10-06
Version: 0.6.3
Python Version: 3.12
Dependencies: streamlit, dashboard.functions
================================================================================
"""

import streamlit as st

from dashboard.functions import (
    dashboard_action_running,
    execute_dashboard_action,
    get_war_overview_data,
    get_war_season_data,
    get_player_war_stats_data,
    refresh_war_data,
)

st.set_page_config(page_title="War Performance", layout="wide")
st.title("⚔️ War Performance")
st.button(
    "Sync War Data",
    on_click=execute_dashboard_action,
    args=(refresh_war_data, "Synchronizing war data..."),
    disabled=dashboard_action_running(),
)

overview = get_war_overview_data()
live = overview["live_status"]
st.header("Current war phase")
if live and live.get("phase") == "training":
    day = live["training_day"]
    st.info(f"Training days — day {day} of 3" if day else "Training days")
    st.caption(
        "Training is optional. Decks, fame and participation during this phase are excluded from war statistics."
    )
    st.caption(
        f"Last synchronized: {live['observed_at']}. Sync War Data to update the phase."
    )
elif live:
    st.info(
        f"Season {live['season_id']}, race #{live['section_index'] + 1} is currently in progress."
    )
    left, right = st.columns(2)
    with left:
        st.metric("Have attacked", live["participated_count"])
    with right:
        st.metric("Haven't attacked yet", live["not_participated_count"])
    if not overview["not_participated"].empty:
        st.warning("Members who haven't attacked yet:")
        st.dataframe(overview["not_participated"], hide_index=True, width="stretch")
else:
    st.info("No river race currently in progress.")

st.divider()
if not overview["season_ids"]:
    st.warning("No war seasons found.")
    st.stop()
selected_season = st.selectbox("Select Season", overview["season_ids"])
limit = st.slider(
    "Number of top players to display", min_value=1, max_value=50, value=10
)
data = get_war_season_data(selected_season, limit)
st.header(f"Season {selected_season}")
for column, label, key in zip(
    st.columns(4),
    ("Total Fame", "Repair Points", "Decks Used", "Participants"),
    ("total_fame", "total_repairs", "total_decks", "participants"),
):
    with column:
        st.metric(label, data["summary"][key])

st.divider()
st.subheader("🏆 Top War Players")
if not data["top_players"].empty:
    st.dataframe(data["top_players"], width="stretch")
else:
    st.info("No player statistics available.")

st.divider()
st.subheader("🏁 River Races")
if not data["races"].empty:
    st.dataframe(data["races"], width="stretch")
else:
    st.info("No races found.")

st.divider()
st.subheader("📈 Race Comparison")
if not data["comparison"].empty:
    st.bar_chart(data["comparison"], x="section_index", y="avg_fame")
    st.dataframe(data["comparison"], hide_index=True, width="stretch")
    st.caption(
        "Participation rate uses the CURRENT active member count as an approximation — "
        "historical roster size at race time isn't tracked."
    )
else:
    st.info("No races to compare for this season.")

st.divider()
st.subheader("📊 Player War Details")
players = data["player_options"]
selected_player = st.selectbox("Select Player", players, format_func=players.get)
all_time = st.checkbox("Show all-time stats (ignore season filter)", value=False)
if selected_player:
    stats = get_player_war_stats_data(selected_player, selected_season, all_time)
    if stats:
        for column, label, key in zip(
            st.columns(4),
            ("Fame", "Repair", "Boat Attacks", "Decks Used"),
            ("fame", "repair_points", "boat_attacks", "decks_used"),
        ):
            with column:
                st.metric(label, stats[key])
