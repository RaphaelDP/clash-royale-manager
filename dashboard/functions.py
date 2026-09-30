"""
================================================================================
Filename: functions.py
Description: Data preparation and action helpers for the Streamlit dashboard.
Author: Raphael Smilet
Date Created: 2026-07-25
Last Modified: 2026-09-30
Version: 0.1.2
Python Version: 3.12
Dependencies: pandas, streamlit, app.database, app.services, app.scheduler.jobs
================================================================================
"""

import copy

from pathlib import Path
from platform import python_version
from typing import Any, Callable

import pandas as pd
import streamlit as st

from app.core.config import settings, validate_required_config
from app.core.utils import count, format_datetime, get_time
from app.database.models import (
    JobRunState,
    ContributionScore,
    Member,
    RiverRace,
    Snapshot,
    WarParticipation,
    WarSeason,
)
from app.database.session import get_session
from app.scheduler.jobs import calculate_scores, update_clan_members, update_war_data
from app.services.dashboard_service import DashboardService
from app.services.member_service import MemberService
from app.services.scheduler_config import load_schedule, save_schedule, DEFAULT_SCHEDULE
from app.scheduler.scheduler import JOB_NAMES


def refresh_clan_members_data() -> bool:
    """
    Refresh clan members data by calling the update_clan_members job.
    """
    with get_session() as db_session:
        return update_clan_members(db_session=db_session)


def refresh_war_data() -> bool:
    """
    Refresh war data by calling the update_war_data job.
    """
    with get_session() as db_session:
        return update_war_data(db_session=db_session)


def recalculate_scores() -> bool:
    """
    Recalculate scores by calling the calculate_scores job.
    """
    with get_session() as db_session:
        return calculate_scores(db_session=db_session)


def execute_dashboard_action(action: Callable[[], Any], label: str) -> None:
    """
    Execute a dashboard action with a spinner and prevent multiple simultaneous executions.

    Args:
        action (callable): The function to execute.
        label (str): The label to display in the spinner.
    """

    if st.session_state.get("dashboard_action_running", False):
        return

    st.session_state.dashboard_action_running = True

    try:
        with st.spinner(f"⏳ {label}"):
            result = action()
        if result is False:
            st.error("The action failed. Check the logs for details.")
    except Exception as error:
        st.error(f"The action failed: {error}")
    finally:
        st.session_state.dashboard_action_running = False


def dashboard_action_running() -> bool:
    """
    Check if a dashboard action is currently running.

    Returns:
        bool: True if an action is running, False otherwise.
    """
    return st.session_state.get("dashboard_action_running", False)


def get_home_page_data() -> dict[str, Any]:
    """Prepare configuration validation for the landing page."""
    return {"missing_config": validate_required_config()}


# -----------------------------------------------------------------------------
# Overview
# -----------------------------------------------------------------------------


def get_overview_page_data() -> dict[str, Any]:
    """
    Collect and prepare all data displayed by the overview page.

    Returns:
        dict[str, Any]: A dictionary containing all the data needed for the overview page.
    """
    with get_session() as db:
        dashboard = DashboardService(db, api_clash=None)

        failed_jobs = [
            job
            for job in dashboard.get_failed_jobs()
            if job.job_name in {"update_clan_members", "update_war_data"}
        ]
        known_success_dates = [
            job.last_success_at
            for job in failed_jobs
            if job.last_success_at is not None
        ]
        stale_since = min(known_success_dates) if known_success_dates else None

        health = dashboard.get_clan_health_score()
        activity = dashboard.get_inactivity_ranking(limit=15)
        snapshot_history = dashboard.get_daily_snapshot_history()
        roles = dashboard.get_role_distribution()
        top_trophies = dashboard.get_top_members_by_trophies()
        top_donations = dashboard.get_top_members_by_donations()
        top_war_players = dashboard.get_top_war_players()
        snapshots = dashboard.get_snapshot_stats()
        snapshots["latest_display"] = format_datetime(snapshots["latest_snapshot"])
        snapshots["oldest_display"] = format_datetime(snapshots["oldest_snapshot"])
        snapshots["days_since_update"] = (
            (get_time() - snapshots["latest_snapshot"]).days
            if snapshots["latest_snapshot"]
            else "-"
        )

        return {
            "sync_warning": _get_sync_warning(failed_jobs, stale_since),
            "overview": dashboard.get_overview_stats(),
            "database": dashboard.get_database_stats(),
            "war": dashboard.get_war_stats(),
            "snapshots": snapshots,
            "health": health,
            "health_components": pd.DataFrame(
                [
                    {"Component": key.replace("_", " ").title(), "Score": value}
                    for key, value in health["components"].items()
                ]
            ),
            "activity": pd.DataFrame(activity) if activity else pd.DataFrame(),
            "snapshot_history": _snapshot_history_dataframe(snapshot_history),
            "roles": pd.DataFrame(roles) if roles else pd.DataFrame(),
            "top_trophies": _member_ranking_dataframe(
                top_trophies, "Trophies", lambda member: member.trophies
            ),
            "top_donations": _member_ranking_dataframe(
                top_donations, "Donations", lambda member: member.donations
            ),
            "top_war_players": _war_players_dataframe(top_war_players),
        }


