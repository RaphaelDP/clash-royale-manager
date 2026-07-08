"""
================================================================================
Filename: _05_wars.py
Description: Streamlit page for displaying clan war performance.
Author: Raphael Smilet
Date Created: 2026-07-03
Last Modified: 2026-07-08
Version: 0.5.0
Python Version: 3.12
Dependencies: streamlit, pandas, app.services.dashboard_service
================================================================================
"""

import streamlit as st
import pandas as pd

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

    seasons = dashboard_service.get_available_war_seasons()

    if not seasons:
        st.warning("No war seasons found.")
        st.stop()

    selected_season = st.selectbox(
        "Select Season",
        seasons,
    )

    season_stats = dashboard_service.get_war_season_stats(
        selected_season
    )

    if not season_stats:
        st.warning("No statistics available for this season.")
        st.stop()

    st.header(f"Season {selected_season}")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Fame",
            season_stats.get("total_fame", 0),
        )

    with col2:
        st.metric(
            "Repair Points",
            season_stats.get("total_repair_points", 0),
        )

    with col3:
        st.metric(
            "Decks Used",
            season_stats.get("total_decks_used", 0),
        )

    with col4:
        st.metric(
            "Participants",
            season_stats.get("participants", 0),
        )

    st.divider()

    st.subheader("🏆 Top War Players")

    top_players = dashboard_service.get_war_player_ranking(
        season_id=selected_season,
        limit=10,
    )

    if top_players:
        players_df = pd.DataFrame(
            top_players
        )

        st.dataframe(
            players_df,
            width="stretch",
        )
    else:
        st.info("No player statistics available.")

    st.divider()

    st.subheader("🏁 River Races")

    races = dashboard_service.get_river_races(
        selected_season
    )

    if races:
        races_df = pd.DataFrame(races)

        st.dataframe(
            races_df,
            width="stretch",
        )
    else:
        st.info("No races found.")

    st.divider()

    st.subheader("📊 Player War Details")

    selected_player = st.selectbox(
        "Select Player",
        [
            player["member_tag"]
            for player in top_players
        ]
        if top_players
        else [],
    )

    if selected_player:
        player_war_stats = dashboard_service.get_player_war_stats(
            selected_player
        )

        if player_war_stats:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Fame",
                    player_war_stats.get("fame", 0),
                )

            with col2:
                st.metric(
                    "Repair",
                    player_war_stats.get("repair_points", 0),
                )

            with col3:
                st.metric(
                    "Boat Attacks",
                    player_war_stats.get("boat_attacks", 0),
                )

            with col4:
                st.metric(
                    "Decks Used",
                    player_war_stats.get("decks_used", 0),
                )

    st.divider()

    st.subheader("🔄 War Synchronisation")

    if st.button("Sync War Data"):
        try:
            war_service.sync_river_race_log()
            st.success("War data synchronized.")
            st.rerun()
        except Exception as error:
            st.error(
                f"War sync failed: {error}"
            )