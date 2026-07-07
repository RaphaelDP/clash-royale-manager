"""
================================================================================
Filename: 02_members.py
Description: Streamlit page for displaying and filtering clan members.
Author: Raphael Smilet
Date Created: 2026-07-03
Last Modified: 2026-07-03
Version: 0.5.0
Python Version: 3.12
Dependencies: streamlit, pandas, app.database.session, app.database.models
================================================================================
"""

from datetime import timedelta

import streamlit as st
import pandas as pd

from app.core.utils import get_time
from app.database.session import get_session
from app.database.models import Member

st.set_page_config(page_title="Clan Members", layout="wide")
st.title("👥 Clan Members")

with get_session() as db:
    members = db.query(Member).all()

    if members:
        # --- Filters ---
        st.sidebar.header("Filters")
        role_filter = st.sidebar.multiselect(
            "Role",
            options=["leader", "coLeader", "elder", "member", "left", "fired"],
            default=["leader", "coLeader", "elder", "member"],
        )
        min_trophies = st.sidebar.slider("Min Trophies", 0, 14000, 0)
        min_donations = st.sidebar.slider("Min Donations", 0, 5000, 0)
        inactive_days = st.sidebar.slider("Inactive Days Threshold", 1, 30, 7)

        # Apply filters
        filtered_members = [
            m
            for m in members
            if (m.role in role_filter)
            and (m.trophies >= min_trophies)
            and (m.donations >= min_donations)
            and (
                not m.last_seen
                or (get_time() - m.last_seen) <= timedelta(days=inactive_days)
            )
        ]

        # --- Member Table ---
        st.subheader(f"Member List ({len(filtered_members)})")
        members_data = [
            {
                "Tag": m.tag,
                "Name": m.name,
                "Role": m.role,
                "Trophies": m.trophies,
                "Donations": m.donations,
                "Last Seen": m.last_seen,
                "Promotion Score": m.promotion_score,
            }
            for m in filtered_members
        ]
        df = pd.DataFrame(members_data)
        st.dataframe(df, width="stretch")

        # --- Stats ---
        st.subheader("📊 Member Statistics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Filtered Members", len(filtered_members))
        with col2:
            avg_trophies = (
                sum(m.trophies for m in filtered_members) / len(filtered_members)
                if filtered_members
                else 0
            )
            st.metric("Avg Trophies", f"{avg_trophies:.0f}")
        with col3:
            total_donations = sum(m.donations for m in filtered_members)
            st.metric("Total Donations", total_donations)

        # --- Inactivity Alert ---
        inactive_members = [
            m
            for m in members
            if m.last_seen
            and m.role not in ["left", "fired"]
            and (get_time() - m.last_seen) > timedelta(days=inactive_days)
        ]
        if inactive_members:
            st.warning(
                f"⚠️ {len(inactive_members)} members inactive for more than {inactive_days} days."
            )
            inactive_df = pd.DataFrame(
                [
                    {
                        "Tag": m.tag,
                        "Name": m.name,
                        "Last Seen": m.last_seen,
                        "Days Inactive": (get_time() - m.last_seen).days,
                    }
                    for m in inactive_members
                ]
            )
            st.dataframe(inactive_df, width="stretch")
    else:
        st.warning("No members found in the database.")
