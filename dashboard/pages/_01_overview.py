"""
================================================================================
Filename: _01_overview.py
Description: Streamlit page for displaying clan overview and aggregated KPIs.
Author: Raphael Smilet
Date Created: 2026-07-03
Last Modified: 2026-07-10
Version: 0.6.0
Python Version: 3.12
Dependencies: streamlit, pandas, app.services.dashboard_service
================================================================================
"""

import pandas as pd
import streamlit as st

from app.core.utils import get_time, format_datetime
from app.database.session import get_session
from app.services.dashboard_service import DashboardService

st.set_page_config(
    page_title="Clan Overview",
    layout="wide",
)

st.title("📊 Clan Overview")


with get_session() as db:
    dashboard_service = DashboardService(db, api_clash=None)

    overview = dashboard_service.get_overview_stats()
    database = dashboard_service.get_database_stats()
    war = dashboard_service.get_war_stats()
    snapshots = dashboard_service.get_snapshot_stats()

    # ==========================================================================
    # Clan KPIs
    # ==========================================================================

    st.header("📈 Clan Statistics")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Members", overview["member_count"])

    with col2:
        st.metric("Active Members", overview["active_members"])

    with col3:
        st.metric("Average Trophies", overview["average_trophies"])

    with col4:
        st.metric("Total Donations", overview["total_donations"])

    with col5:
        st.metric("Average Promotion Score", overview["average_promotion_score"])

    # ==========================================================================
    # Clan Health Score
    # ==========================================================================

    st.header("🩺 Clan Health Score")

    health = dashboard_service.get_clan_health_score()

    col1, col2 = st.columns([1, 2])

    with col1:
        st.metric("Overall Health", f"{health['final_score']:.1f} / 100")

    with col2:
        components_df = pd.DataFrame(
            [
                {"Component": key.replace("_", " ").title(), "Score": value}
                for key, value in health["components"].items()
            ]
        )
        st.bar_chart(components_df, x="Component", y="Score")

    st.caption(
        "Leadership Depth is a fixed placeholder (100) until scoring thresholds "
        "are defined. Participation/Efficiency are scoped to the most recent race."
    )

    # ==========================================================================
    # Activity Ranking
    # ==========================================================================

    st.header("🏃 Activity Ranking")

    activity_ranking = dashboard_service.get_activity_ranking(limit=15)

    if activity_ranking:
        activity_df = pd.DataFrame(activity_ranking)
        st.dataframe(activity_df, hide_index=True, width="stretch")
    else:
        st.info("No active members to rank.")

    # ==========================================================================
    # Database status
    # ==========================================================================

    st.header("🗄️ Database Overview")

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.metric("Members", database["members"])

    with col2:
        st.metric("Snapshots", database["snapshots"])

    with col3:
        st.metric("Promotion Scores", database["promotion_scores"])

    with col4:
        st.metric("War Seasons", database["war_seasons"])

    with col5:
        st.metric("River Races", database["river_races"])

    with col6:
        st.metric("War Participations", database["participations"])

    # ==========================================================================
    # Activity trends
    # ==========================================================================

    st.header("📉 Activity Trends")

    snapshot_history = dashboard_service.get_daily_snapshot_history()

    if snapshot_history:
        snapshot_df = pd.DataFrame(snapshot_history)

        snapshot_df["date"] = pd.to_datetime(snapshot_df["date"])

        st.line_chart(
            snapshot_df,
            x="date",
            y=[
                "avg_trophies",
                "avg_donations",
            ],
        )
    else:
        st.warning("No snapshot history available.")

    # ==========================================================================
    # Role distribution
    # ==========================================================================

    st.header("👥 Role Distribution")

    roles = dashboard_service.get_role_distribution()

    if roles:
        roles_df = pd.DataFrame(roles)

        st.bar_chart(
            roles_df,
            x="role",
            y="count",
        )
    else:
        st.warning("No role data available.")

    # ==========================================================================
    # War summary
    # ==========================================================================

    st.header("⚔️ War Summary")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "Seasons",
            war["season_count"],
        )

    with col2:
        st.metric(
            "Races",
            war["race_count"],
        )

    with col3:
        st.metric(
            "Total Fame",
            war["total_fame"],
        )

    with col4:
        st.metric(
            "Repair Points",
            war["total_repair_points"],
        )

    with col5:
        st.metric(
            "Decks Used",
            war["total_decks_used"],
        )

    # ==========================================================================
    # Top players
    # ==========================================================================

    st.header("🏆 Top Players")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Highest Trophies")

        top_trophies = dashboard_service.get_top_members_by_trophies()

        if top_trophies:
            trophies_df = pd.DataFrame(
                [
                    {
                        "Player": member.name,
                        "Tag": member.tag,
                        "Trophies": member.trophies,
                    }
                    for member in top_trophies
                ]
            )

            st.dataframe(
                trophies_df,
                width="stretch",
            )

    with col2:
        st.subheader("Highest Donations")

        top_donations = dashboard_service.get_top_members_by_donations()

        if top_donations:
            donations_df = pd.DataFrame(
                [
                    {
                        "Player": member.name,
                        "Tag": member.tag,
                        "Donations": member.donations,
                    }
                    for member in top_donations
                ]
            )

            st.dataframe(
                donations_df,
                width="stretch",
            )

    # ==========================================================================
    # Top War Performers
    # ==========================================================================

    st.header("⚔️ Top War Performers")

    top_war_players = dashboard_service.get_top_war_players()

    if top_war_players:
        war_players_df = pd.DataFrame(
            [
                {
                    "Player": player.name,
                    "Tag": player.tag,
                    "Fame": player.fame,
                    "Repair Points": player.repair,
                    "Boat Attacks": player.boats,
                    "Decks Used": player.decks,
                }
                for player in top_war_players
            ]
        )

        st.dataframe(
            war_players_df,
            width="stretch",
        )
    else:
        st.warning("No war participation data available.")

    # ==========================================================================
    # Latest database activity
    # ==========================================================================

    st.header("🕒 Data Freshness")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Latest Snapshot",
            format_datetime(snapshots["latest_snapshot"]),
        )

    with col2:
        st.metric(
            "Oldest Snapshot",
            format_datetime(snapshots["oldest_snapshot"]),
        )

    with col3:
        if snapshots["latest_snapshot"]:
            days_since_update = (get_time() - snapshots["latest_snapshot"]).days

            st.metric(
                "Days Since Update",
                days_since_update,
            )
        else:
            st.metric(
                "Days Since Update",
                "-",
            )
