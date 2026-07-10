"""
================================================================================
Filename: _03_player.py
Description: Streamlit page for displaying detailed player statistics.
Author: Raphael Smilet
Date Created: 2026-07-07
Last Modified: 2026-07-08
Version: 0.5.0
Python Version: 3.12
Dependencies: streamlit, pandas, app.database.session, app.services.dashboard_service
================================================================================
"""

import pandas as pd
import streamlit as st

from app.database.session import get_session
from app.services.dashboard_service import DashboardService
from app.services.member_service import MemberService
from app.core.utils import get_time

st.set_page_config(page_title="Player Profile", page_icon="👤", layout="wide")
st.title("👤 Player Profile")

with get_session() as db:

    dashboard = DashboardService(db)
    member_service = MemberService(db)

    selected_roles = st.selectbox(
        "Select roles to filter by",
        ["leader", "coLeader", "elder", "member"],
    )

    members = dashboard.get_members_filter_by_role(
        role=selected_roles,
    )

    if not members:
        st.warning("No members found.")
        st.stop()

    selected = st.selectbox(
        "Select a player",
        members,
        format_func=lambda m: f"{m.name} ({m.role})",
    )

    refresh = st.button("🔄 Refresh Clash Royale profile")

    profile = member_service.get_player_profile(
        selected.tag,
        all_stats=True,
        refresh=refresh,
    )

    if not profile:
        st.error("Unable to load player.")
        st.stop()

    api = profile.get("api", {})

    st.header(profile["name"])

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("🏆 Trophies", profile["trophies"])

    with col2:
        st.metric(
            "🥇 Best",
            api.get("bestTrophies", "-"),
        )

    with col3:
        st.metric(
            "⭐ Promotion",
            (
                f"{profile['promotion_score']:.1f}"
                if profile["promotion_score"] is not None
                else "-"
            ),
        )

    with col4:
        st.metric(
            "🎯 Level",
            api.get("expLevel", "-"),
        )

    with col5:
        last_seen = profile["last_seen"]

        display_value = "-"

        if last_seen:
            delta = get_time() - last_seen
            display_value = f"{delta.days} day(s) ago"

        st.metric("⏱ Last seen", display_value)

    st.divider()

    left, right = st.columns([2, 1])

    with left:

        st.subheader("General Information")

        info = pd.DataFrame(
            [
                ("Tag", profile["tag"]),
                ("Role", profile["role"]),
                ("Arena", api.get("arena", {}).get("name")),
                ("Clan", api.get("clan", {}).get("name")),
                (
                    "League",
                    api.get("leagueStatistics", {})
                    .get("currentSeason", {})
                    .get("leagueNumber"),
                ),
                ("Favorite Card", api.get("currentFavouriteCard", {}).get("name")),
            ],
            columns=["Field", "Value"],
        )

        st.dataframe(info, hide_index=True, width="stretch")

        st.subheader("Battle Statistics")

        battle = pd.DataFrame(
            [
                {
                    "Wins": api.get("wins"),
                    "Losses": api.get("losses"),
                    "Battles": api.get("battleCount"),
                    "3 Crowns": api.get("threeCrownWins"),
                    "Current Streak": api.get("currentWinLoseStreak"),
                    "War Wins": api.get("warDayWins"),
                }
            ]
        )

        st.dataframe(battle, hide_index=True, width="stretch")

        st.subheader("Clan Activity")

        activity = pd.DataFrame(
            [
                {
                    "Donations": profile["donations"],
                    "Total Donations": api.get("totalDonations"),
                    "Received": api.get("donationsReceived"),
                    "Clan Cards": api.get("clanCardsCollected"),
                }
            ]
        )

        st.dataframe(activity, hide_index=True, width="stretch")

    with right:

        st.subheader("Performance")

        wins = api.get("wins", 0)
        losses = api.get("losses", 0)

        total = wins + losses

        winrate = round((wins / total) * 100, 1) if total else 0

        st.metric("Win Rate", f"{winrate}%")
        st.metric("Challenge Max Wins", api.get("challengeMaxWins"))
        st.metric("Challenge Cards", api.get("challengeCardsWon"))
        st.metric("Tournament Cards", api.get("tournamentCardsWon"))
        st.metric("Star Points", api.get("starPoints"))
        st.metric("XP", api.get("expPoints"))

    st.divider()

    st.subheader("Current Deck")

    deck = api.get("currentDeck", [])

    if deck:

        deck_df = pd.DataFrame(
            [
                {
                    "Card": card.get("name"),
                    "Level": card.get("level"),
                    "Evolution": card.get("evolutionLevel"),
                }
                for card in deck
            ]
        )

        st.dataframe(deck_df, hide_index=True, width="stretch")

    st.subheader("Recent Progress")

    progress = pd.DataFrame(
        [
            {
                "Current Trophies": api.get("trophies"),
                "Best Trophies": api.get("bestTrophies"),
                "Legacy Best": api.get("legacyTrophyRoadHighScore"),
                "Challenge Max Wins": api.get("challengeMaxWins"),
                "Battle Count": api.get("battleCount"),
            }
        ]
    )

    st.dataframe(progress, hide_index=True, width="stretch")

    badges = api.get("badges", [])

    if badges:

        st.subheader(f"Badges ({len(badges)})")

        badge_df = pd.DataFrame(
            [
                {
                    "Badge": badge.get("name"),
                    "Level": badge.get("level"),
                    "Progress": badge.get("progress"),
                }
                for badge in badges
            ]
        )

        st.dataframe(badge_df, hide_index=True, width="stretch")

    st.divider()

    st.subheader("Season Results")

    season_cols = st.columns(3)

    current = api.get("currentPathOfLegendSeasonResult", {})
    last = api.get("lastPathOfLegendSeasonResult", {})
    best = api.get("bestPathOfLegendSeasonResult", {})

    with season_cols[0]:
        st.markdown("### 🏅 Current Season")
        if current:
            st.metric("League", current.get("leagueNumber", "-"))
            st.metric("Trophies", current.get("trophies", "-"))
            st.metric("Rank", current.get("rank", "-"))
        else:
            st.info("No current season data.")

    with season_cols[1]:
        st.markdown("### 📅 Previous Season")
        if last:
            st.metric("League", last.get("leagueNumber", "-"))
            st.metric("Trophies", last.get("trophies", "-"))
            st.metric("Rank", last.get("rank", "-"))
        else:
            st.info("No previous season data.")

    with season_cols[2]:
        st.markdown("### 👑 Best Season")
        if best:
            st.metric("League", best.get("leagueNumber", "-"))
            st.metric("Trophies", best.get("trophies", "-"))
            st.metric("Rank", best.get("rank", "-"))
        else:
            st.info("No best season data.")

    st.divider()

    st.subheader("War Statistics")

    history = member_service.get_member_history(profile["tag"])

    participations = history.get("war_participations", [])

    if participations:

        total_fame = sum(p.fame for p in participations)
        total_repairs = sum(p.repair_points for p in participations)
        total_boats = sum(p.boat_attacks for p in participations)
        total_decks = sum(p.decks_used for p in participations)

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric("River Races", len(participations))

        with c2:
            st.metric("Total Fame", total_fame)

        with c3:
            st.metric("Boat Attacks", total_boats)

        with c4:
            st.metric("Decks Used", total_decks)

        war_df = pd.DataFrame(
            [
                {
                    "Season": p.river_race.season_id,
                    "Race": p.river_race.section_index,
                    "Fame": p.fame,
                    "Repairs": p.repair_points,
                    "Boat": p.boat_attacks,
                    "Decks": p.decks_used,
                }
                for p in sorted(
                    participations,
                    key=lambda x: (
                        x.river_race.season_id,
                        x.river_race.section_index,
                    ),
                    reverse=True,
                )
            ]
        )

        st.dataframe(war_df, hide_index=True, width="stretch")

    else:
        st.info("No war participation found.")

    st.divider()

    st.subheader("Promotion History")

    scores = history.get("promotion_scores", [])

    if scores:

        score_df = pd.DataFrame(
            [
                {
                    "Date": s.calculated_at,
                    "Score": s.score,
                    "War Activity": s.war_activity,
                    "War Win Rate": s.war_win_rate,
                    "Donations": s.donations,
                    "Trophies": s.trophy_level,
                }
                for s in sorted(
                    scores,
                    key=lambda x: x.calculated_at,
                )
            ]
        )

        st.line_chart(
            score_df.set_index("Date")["Score"],
            height=250,
        )

        st.dataframe(score_df, hide_index=True, width="stretch")

    else:
        st.info("No promotion score history.")

    st.divider()

    st.subheader("Snapshot History")

    snapshots = history.get("snapshots", [])

    if snapshots:

        snapshot_df = pd.DataFrame(
            [
                {
                    "Date": s.collected_at,
                    "Trophies": s.trophies,
                    "Donations": s.donations,
                }
                for s in sorted(
                    snapshots,
                    key=lambda x: x.collected_at,
                )
            ]
        )

        st.line_chart(
            snapshot_df.set_index("Date")[["Trophies", "Donations"]],
            height=300,
        )

        st.dataframe(snapshot_df, hide_index=True, width="stretch")

    else:
        st.info("No snapshots available.")

    st.divider()

    with st.expander("Raw Clash Royale API Response"):

        st.json(api)