def _get_sync_warning(failed_jobs: list[Any], stale_since: Any) -> str | None:
    """
    Generate a warning message if there are failed synchronization jobs.

    Args:
        failed_jobs (list[Any]): List of failed job states.
        stale_since (Any): The timestamp of the last successful synchronization.
    Returns:
        str | None: A warning message if there are failed jobs, otherwise None.
    """
    if not failed_jobs:
        return None
    if stale_since:
        return (
            "Some Clash Royale data could not be synchronized. "
            f"Showing the latest available data from {format_datetime(stale_since)}."
        )
    return (
        "Some Clash Royale data could not be synchronized. "
        "No successful synchronization is available yet."
    )


def _snapshot_history_dataframe(history: list[dict[str, Any]]) -> pd.DataFrame:
    """
    Convert snapshot history data into a pandas DataFrame.

    Args:
        history (list[dict[str, Any]]): List of snapshot history records.
    Returns:
        pd.DataFrame: A DataFrame containing the snapshot history data.
    """
    if not history:
        return pd.DataFrame()
    dataframe = pd.DataFrame(history)
    dataframe["date"] = pd.to_datetime(dataframe["date"])
    return dataframe


def _member_ranking_dataframe(
    members: list[Any], value_name: str, value_getter
) -> pd.DataFrame:
    """
    Convert member ranking data into a pandas DataFrame.

    Args:
        members (list[Any]): List of member objects.
        value_name (str): The name of the column for the ranking values.
        value_getter (callable): A function to extract the ranking value from each member.

    Returns:
        pd.DataFrame: A DataFrame containing the member ranking data.
    """
    return pd.DataFrame(
        [
            {
                "Player": member.name,
                "Tag": member.tag,
                value_name: value_getter(member),
            }
            for member in members
        ]
    )


def _war_players_dataframe(players: list[Any]) -> pd.DataFrame:
    """
    Convert war player data into a pandas DataFrame.

    Args:
        players (list[Any]): List of war player objects.

    Returns:
        pd.DataFrame: A DataFrame containing the war player data.
    """
    return pd.DataFrame(
        [
            {
                "Player": player.name,
                "Tag": player.tag,
                "Fame": player.fame,
                "Repair Points": player.repair,
                "Boat Attacks": player.boats,
                "Decks Used": player.decks,
            }
            for player in players
        ]
    )


# -----------------------------------------------------------------------------
# Members
# -----------------------------------------------------------------------------


def get_member_filter_options() -> dict[str, Any]:
    """
    Retrieve available filter options for the members page.

    Returns:
        dict[str, Any]: A dictionary containing available filter options.
    """
    with get_session() as db:
        options = DashboardService(db).get_member_filter_options()
    # Streamlit sliders require different minimum and maximum bounds.
    options["trophy_slider_max"] = max(1, options["max_trophies"])
    options["donation_slider_max"] = max(1, options["max_donations"])
    return options


