"""
================================================================================
Filename: _04_promotions.py
Description: Streamlit page for displaying contribution rankings, promotion
    recommendations, and inactivity analysis.
Author: Raphael Smilet
Date Created: 2026-07-03
Last Modified: 2026-09-30
Version: 0.6.2
================================================================================
"""

import streamlit as st
from dashboard.functions import (
    get_promotions_page_data,
    get_inactive_members_data,
    sort_contribution_ranking,
)

st.set_page_config(page_title="Promotions", layout="wide")
st.title("📈 Promotions & Clan Management")

data = get_promotions_page_data()
overview = data["overview"]
contribution = data["contribution"]

st.header("🏆 Contribution Overview")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Actual members", overview["actual_members"])
with c2:
    st.metric("Contribution Scores", contribution["score_count"])
with c3:
    st.metric("Average Score", f"{contribution['average_score']:.2f}")
with c4:
    st.metric("Highest Score", f"{contribution['highest_score']:.2f}")

st.divider()

st.header("🥇 Contribution Ranking")

ranking = data["ranking"]

if not ranking.empty:
    st.dataframe(ranking, width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Top Contribution Scores")
        st.bar_chart(data["top_scores"], x="name", y="score")
    with c2:
        st.subheader("Contribution Score Distribution")
        st.bar_chart(data["score_distribution"], x="name", y="score")
else:
    st.info("No contribution scores available.")

st.divider()

st.header("🎖 Component Rankings")

metric = st.selectbox(
    "Sort by",
    [
        "score",
        "war_activity",
        "war_performance",
        "donations",
        "trophy_level",
        "activity",
        "consistency",
        "seniority",
    ],
)

if not ranking.empty:
    st.dataframe(sort_contribution_ranking(ranking, metric), width="stretch")

st.divider()

st.header("🔀 Promotion Recommendations")

st.caption(
    "Rank-based on the last completed river race's fame (not the "
    "Contribution Score above). This is a read-only recommendation — "
    "the Clash Royale API can't apply role changes automatically, so "
    "these need to be actioned manually in-game."
)

recommendations = data["recommendations"]

if not recommendations.empty:
    actionable = data["actionable"]

    if not actionable.empty:
        st.dataframe(
            actionable,
            hide_index=True,
            width="stretch",
        )
    else:
        st.success("No promotion/demotion changes recommended right now.")

    with st.expander("Show full ranking (including no-change members)"):
        st.dataframe(
            recommendations,
            hide_index=True,
            width="stretch",
        )
else:
    st.info("No completed river race yet - recommendations need at least one.")

st.divider()

st.header("🚨 Inactive Members")

threshold = st.slider("Inactive after (days)", 7, 60, 14)

inactive = get_inactive_members_data(threshold)

if not inactive.empty:
    st.warning(f"{len(inactive)} inactive members found.")
    st.dataframe(inactive, width="stretch")
else:
    st.success("No inactive members.")

st.divider()

st.header("❌ Kick Candidates")

st.caption(
    "Members who scored under the fame sanction threshold in 2 "
    "consecutive completed races."
)

kick = data["kick"]

if not kick.empty:
    st.error(f"{len(kick)} kick candidates")
    st.dataframe(kick, hide_index=True, width="stretch")
else:
    st.success("No kick candidates.")

st.divider()

st.header("📊 Clan Distribution")

c1, c2 = st.columns(2)
with c1:
    st.subheader("Contribution Components")
    if not ranking.empty:
        st.dataframe(data["components"], width="stretch")

with c2:
    st.subheader("Top 10 Overall")
    if not ranking.empty:
        st.dataframe(data["top_ten"], width="stretch")

st.divider()

if not ranking.empty:
    st.download_button(
        "📥 Download Contribution Ranking",
        data["ranking_csv"],
        file_name="contribution_ranking.csv",
        mime="text/csv",
    )
