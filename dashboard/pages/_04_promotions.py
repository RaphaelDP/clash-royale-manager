"""
================================================================================
Filename: _04_promotions.py
Description: Streamlit page for displaying promotion rankings and inactivity analysis.
Author: Raphael Smilet
Date Created: 2026-07-03
Last Modified: 2026-07-08
Version: 0.5.1
================================================================================
"""

import streamlit as st
import pandas as pd
from app.database.session import get_session
from app.services.dashboard_service import DashboardService

st.set_page_config(page_title="Promotions", layout="wide")
st.title("📈 Promotions & Clan Management")

with get_session() as db:
    dashboard = DashboardService(db)

    overview = dashboard.get_overview_stats()
    promotion = dashboard.get_promotion_dashboard()

    st.header("🏆 Promotion Overview")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Members", overview["member_count"])
    with c2:
        st.metric("Promotion Scores", promotion["score_count"])
    with c3:
        st.metric("Average Score", f"{promotion['average_score']:.2f}")
    with c4:
        st.metric("Highest Score", f"{promotion['highest_score']:.2f}")

    st.divider()

    st.header("🥇 Promotion Ranking")

    ranking = pd.DataFrame(promotion["ranking"])

    if not ranking.empty:
        st.dataframe(ranking, width="stretch")

        c1, c2 = st.columns(2)

        with c1:
            st.subheader("Top Promotion Scores")
            st.bar_chart(ranking.head(15), x="name", y="score")

        with c2:
            st.subheader("Promotion Score Distribution")
            st.bar_chart(
                ranking.sort_values("score"),
                x="name",
                y="score",
            )
    else:
        st.info("No promotion scores available.")

    st.divider()

    st.header("🎖 Component Rankings")

    metric = st.selectbox(
        "Sort by",
        [
            "score",
            "war_activity",
            "war_win_rate",
            "donations",
            "trophy_level",
        ],
    )

    if not ranking.empty:
        st.dataframe(
            ranking.sort_values(metric, ascending=False),
            width="stretch",
        )

    st.divider()

    st.header("🚨 Inactive Members")

    threshold = st.slider(
        "Inactive after (days)",
        7,
        60,
        14,
    )

    inactive = pd.DataFrame(dashboard.get_inactive_members(threshold))

    if not inactive.empty:
        st.warning(f"{len(inactive)} inactive members found.")
        st.dataframe(inactive, width="stretch")
    else:
        st.success("No inactive members.")

    st.divider()

    st.header("📉 Promotion Candidates")

    if not ranking.empty:
        promote = ranking[(ranking["score"] >= ranking["score"].quantile(0.90))]

        st.success(f"{len(promote)} promotion candidates")

        st.dataframe(
            promote,
            width="stretch",
        )

    st.divider()

    st.header("❌ Kick Candidates")

    kick = pd.DataFrame(dashboard.get_kick_candidates(threshold))

    if not kick.empty:
        st.error(f"{len(kick)} kick candidates")
        st.dataframe(kick, width="stretch")
    else:
        st.info("Kick-candidate detection is planned for v0.8.0 (Decision Support Release).")

    st.divider()

    st.header("📊 Clan Distribution")

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Promotion Components")

        if not ranking.empty:
            component_df = ranking[
                [
                    "name",
                    "war_activity",
                    "war_win_rate",
                    "donations",
                    "trophy_level",
                ]
            ]
            st.dataframe(component_df, width="stretch")

    with c2:
        st.subheader("Top 10 Overall")

        if not ranking.empty:
            st.dataframe(
                ranking.head(10),
                width="stretch",
            )

    st.divider()

    if not ranking.empty:
        st.download_button(
            "📥 Download Promotion Ranking",
            ranking.to_csv(index=False).encode(),
            file_name="promotion_ranking.csv",
            mime="text/csv",
        )