def get_members_page_data(
    roles: list[str],
    min_trophies: int,
    min_donations: int,
    has_contribution_score: bool,
) -> dict[str, Any]:
    """
    Retrieve and prepare data for the members page based on the provided filters.

    Args:
        roles (list[str]): List of roles to filter members by.
        min_trophies (int): Minimum trophies to filter members by.
        min_donations (int): Minimum donations to filter members by.
        has_contribution_score (bool): Whether to filter members with a contribution score.

    Returns:
        dict[str, Any]: A dictionary containing filtered members and related statistics.
    """
    with get_session() as db:
        dashboard = DashboardService(db)
        members = dashboard.get_filtered_members(
            roles=roles,
            min_trophies=min_trophies,
            min_donations=min_donations,
            has_contribution_score=has_contribution_score,
        )
        role_distribution = dashboard.get_role_distribution()

    scores = [m.contribution_score for m in members if m.contribution_score is not None]

    return {
        "summary": {
            "displayed_members": len(members),
            "average_trophies": (
                round(sum(m.trophies for m in members) / len(members)) if members else 0
            ),
            "total_donations": sum(m.donations for m in members),
            "average_score": round(sum(scores) / len(scores), 2) if scores else 0,
        },
        "members_df": pd.DataFrame(
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
                for member in members
            ]
        ),
        "trophies_df": pd.DataFrame(
            [
                {"Player": member.name, "Trophies": member.trophies}
                for member in sorted(members, key=lambda x: x.trophies, reverse=True)[
                    :10
                ]
            ]
        ),
        "donations_df": pd.DataFrame(
            [
                {"Player": member.name, "Donations": member.donations}
                for member in sorted(members, key=lambda x: x.donations, reverse=True)[
                    :10
                ]
            ]
        ),
        "contribution_df": pd.DataFrame(
            [
                {"Player": member.name, "Score": member.contribution_score}
                for member in sorted(
                    [m for m in members if m.contribution_score is not None],
                    key=lambda x: x.contribution_score,
                    reverse=True,
                )[:10]
            ]
        ),
        "role_distribution": (
            pd.DataFrame([row for row in role_distribution if row["role"] in roles])
        ),
    }


# -----------------------------------------------------------------------------
# Player profile
# -----------------------------------------------------------------------------


def get_player_options(selected_role: str | None) -> dict[str, str]:
    """
    Prepare player tags and display labels filtered by the selected role.

    Args:
        selected_role (str | None): The role to filter players by. If None, all roles are included.

    Returns:
        dict[str, str]: Player tags mapped to display labels.
    """
    with get_session() as db:
        members = DashboardService(db).get_filtered_members(
            roles=[selected_role] if selected_role else None
        )
        return {member.tag: f"{member.name} ({member.role})" for member in members}


def get_player_page_data(tag: str, refresh: bool) -> dict[str, Any] | None:
    """
    Retrieve and prepare data for the player profile page.

    Args:
        tag (str): The player's tag.
        refresh (bool): Whether to refresh the player's data from the API.

    Returns:
        dict[str, Any] | None: A dictionary containing the player's profile and related data,
        or None if the player does not exist.
    """
    with get_session() as db:
        member_service = MemberService(db)
        profile = member_service.get_player_profile(
            tag, all_stats=True, refresh=refresh
        )
        if not profile:
            return None
        history = member_service.get_member_history(profile["tag"])

    api = profile.get("api", {})
    participations = history.get("war_participations", [])
    scores = history.get("contribution_scores", [])
    snapshots = history.get("snapshots", [])

    wins = api.get("wins", 0)
    losses = api.get("losses", 0)
    total_battles = wins + losses
    score_df = _score_dataframe(scores)
    snapshot_df = _snapshot_dataframe(snapshots)
    updated_at = profile.get("api_data_updated_at")
    warning = None
    if profile.get("api_refresh_failed"):
        warning = (
            "Clash Royale profile refresh failed. Showing the latest available "
            f"data from {format_datetime(updated_at)}."
            if updated_at
            else "Clash Royale profile could not be refreshed and no cached profile data is available."
        )

    return {
        "profile": profile,
        "sync_warning": warning,
        "cache_updated_display": format_datetime(updated_at),
        "api": api,
        "last_seen_display": _last_seen_display(profile.get("last_seen")),
        "info_df": pd.DataFrame(
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
        ),
        "battle_df": pd.DataFrame(
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
        ),
        "activity_df": pd.DataFrame(
            [
                {
                    "Donations": profile["donations"],
                    "Total Donations": api.get("totalDonations"),
                    "Received": api.get("donationsReceived"),
                    "Clan Cards": api.get("clanCardsCollected"),
                }
            ]
        ),
        "winrate": round((wins / total_battles) * 100, 1) if total_battles else 0,
        "deck_df": _deck_dataframe(api.get("currentDeck", [])),
        "progress_df": pd.DataFrame(
            [
                {
                    "Current Trophies": api.get("trophies"),
                    "Best Trophies": api.get("bestTrophies"),
                    "Legacy Best": api.get("legacyTrophyRoadHighScore"),
                    "Challenge Max Wins": api.get("challengeMaxWins"),
                    "Battle Count": api.get("battleCount"),
                }
            ]
        ),
        "badge_df": _badge_dataframe(api.get("badges", [])),
        "season_results": {
            "current": api.get("currentPathOfLegendSeasonResult", {}),
            "last": api.get("lastPathOfLegendSeasonResult", {}),
            "best": api.get("bestPathOfLegendSeasonResult", {}),
        },
        "war": _player_war_data(participations),
        "score_df": score_df,
        "score_chart": (
            score_df.set_index("Date")[["Score"]]
            if not score_df.empty
            else pd.DataFrame()
        ),
        "snapshot_df": snapshot_df,
        "snapshot_chart": (
            snapshot_df.set_index("Date")[["Trophies", "Donations"]]
            if not snapshot_df.empty
            else pd.DataFrame()
        ),
    }


