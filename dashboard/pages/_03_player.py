"""
================================================================================
Filename: _03_player.py
Description: Streamlit page for displaying detailed player statistics.
Author: Raphael Smilet
Date Created: 2026-07-07
Last Modified: 2026-09-30
Version: 0.5.2
Python Version: 3.12
Dependencies: streamlit, dashboard.functions
================================================================================
"""

import streamlit as st

from dashboard.functions import get_player_options, get_player_page_data

st.set_page_config(page_title="Player Profile", page_icon="👤", layout="wide")
st.title("👤 Player Profile")

selected_role = st.selectbox(
    "Select roles to filter by", ["leader", "coLeader", "elder", "member"]
)
players = get_player_options(selected_role)
if not players:
    st.warning("No members found.")
    st.stop()

selected_tag = st.selectbox("Select a player", players, format_func=players.get)
refresh = st.button("🔄 Refresh Clash Royale profile")
with st.spinner("Loading player profile..."):
    data = get_player_page_data(selected_tag, refresh=refresh)
if data is None:
    st.error("Unable to load player.")
    st.stop()
if data["sync_warning"]:
    st.warning(data["sync_warning"])

st.caption(f"Profile cache updated: {data['cache_updated_display']}")

profile = data["profile"]
api = data["api"]
st.header(profile["name"])
columns = st.columns(5)
with columns[0]:
    st.metric("🏆 Trophies", profile["trophies"])
with columns[1]:
    st.metric("🥇 Best", api.get("bestTrophies", "-"))
with columns[2]:
    st.metric(
        "⭐ Contribution",
        (
            f"{profile['contribution_score']:.1f}"
            if profile["contribution_score"] is not None
            else "-"
        ),
    )
with columns[3]:
    st.metric("🎯 Level", api.get("expLevel", "-"))
with columns[4]:
    st.metric("⏱ Last seen", data["last_seen_display"])

st.divider()
left, right = st.columns([2, 1])
with left:
    for title, key in (
        ("General Information", "info_df"),
        ("Battle Statistics", "battle_df"),
        ("Clan Activity", "activity_df"),
    ):
        st.subheader(title)
        st.dataframe(data[key], hide_index=True, width="stretch")
with right:
    st.subheader("Performance")
    st.metric("Win Rate", f"{data['winrate']}%")
    for label, key in (
        ("Challenge Max Wins", "challengeMaxWins"),
        ("Challenge Cards", "challengeCardsWon"),
        ("Tournament Cards", "tournamentCardsWon"),
        ("Star Points", "starPoints"),
        ("XP", "expPoints"),
    ):
        st.metric(label, api.get(key))

st.divider()
st.subheader("Current Deck")
if not data["deck_df"].empty:
    st.dataframe(data["deck_df"], hide_index=True, width="stretch")
st.subheader("Recent Progress")
st.dataframe(data["progress_df"], hide_index=True, width="stretch")
if not data["badge_df"].empty:
    st.subheader(f"Badges ({len(data['badge_df'])})")
    st.dataframe(data["badge_df"], hide_index=True, width="stretch")

st.divider()
st.subheader("Season Results")
for column, key, label in zip(
    st.columns(3),
    ("current", "last", "best"),
    ("🏅 Current Season", "📅 Previous Season", "👑 Best Season"),
):
    with column:
        st.markdown(f"### {label}")
        result = data["season_results"][key]
        if result:
            st.metric("League", result.get("leagueNumber", "-"))
            st.metric("Trophies", result.get("trophies", "-"))
            st.metric("Rank", result.get("rank", "-"))
        else:
            st.info("No season data.")

st.divider()
st.subheader("War Statistics")
war = data["war"]
if war["count"]:
    for column, label, key in zip(
        st.columns(4),
        ("River Races", "Total Fame", "Boat Attacks", "Decks Used"),
        ("count", "total_fame", "total_boats", "total_decks"),
    ):
        with column:
            st.metric(label, war[key])
    st.dataframe(war["df"], hide_index=True, width="stretch")
else:
    st.info("No war participation found.")

st.divider()
st.subheader("Contribution History")
if not data["score_df"].empty:
    st.line_chart(data["score_chart"], height=250)
    st.dataframe(data["score_df"], hide_index=True, width="stretch")
else:
    st.info("No contribution score history.")

st.divider()
st.subheader("Snapshot History")
if not data["snapshot_df"].empty:
    st.line_chart(data["snapshot_chart"], height=300)
    st.dataframe(data["snapshot_df"], hide_index=True, width="stretch")
else:
    st.info("No snapshots available.")

st.divider()
with st.expander("Raw Clash Royale API Response"):
    st.json(api)
