"""
================================================================================
Filename: test_war_identity.py
Description: Verify live-war identity guards and preservation of completed history.
Author: Raphael Smilet
Date Created: 2026-10-01
Last Modified: 2026-10-01
Version: 0.1.0
Python Version: 3.12
================================================================================
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.core.constants import MAX_LIVE_HISTORY_AGE_DAYS
from app.database.models import (
    JobRunState,
    Member,
    RiverRace,
    WarParticipation,
    WarSeason,
)
from app.scheduler import jobs
from app.services.war_service import WarService

NOW = datetime(2026, 10, 1, 12)


@pytest.fixture
def history(db_session, monkeypatch):
    """Seed authoritative history and freeze the service clock.

    Args:
        db_session: Isolated SQLAlchemy session supplied by the shared fixture.
        monkeypatch: Pytest fixture restoring the patched service clock.

    Returns:
        RiverRace: Completed synthetic race with a persisted participation.
    """
    monkeypatch.setattr("app.services.war_service.get_time", lambda: NOW)
    race = RiverRace(
        war_season=WarSeason(season_id="200", start_date=NOW - timedelta(days=30)),
        section_index=3,
        created_date=NOW - timedelta(days=3),
        is_completed=True,
    )
    member = Member(tag="#TESTPLAYER", name="Synthetic", role="member")
    db_session.add(
        WarParticipation(member=member, river_race=race, fame=2500, decks_used=16)
    )
    db_session.commit()
    return race


def api_response(section=0, **extra):
    """Build a mocked live API response without making a network request.

    Args:
        section: Live section index to include in the response.
        **extra: Additional or overridden top-level response fields.

    Returns:
        MagicMock: API client with a synthetic current-race response and empty log.
    """
    api = MagicMock()
    api.get_current_river_race.return_value = {
        "sectionIndex": section,
        "clan": {"tag": "#TEST", "participants": []},
        **extra,
    }
    api.get_river_race_log.return_value = []
    return api


@pytest.mark.parametrize(
    "age",
    [
        timedelta(days=MAX_LIVE_HISTORY_AGE_DAYS, microseconds=1),
        timedelta(days=45),
        timedelta(seconds=-1),
    ],
)
def test_untrusted_history_cannot_create_live_race(db_session, history, age):
    """Reject expired or future evidence without changing authoritative records.

    Args:
        db_session: Isolated SQLAlchemy session.
        history: Completed race fixture linked to a member and participation.
        age: Elapsed time since the completed race timestamp.

    Returns:
        None. Assertions verify rejection and retained database contents.
    """
    history.created_date = NOW - age
    db_session.commit()
    with pytest.raises(ValueError, match="Stale or future-dated"):
        WarService(db_session, api_response()).sync_current_river_race("#TEST")
    assert db_session.query(RiverRace).count() == 1
    assert db_session.query(WarSeason).count() == 1
    assert db_session.query(WarParticipation).one().fame == 2500
    assert db_session.query(RiverRace).one().is_completed


@pytest.mark.parametrize("section", [1, 5])
def test_nonadjacent_sections_are_rejected(db_session, history, section):
    """Reject backward nonzero sections and unexplained forward gaps.

    Args:
        db_session: Isolated SQLAlchemy session.
        history: Completed race fixture establishing section three.
        section: Nonadjacent live section from the synthetic response.

    Returns:
        None. Assertions verify no season or race was added.
    """
    assert history.section_index == 3
    with pytest.raises(ValueError, match="non-adjacent"):
        WarService(db_session, api_response(section)).sync_current_river_race("#TEST")
    assert db_session.query(RiverRace).count() == 1
    assert db_session.query(WarSeason).count() == 1


def test_bare_season_is_not_evidence(db_session):
    """Require completed history even when a season row is available.

    Args:
        db_session: Isolated SQLAlchemy session.

    Returns:
        None. Assertions verify the ungrounded live response is rejected.
    """
    db_session.add(WarSeason(season_id="200", start_date=NOW))
    db_session.commit()
    with pytest.raises(ValueError, match="No historical season"):
        WarService(db_session, api_response()).sync_current_river_race("#TEST")
    assert db_session.query(RiverRace).count() == 0


@pytest.mark.parametrize("section, expected_season", [(0, "201"), (4, "200")])
def test_recent_transition_is_repeatable(db_session, history, section, expected_season):
    """Accept adjacent/reset transitions once, including at the age limit.

    Args:
        db_session: Isolated SQLAlchemy session.
        history: Completed race fixture establishing the inference anchor.
        section: Reset or adjacent live section index.
        expected_season: Season identifier expected from the transition.

    Returns:
        None. Assertions verify repeated synchronization does not duplicate races.
    """
    history.created_date = NOW - timedelta(days=MAX_LIVE_HISTORY_AGE_DAYS)
    db_session.commit()
    service = WarService(db_session, api_response(section))
    service.sync_current_river_race("#TEST")
    service.sync_current_river_race("#TEST")
    live = db_session.query(RiverRace).filter_by(is_completed=False).one()
    assert live.season_id == expected_season
    assert live.section_index == section
    assert db_session.query(WarParticipation).one().fame == 2500


def test_explicit_identity_does_not_depend_on_stale_history(db_session, history):
    """Use an explicit response ID without inferring a season from old results.

    Args:
        db_session: Isolated SQLAlchemy session.
        history: Historical race deliberately made too old for inference.

    Returns:
        None. Assertions verify the explicit season is used and old fame remains.
    """
    history.created_date = NOW - timedelta(days=90)
    db_session.commit()
    WarService(db_session, api_response(2, seasonId=205)).sync_current_river_race(
        "#TEST"
    )
    assert (
        db_session.query(RiverRace).filter_by(is_completed=False).one().season_id
        == "205"
    )
    assert db_session.query(WarParticipation).one().fame == 2500


@pytest.mark.parametrize("season_id", [True, False, "", "  ", -1, 1.5, [], {}])
def test_malformed_explicit_identity_is_rejected(db_session, season_id):
    """Reject malformed explicit IDs instead of converting them into database keys.

    Args:
        db_session: Isolated SQLAlchemy session.
        season_id: Invalid explicit season identifier supplied by parametrization.

    Returns:
        None. Assertions verify no season or race is stored.
    """
    with pytest.raises(ValueError, match="Invalid explicit"):
        WarService(
            db_session, api_response(seasonId=season_id)
        ).sync_current_river_race("#TEST")
    assert db_session.query(WarSeason).count() == 0
    assert db_session.query(RiverRace).count() == 0


@pytest.mark.parametrize("section", [True, False, -1, "0"])
def test_invalid_live_section_is_rejected(db_session, section):
    """Treat booleans, negative values, and strings as invalid section indices.

    Args:
        db_session: Isolated SQLAlchemy session.
        section: Invalid live section value.

    Returns:
        None. Assertions verify the response cannot create a race.
    """
    with pytest.raises(ValueError, match="section index"):
        WarService(
            db_session, api_response(section, seasonId=201)
        ).sync_current_river_race("#TEST")
    assert db_session.query(RiverRace).count() == 0


def test_missing_clan_identity_is_rejected(db_session):
    """Require the requested clan tag in the live response.

    Args:
        db_session: Isolated SQLAlchemy session.

    Returns:
        None. Assertions verify an anonymous clan cannot create a race.
    """
    api = api_response(seasonId=201, clan={"participants": []})
    with pytest.raises(ValueError, match="mismatched live race clan"):
        WarService(db_session, api).sync_current_river_race("#TEST")
    assert db_session.query(RiverRace).count() == 0


def test_guard_failure_is_visible_in_job_health(db_session, history, monkeypatch):
    """Persist an actionable job error when current-war identity cannot be trusted.

    Args:
        db_session: Isolated SQLAlchemy session.
        history: Completed race made too old for live identity inference.
        monkeypatch: Pytest fixture replacing API-backed job dependencies.

    Returns:
        None. Assertions verify failure reporting and unchanged authoritative fame.
    """
    history.created_date = NOW - timedelta(days=90)
    db_session.commit()
    api = api_response()
    monkeypatch.setattr(jobs, "WarService", lambda db: WarService(db, api))
    monkeypatch.setattr(jobs.settings, "CLAN_TAG", "#TEST")
    assert not jobs.update_war_data(db_session)
    state = db_session.query(JobRunState).filter_by(job_name="update_war_data").one()
    assert "refresh war history" in state.last_error
    assert state.last_success_at is None
    assert db_session.query(WarParticipation).one().fame == 2500