def _last_seen_display(last_seen: Any) -> str:
    """
    Generate a human-readable string for the last seen timestamp.

    Args:
        last_seen (Any): The last seen timestamp.
    Returns:
        str: A string representing how long ago the player was last seen, or "-" if unknown.
    """
    if not last_seen:
        return "-"
    return f"{(get_time() - last_seen).days} day(s) ago"


def _deck_dataframe(deck: list[dict[str, Any]]) -> pd.DataFrame:
    """
    Convert deck data into a pandas DataFrame.

    Args:
        deck (list[dict[str, Any]]): List of card dictionaries representing the player's deck.

    Returns:
        pd.DataFrame: A DataFrame containing the deck data.
    """
    return pd.DataFrame(
        [
            {
                "Card": card.get("name"),
                "Level": card.get("level"),
                "Evolution": card.get("evolutionLevel"),
            }
            for card in deck
        ]
    )


def _badge_dataframe(badges: list[dict[str, Any]]) -> pd.DataFrame:
    """
    Convert badge data into a pandas DataFrame.

    Args:
        badges (list[dict[str, Any]]): List of badge dictionaries.

    Returns:
        pd.DataFrame: A DataFrame containing the badge data.
    """
    return pd.DataFrame(
        [
            {
                "Badge": badge.get("name"),
                "Level": badge.get("level"),
                "Progress": badge.get("progress"),
            }
            for badge in badges
        ]
    )


def _player_war_data(participations: list[Any]) -> dict[str, Any]:
    """
    Process war participation data and return summary statistics and a DataFrame.

    Args:
        participations (list[Any]): List of war participation objects.

    Returns:
        dict[str, Any]: A dictionary containing summary statistics and a DataFrame of participations.
    """
    if not participations:
        return {
            "count": 0,
            "total_fame": 0,
            "total_boats": 0,
            "total_decks": 0,
            "df": pd.DataFrame(),
        }
    ordered = sorted(
        participations,
        key=lambda x: (x.river_race.created_date, x.river_race.section_index),
        reverse=True,
    )

    return {
        "count": len(participations),
        "total_fame": sum(p.fame for p in participations),
        "total_boats": sum(p.boat_attacks for p in participations),
        "total_decks": sum(p.decks_used for p in participations),
        "df": pd.DataFrame(
            [
                {
                    "Season": p.river_race.season_id,
                    "Race": p.river_race.section_index,
                    "Fame": p.fame,
                    "Repairs": p.repair_points,
                    "Boat": p.boat_attacks,
                    "Decks": p.decks_used,
                }
                for p in ordered
            ]
        ),
    }


def _score_dataframe(scores: list[Any]) -> pd.DataFrame:
    """
    Convert contribution score data into a pandas DataFrame.

    Args:
        scores (list[Any]): List of contribution score objects.

    Returns:
        pd.DataFrame: A DataFrame containing the contribution score data.
    """
    return pd.DataFrame(
        [
            {
                "Date": score.calculated_at,
                "Score": score.score,
                "War Activity": score.war_activity,
                "War Performance": score.war_performance,
                "Donations": score.donations,
                "Trophies": score.trophy_level,
                "Activity": score.activity,
                "Consistency": score.consistency,
                "Seniority": score.seniority,
            }
            for score in sorted(scores, key=lambda x: x.calculated_at)
        ]
    )


