"""
================================================================================
Filename: 04_promotions.py
Description: Streamlit page for displaying promotion and kick candidates.
Author: Raphael Smilet
Date Created: 2026-07-03
Last Modified: 2026-07-03
Version: 0.5.0
Python Version: 3.12
Dependencies: streamlit, pandas, app.database.session, app.database.models
================================================================================
"""

import streamlit as st
import pandas as pd

from app.database.session import get_session
from app.database.models import Member, PromotionScore, Snapshot
from app.core.utils import get_time

st.set_page_config(page_title="Promotions & Kick Candidates", layout="wide")
st.title("📈 Promotions & Kick Candidates")

with get_session() as db:
    members = db.query(Member).all()
    promotion_scores = db.query(PromotionScore).all()
    snapshots = db.query(Snapshot).all()

    # --- Promotion Scores ---
    st.header("🏆 Promotion Candidates")
    if promotion_scores:
        # Sort by score (descending)
        sorted_scores = sorted(promotion_scores, key=lambda x: x.score, reverse=True)

        # Display top candidates
        st.subheader("Top 10 Promotion Candidates")
        scores_data = [{
            "Member": s.member_tag,
            "Score": f"{s.score:.2f}",
            "War Activity": f"{s.war_activity:.2f}",
            "War Win Rate": f"{s.war_win_rate:.2f}",
            "Donations": f"{s.donations:.2f}",
            "Trophy Level": f"{s.trophy_level:.2f}",
            "Last Updated": s.calculated_at,
        } for s in sorted_scores[:10]]
        df = pd.DataFrame(scores_data)
        st.dataframe(df, width="stretch")

        # Score distribution
        st.subheader("Score Distribution")
        st.bar_chart(
            pd.DataFrame([{"Member": s.member_tag, "Score": s.score} for s in sorted_scores]),
            x="Member",
            y="Score",
        )
    else:
        st.warning("No promotion scores found in the database.")

    # --- Inactivity Analysis ---
    st.header("🚨 Kick Candidates")
    inactive_threshold = st.slider("Inactive Days Threshold", 7, 30, 14)
    inactive_members = []
    for member in members:
        latest_snapshot = (
            db.query(Snapshot)
            .filter_by(member_tag=member.tag)
            .order_by(Snapshot.collected_at.desc())
            .first()
        )
        if latest_snapshot:
            days_inactive = (get_time() - latest_snapshot.collected_at).days
            if days_inactive > inactive_threshold:
                inactive_members.append({
                    "Tag": member.tag,
                    "Name": member.name,
                    "Days Inactive": days_inactive,
                    "Last Seen": latest_snapshot.collected_at,
                })

    if inactive_members:
        st.warning(f"⚠️ {len(inactive_members)} members inactive for more than {inactive_threshold} days.")
        inactive_df = pd.DataFrame(inactive_members)
        st.dataframe(inactive_df, width='stretch')
    else:
        st.success("No inactive members found!")

    # --- Activity Trends ---
    st.header("📉 Activity Trends")
    if snapshots:
        # Group by member and calculate activity metrics
        activity_data = []
        for member in members:
            member_snapshots = [s for s in snapshots if s.member_tag == member.tag]
            if member_snapshots:
                latest = max(member_snapshots, key=lambda x: x.collected_at)
                days_since_last = (get_time() - latest.collected_at).days
                avg_trophies = sum(s.trophies for s in member_snapshots) / len(member_snapshots)
                avg_donations = sum(s.donations for s in member_snapshots) / len(member_snapshots)
                activity_data.append({
                    "Member": member.tag,
                    "Days Since Last Activity": days_since_last,
                    "Avg Trophies": avg_trophies,
                    "Avg Donations": avg_donations,
                })

        activity_df = pd.DataFrame(activity_data)
        st.dataframe(activity_df, width='stretch')
    else:
        st.warning("No snapshot data available for activity trends.")
