"""
================================================================================
Filename: 01_overview.py
Description: Streamlit page for displaying clan overview and KPIs.
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

from app.database.session import get_session
from app.database.models import Member, Snapshot, WarSeason, RiverRace, WarParticipation
from app.core.utils import get_time

st.set_page_config(page_title="Clan Overview", layout="wide")
st.title("📊 Clan Overview")

with get_session() as db:
    members = db.query(Member).all()
    snapshots = db.query(Snapshot).all()
    war_seasons = db.query(WarSeason).all()
    river_races = db.query(RiverRace).all()
    participations = db.query(WarParticipation).all()

    # --- Clan Statistics ---
    st.header("📈 Clan Statistics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Members", len(members))
    with col2:
        avg_trophies = sum(m.trophies for m in members) / len(members) if members else 0
        st.metric("Avg Trophies", f"{avg_trophies:.0f}")
    with col3:
        total_donations = sum(m.donations for m in members)
        st.metric("Total Donations", total_donations)
    with col4:
        active_members = len([m for m in members if m.last_seen and (get_time() - m.last_seen) < timedelta(days=7)])
        st.metric("Active (7d)", active_members)

    # --- Activity Trends ---
    st.header("📉 Activity Trends")
    if snapshots:
        # Group snapshots by date
        snapshots_df = pd.DataFrame([{
            "date": s.collected_at.date(),
            "trophies": s.trophies,
            "donations": s.donations,
        } for s in snapshots])
        snapshots_df["date"] = pd.to_datetime(snapshots_df["date"])
        snapshots_df = snapshots_df.groupby("date").mean().reset_index()

        # Plot trophies and donations over time
        st.line_chart(
            snapshots_df,
            x="date",
            y=["trophies", "donations"],
            title="Trophies & Donations Over Time",
        )
    else:
        st.warning("No snapshot data available.")

    # --- War Performance ---
    st.header("⚔️ War Performance")
    if war_seasons:
        selected_season = st.selectbox(
            "Select War Season",
            [s.season_id for s in war_seasons],
        )
        selected_season_obj = db.query(WarSeason).filter_by(season_id=selected_season).first()
        river_races = selected_season_obj.river_races if selected_season_obj else []

        if river_races:
            col1, col2, col3 = st.columns(3)
            with col1:
                total_fame = sum(p.fame for race in river_races for p in race.war_participations)
                st.metric("Total Fame", total_fame)
            with col2:
                total_repair = sum(p.repair_points for race in river_races for p in race.war_participations)
                st.metric("Total Repair Points", total_repair)
            with col3:
                total_decks = sum(p.decks_used for race in river_races for p in race.war_participations)
                st.metric("Total Decks Used", total_decks)

            # Top performers in the selected season
            st.subheader("🏆 Top Performers")
            all_participations = [
                p for race in river_races for p in race.war_participations
            ]
            if all_participations:
                top_performers = sorted(all_participations, key=lambda x: x.fame, reverse=True)[:5]
                performers_df = pd.DataFrame([{
                    "Member": p.member_tag,
                    "Fame": p.fame,
                    "Repair Points": p.repair_points,
                    "Decks Used": p.decks_used,
                } for p in top_performers])
                st.dataframe(performers_df, width='stretch')
        else:
            st.warning("No river races found for this season.")
    else:
        st.warning("No war seasons found.")