def _snapshot_dataframe(snapshots: list[Any]) -> pd.DataFrame:
    """
    Convert snapshot data into a pandas DataFrame.

    Args:
        snapshots (list[Any]): List of snapshot objects.
    Returns:
        pd.DataFrame: A DataFrame containing the snapshot data.
    """
    return pd.DataFrame(
        [
            {
                "Date": snapshot.collected_at,
                "Trophies": snapshot.trophies,
                "Donations": snapshot.donations,
            }
            for snapshot in sorted(snapshots, key=lambda x: x.collected_at)
        ]
    )


# -----------------------------------------------------------------------------
# Promotions
# -----------------------------------------------------------------------------


def get_promotions_page_data() -> dict[str, Any]:
    """
    Retrieve and prepare data for the promotions page.

    Returns:
        dict[str, Any]: A dictionary containing promotion recommendations and kick candidates.
    """
    with get_session() as db:
        dashboard = DashboardService(db)
        overview = dashboard.get_overview_stats()
        contribution = dashboard.get_contribution_dashboard()
        recommendations = dashboard.get_promotion_recommendations()

    ranking = pd.DataFrame(contribution["ranking"])
    recommendations_df = pd.DataFrame(recommendations)
    if not recommendations_df.empty:
        recommendations_df = recommendations_df.sort_values("rank")
        actionable = recommendations_df[recommendations_df["action"] != "no_change"]
        kick_df = recommendations_df[recommendations_df["action"] == "kick"]
    else:
        actionable = kick_df = pd.DataFrame()

    return {
        "overview": overview,
        "contribution": contribution,
        "ranking": ranking,
        "top_scores": ranking.head(15),
        "score_distribution": (
            ranking.sort_values("score") if not ranking.empty else ranking
        ),
        "top_ten": ranking.head(10),
        "components": ranking.drop(columns=["score"], errors="ignore"),
        "ranking_csv": ranking.to_csv(index=False).encode("utf-8"),
        "actionable": actionable,
        "recommendations": recommendations_df,
        "kick": kick_df,
    }


