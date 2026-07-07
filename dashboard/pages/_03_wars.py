"""
================================================================================
Filename: 03_wars.py
Description: Streamlit page for displaying war performance and participation.
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
from app.database.models import WarSeason

st.set_page_config(page_title="War Performance", layout="wide")
st.title("⚔️ War Performance")

with get_session() as db:
    war_seasons = db.query(WarSeason).all()

    if war_seasons:
        # --- Season Selector ---
        selected_season = st.selectbox(
            "Select War Season",
            [s.season_id for s in war_seasons],
        )
        selected_season_obj = (
            db.query(WarSeason).filter_by(season_id=selected_season).first()
        )
        river_races = selected_season_obj.river_races if selected_season_obj else []

        if river_races:
            # --- Season Overview ---
            st.header(f"Season {selected_season} Overview")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                total_fame = sum(
                    p.fame for race in river_races for p in race.war_participations
                )
                st.metric("Total Fame", total_fame)
            with col2:
                total_repair = sum(
                    p.repair_points
                    for race in river_races
                    for p in race.war_participations
                )
                st.metric("Total Repair Points", total_repair)
            with col3:
                total_decks = sum(
                    p.decks_used
                    for race in river_races
                    for p in race.war_participations
                )
                st.metric("Total Decks Used", total_decks)
            with col4:
                avg_boat_attacks = (
                    sum(
                        p.boat_attacks
                        for race in river_races
                        for p in race.war_participations
                    )
                    / len([p for race in river_races for p in race.war_participations])
                    if river_races
                    else 0
                )
                st.metric("Avg Boat Attacks", f"{avg_boat_attacks:.1f}")

            # --- Race Breakdown ---
            st.header("🏁 Race Breakdown")
            for race in river_races:
                with st.expander(
                    f"Race {race.section_index} (Created: {race.created_date})"
                ):
                    participations = race.war_participations
                    if participations:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Participants", len(participations))
                        with col2:
                            race_fame = sum(p.fame for p in participations)
                            st.metric("Race Fame", race_fame)

                        # Participations table
                        participations_data = [
                            {
                                "Tag": p.member_tag,
                                "Member": p.member.name,
                                "Fame": p.fame,
                                "Repair Points": p.repair_points,
                                "Boat Attacks": p.boat_attacks,
                                "Decks Used": p.decks_used,
                                "Decks Used Today": p.decks_used_today,
                            }
                            for p in participations
                        ]
                        df = pd.DataFrame(participations_data)
                        st.dataframe(df, width="stretch")
                    else:
                        st.warning(f"No participations for race {race.section_index}.")

            # --- Top Performers ---
            st.header("🏆 Top Performers in Season")
            all_participations = [
                p for race in river_races for p in race.war_participations
            ]
            if all_participations:
                metric = st.selectbox(
                    "Sort by", ["Fame", "Repair Points", "Boat Attacks", "Decks Used"]
                )
                top_performers = sorted(
                    all_participations,
                    key=lambda x: getattr(x, metric.lower().replace(" ", "_")),
                    reverse=True,
                )[:10]
                performers_df = pd.DataFrame(
                    [
                        {
                            "Tag": p.member_tag,
                            "Member": p.member.name,
                            "Fame": p.fame,
                            "Repair Points": p.repair_points,
                            "Boat Attacks": p.boat_attacks,
                            "Decks Used": p.decks_used,
                        }
                        for p in top_performers
                    ]
                )
                st.dataframe(performers_df, width="stretch")
        else:
            st.warning("No river races found for this season.")
    else:
        st.warning("No war seasons found in the database.")
