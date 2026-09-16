"""
================================================================================
Filename: _02_members.py
Description: Streamlit page for displaying clan members and aggregated member statistics.
Author: Raphael Smilet
Date Created: 2026-07-03
Last Modified: 2026-07-07
Version: 0.5.0
Python Version: 3.12
Dependencies: streamlit, pandas, app.database.session, app.database.models
================================================================================
"""

import pandas as pd
import streamlit as st

from app.database.session import get_session
from app.services.dashboard_service import DashboardService
from app.scheduler.jobs import update_clan_members

st.set_page_config(
    page_title="Clan Members",
    layout="wide",
)

st.title("👥 Clan Members")


with get_session() as db:
    dashboard_service = DashboardService(db)

    filter_options = dashboard_service.get_member_filter_options()

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
        max_value=filter_options["max_trophies"],
        value=0,
    )

    min_donations = st.sidebar.slider(
        "Minimum Donations",
        min_value=0,
        max_value=filter_options["max_donations"],
        value=0,
    )

    has_contribution_score = st.sidebar.checkbox(
        "Only members with contribution score",
        value=False,
    )

    # ==========================================================================
    # Filtering
    # ==========================================================================

    filtered_members = dashboard_service.get_filtered_members(
        roles=selected_roles,
        min_trophies=min_trophies,
        min_donations=min_donations,
        has_contribution_score=has_contribution_score,
    )

    # ==========================================================================
    # Summary
    # ==========================================================================

    st.header("📊 Member Summary")

    refresh = st.button("🔄 Refresh Clash Royale profile", on_click=lambda: update_clan_members(db_session=db))

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Displayed Members",
            len(filtered_members),
        )

    with col2:
        st.metric(
            "Average Trophies",
            (
                round(
                    sum(member.trophies for member in filtered_members)
                    / len(filtered_members)
                )
                if filtered_members
                else 0
            ),
        )

    with col3:
        st.metric(
            "Total Donations",
            sum(member.donations for member in filtered_members),
        )

    with col4:
        scores = [
            member.contribution_score
            for member in filtered_members
            if member.contribution_score is not None
        ]

        st.metric(
            "Average Score",
            (
                round(
                    sum(scores) / len(scores),
                    2,
                )
                if scores
                else 0
            ),
        )

    # ==========================================================================
    # Member table
    # ==========================================================================

    st.header("👥 Members")

    members_df = pd.DataFrame(
        [
            {
                "Tag": member.tag,
                "Name": member.name,
                "Role": member.role,
                "Trophies": member.trophies,
                "Donations": member.donations,
                "Last Seen": member.last_seen,
                "Contribution Score": member.contribution_score,
                "Score Updated": member.contribution_score_updated_at,
            }
            for member in filtered_members
        ]
    )

    st.dataframe(
        members_df,
        width="stretch",
    )

    # ==========================================================================
    # Rankings
    # ==========================================================================

    st.header("🏆 Rankings")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Trophies")

        trophies_df = pd.DataFrame(
            [
                {
                    "Player": member.name,
                    "Trophies": member.trophies,
                }
                for member in sorted(
                    filtered_members,
                    key=lambda x: x.trophies,
                    reverse=True,
                )[:10]
            ]
        )

        st.dataframe(
            trophies_df,
            width="stretch",
        )

    with col2:
        st.subheader("Donations")

        donations_df = pd.DataFrame(
            [
                {
                    "Player": member.name,
                    "Donations": member.donations,
                }
                for member in sorted(
                    filtered_members,
                    key=lambda x: x.donations,
                    reverse=True,
                )[:10]
            ]
        )

        st.dataframe(
            donations_df,
            width="stretch",
        )

    with col3:
        st.subheader("Contribution Score")

        contribution_df = pd.DataFrame(
            [
                {
                    "Player": member.name,
                    "Score": member.contribution_score,
                }
                for member in sorted(
                    [
                        member
                        for member in filtered_members
                        if member.contribution_score is not None
                    ],
                    key=lambda x: x.contribution_score,
                    reverse=True,
                )[:10]
            ]
        )

        st.dataframe(
            contribution_df,
            width="stretch",
        )

    # ==========================================================================
    # Role distribution
    # ==========================================================================

    st.header("📌 Role Distribution")

    role_distribution = dashboard_service.get_role_distribution()

    if role_distribution:
        role_df = pd.DataFrame(role_distribution)

        # Filter according to the selection
        filtered_df = role_df[role_df["role"].isin(selected_roles)]

        st.bar_chart(
            filtered_df,
            x="role",
            y="count",
        )