def sort_contribution_ranking(ranking: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Prepare the selected contribution component ranking."""
    return (
        ranking.sort_values(metric, ascending=False) if not ranking.empty else ranking
    )


def get_inactive_members_data(threshold: int) -> pd.DataFrame:
    """
    Retrieve a DataFrame of members who have been inactive for a specified number of days.

    Args:
        threshold (int): The number of days of inactivity to filter members by.

    Returns:
        pd.DataFrame: A DataFrame containing inactive members.
    """
    with get_session() as db:
        return pd.DataFrame(DashboardService(db).get_inactive_members(threshold))


# -----------------------------------------------------------------------------
# Wars
# -----------------------------------------------------------------------------


def get_war_overview_data() -> dict[str, Any]:
    """
    Retrieve and prepare data for the war overview page.

    Returns:
        dict[str, Any]: A dictionary containing live race status and available seasons.
    """
    with get_session() as db:
        dashboard = DashboardService(db)
        live_status = dashboard.get_current_race_status()
        return {
            "live_status": live_status,
            "not_participated": (
                pd.DataFrame(live_status["not_participated"])
                if live_status
                else pd.DataFrame()
            ),
            "season_ids": [
                season.season_id for season in dashboard.get_available_seasons()
            ],
        }


def get_war_season_data(season_id: Any, limit: int) -> dict[str, Any]:
    """
    Retrieve and prepare data for a specific war season.

    Args:
        season_id (Any): The ID of the war season.
        limit (int): The maximum number of players to retrieve.

    Returns:
        dict[str, Any]: A dictionary containing the war season data.
    """
    with get_session() as db:
        dashboard = DashboardService(db)
        top_players = dashboard.get_war_player_ranking(season_id=season_id, limit=limit)
        all_players = dashboard.get_war_player_ranking(season_id=season_id, limit=50)
        comparison = dashboard.get_race_comparison(season_id)

        return {
            "summary": dashboard.get_season_summary(season_id),
            "top_players": pd.DataFrame(top_players),
            "player_options": {
                player["member_tag"]: player["name"] for player in all_players
            },
            "races": pd.DataFrame(dashboard.get_river_races(season_id)),
            "comparison": pd.DataFrame(comparison),
        }


def get_player_war_stats_data(
    player_tag: str,
    season_id: Any,
    all_time: bool,
) -> dict[str, Any] | None:
    """
    Retrieve and prepare data for a specific player's war statistics.

    Args:
        player_tag (str): The tag of the player.
        season_id (Any): The ID of the war season.
        all_time (bool): Whether to retrieve all-time statistics.

    Returns:
        dict[str, Any] | None: A dictionary containing the player's war statistics or None if not found.
    """
    with get_session() as db:
        return DashboardService(db).get_player_war_stats(
            player_tag,
            season_id=None if all_time else season_id,
        )


# -----------------------------------------------------------------------------
# Settings
# -----------------------------------------------------------------------------


def get_settings_page_data() -> dict[str, Any]:
    """Prepare settings for display and export without exposing the API token."""
    return {
        "database": get_database_counts(),
        "clan_tag": settings.CLAN_TAG or "",
        "database_url": settings.DATABASE_URL,
        "log_level": settings.LOG_LEVEL,
        "api_token_mask": "*" * 32 if settings.CR_API_TOKEN else "",
        "environment": (
            f"Python : {python_version()}\nDashboard : Streamlit\n"
            f"Database : SQLAlchemy\nVersion : {settings.VERSION}\n"
        ),
        "configuration_export": (
            f"CLAN_TAG={settings.CLAN_TAG or ''}\n"
            f"DATABASE_URL={settings.DATABASE_URL}\nLOG_LEVEL={settings.LOG_LEVEL}\n"
        ),
    }


def get_database_counts() -> dict[str, int]:
    """
    Retrieve counts of various entities in the database.

    Returns:
        dict[str, int]: A dictionary containing counts of members, snapshots, contribution scores,
                        war seasons, river races, and participations.
    """
    models = {
        "members": Member,
        "snapshots": Snapshot,
        "contribution_scores": ContributionScore,
        "war_seasons": WarSeason,
        "river_races": RiverRace,
        "participations": WarParticipation,
    }
    with get_session() as db:
        return {
            name: db.query(count(model.id)).scalar() for name, model in models.items()
        }


def get_log_data(line_count: int) -> dict[str, Any] | None:
    """
    Retrieve log data from the specified log file.

    Args:
        line_count (int): The number of recent lines to retrieve.

    Returns:
        dict[str, Any] | None: A dictionary containing the recent and full log data or None if no log file exists.
    """
    log_path = Path(settings.LOG_FILE)
    if not log_path.exists():
        return None

    content = log_path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines(keepends=True)
    return {
        "recent": "".join(lines[-line_count:]) or "Log file is empty.",
        "full": content,
    }


def get_job_health_data() -> pd.DataFrame:
    """Display every expected job, including jobs that have never run."""
    with get_session() as db:
        states = {row.job_name: row for row in db.query(JobRunState).all()}
        rows = []
        for name in JOB_NAMES:
            state = states.get(name)
            success = state.last_success_at if state else None
            error = state.last_error if state else None
            rows.append(
                {
                    "Job": name,
                    "Status": (
                        "Failed"
                        if error
                        else ("Succeeded" if success else "Never succeeded")
                    ),
                    "Last attempt": format_datetime(
                        state.last_attempt_at if state else None
                    ),
                    "Last success": format_datetime(success),
                    "Age (hours)": (
                        round((get_time() - success).total_seconds() / 3600, 1)
                        if success
                        else None
                    ),
                    "Error": error or "",
                }
            )
        return pd.DataFrame(rows)


def get_scheduler_settings_data():
    """Return the saved schedule or defaults with a readable validation error."""
    try:
        return {"config": load_schedule(), "error": None}
    except (OSError, ValueError) as error:
        return {"config": copy.deepcopy(DEFAULT_SCHEDULE), "error": str(error)}


def save_scheduler_settings(enabled, intervals, daily):
    """Validate and persist scheduler controls from the Settings form."""
    save_schedule({"enabled": enabled, "intervals": intervals, "daily": daily})
