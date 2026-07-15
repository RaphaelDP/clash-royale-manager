"""
================================================================================
Filename: _05_wars.py
Description: Streamlit page for displaying clan war performance.
Author: Raphael Smilet
Date Created: 2026-07-03
Last Modified: 2026-07-10
Version: 0.6.0
Python Version: 3.12
Dependencies: streamlit, pandas, app.services.dashboard_service
================================================================================
"""

import streamlit as st
import pandas as pd

from app.core.config import settings
from app.database.session import get_session
from app.services.dashboard_service import DashboardService
from app.services.war_service import WarService

st.set_page_config(
    page_title="War Performance",
    layout="wide",
)

st.title("⚔️ War Performance")

with get_session() as db:
    dashboard_service = DashboardService(db)
    war_service = WarService(db)

    st.header("🔴 Live Race")

    live_status = dashboard_service.get_current_race_status()

    if live_status:
        st.info(
            f"Season {live_status['season_id']}, race #{live_status['section_index']} "
            "is currently in progress."
        )

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Have attacked", live_status["participated_count"])

        with col2:
            st.metric("Haven't attacked yet", live_status["not_participated_count"])

        if live_status["not_participated"]:
            st.warning("Members who haven't attacked yet:")
            st.dataframe(
                pd.DataFrame(live_status["not_participated"]),
                hide_index=True,
                width="stretch",
            )
    else:
        st.info("No river race currently in progress.")

    st.divider()

    seasons = dashboard_service.get_available_seasons()

    if not seasons:
        st.warning("No war seasons found.")
        st.stop()

    season_ids = [season.season_id for season in seasons]

    selected_season = st.selectbox(
        "Select Season",
        season_ids,
    )

    season_stats = dashboard_service.get_season_summary(selected_season)

    if not season_stats:
        st.warning("No statistics available for this season.")
        st.stop()

    st.header(f"Season {selected_season}")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Fame", season_stats.get("total_fame", 0))

    with col2:
        st.metric("Repair Points", season_stats.get("total_repairs", 0))

    with col3:
        st.metric("Decks Used", season_stats.get("total_decks", 0))

    with col4:
        st.metric("Participants", season_stats.get("participants", 0))

    st.divider()

    st.subheader("🏆 Top War Players")

    top_players = dashboard_service.get_war_player_ranking(
        season_id=selected_season,
        limit=10,
    )

    if top_players:
        players_df = pd.DataFrame(top_players)
        st.dataframe(players_df, width="stretch")
    else:
        st.info("No player statistics available.")

    st.divider()

    st.subheader("🏁 River Races")

    races = dashboard_service.get_river_races(selected_season)

    if races:
        races_df = pd.DataFrame(races)
        st.dataframe(races_df, width="stretch")
    else:
        st.info("No races found.")

    st.divider()

    st.subheader("📈 Race Comparison")

    comparison = dashboard_service.get_race_comparison(selected_season)

    if comparison:
        comparison_df = pd.DataFrame(comparison)

        st.bar_chart(comparison_df, x="section_index", y="avg_fame")

        st.dataframe(comparison_df, hide_index=True, width="stretch")

        st.caption(
            "Participation rate uses the CURRENT active member count as an "
            "approximation — historical roster size at race time isn't tracked."
        )
    else:
        st.info("No races to compare for this season.")

    st.divider()

    st.subheader("📊 Player War Details")

    selected_player = st.selectbox(
        "Select Player",
        [player["member_tag"] for player in top_players] if top_players else [],
        format_func=lambda tag: next(
            (p["name"] for p in top_players if p["member_tag"] == tag), tag
        ),
    )

    all_time = st.checkbox(
        "Show all-time stats (ignore season filter)",
        value=False,
    )

    if selected_player:
        player_war_stats = dashboard_service.get_player_war_stats(
            selected_player,
            season_id=None if all_time else selected_season,
        )

        if player_war_stats:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Fame", player_war_stats.get("fame", 0))

            with col2:
                st.metric("Repair", player_war_stats.get("repair_points", 0))

            with col3:
                st.metric("Boat Attacks", player_war_stats.get("boat_attacks", 0))

            with col4:
                st.metric("Decks Used", player_war_stats.get("decks_used", 0))

    st.divider()

    st.subheader("🔄 War Synchronisation")

    if st.button("Sync War Data"):
        try:
            war_service.sync_river_race_log(settings.CLAN_TAG)
            st.success("War data synchronized.")
            st.rerun()
        except Exception as error:
            st.error(f"War sync failed: {error}")
