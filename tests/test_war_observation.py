"""
================================================================================
Filename: test_war_observation.py
Description: Verify qualification evidence and recovery across live-war transitions.
Author: Raphael Smilet
Date Created: 2026-10-02
Last Modified: 2026-10-02
Version: 0.1.1
Python Version: 3.12
================================================================================
"""

import json
from datetime import timedelta
from unittest.mock import MagicMock

import pytest

from app.core.utils import get_time
from app.database.models import RiverRace
from app.services.war_service import WarService
from scripts.observe_war_identity import run_worker


def responses(season=200, section=3, age=3):
    """Build historical and live API fixtures with distinct private markers.

    Args:
        season: Completed race season identifier.
        section: Completed race section index.
        age: Completed race age in days.

    Returns:
        MagicMock: Client with a completed race and a reset-to-zero live response.
    """
    client = MagicMock()
    clan = {"tag": "#PRIVATE", "participants": []}
    client.get_river_race_log.return_value = [
        {
            "seasonId": season,
            "sectionIndex": section,
            "createdDate": (get_time() - timedelta(days=age)).strftime(
                "%Y%m%dT%H%M%S.000Z"
            ),
            "standings": [{"clan": clan}],
        }
    ]
    client.get_current_river_race.return_value = {"sectionIndex": 0, "clan": clan}
    return client


def test_observation_excludes_private_payload(db_session):
    """Emit only projected race identity fields from live synchronization.

    Args:
        db_session: Disposable application database session.

    Returns:
        None. Assertions verify privacy and the inferred next-season identity.
    """
    client = responses()
    result = WarService(db_session, client).observe_identity("#PRIVATE")
    client.session.cache_disabled.assert_called_once_with()
    client.get_river_race_log.assert_called_once_with("#PRIVATE")
    client.get_current_river_race.assert_called_once_with("#PRIVATE")
    assert result["ok"]
    assert not result["explicit_live_season"]
    assert "PRIVATE" not in json.dumps(result)
    assert [(r["season"], r["section"], r["completed"]) for r in result["races"]] == [
        ("200", 3, True),
        ("201", 0, False),
    ]
    assert all(
        set(row) == {"season", "section", "completed", "timestamp"}
        for row in result["races"]
    )


def test_rollover_live_identity_is_confirmed_by_history(db_session):
    """Complete the inferred race in place and open the next section without duplicates.

    Args:
        db_session: Disposable application database session.

    Returns:
        None. Assertions verify identity continuity and completed-state protection.
    """
    client = responses()
    service = WarService(db_session, client)
    service.sync_river_race_log("#PRIVATE")
    service.sync_current_river_race("#PRIVATE")
    live_id = db_session.query(RiverRace).filter_by(is_completed=False).one().id
    client.get_river_race_log.return_value = responses(
        201, 0, 1
    ).get_river_race_log.return_value
    service.sync_river_race_log("#PRIVATE")
    service.sync_current_river_race("#PRIVATE")  # Lagging endpoint must not reopen it.
    assert db_session.get(RiverRace, live_id).is_completed
    assert db_session.query(RiverRace).count() == 2
    client.get_current_river_race.return_value["sectionIndex"] = 1
    service.sync_current_river_race("#PRIVATE")
    service.sync_current_river_race("#PRIVATE")
    assert db_session.query(RiverRace).count() == 3
    live = db_session.query(RiverRace).filter_by(is_completed=False).one()
    assert (live.season_id, live.section_index) == ("201", 1)


def test_stale_history_recovers_after_completed_log_refresh(db_session):
    """Reject a long gap, then recover when authoritative recent history arrives.

    Args:
        db_session: Disposable application database session.

    Returns:
        None. Assertions verify safe refusal and subsequent successful recovery.
    """
    client = responses(age=45)
    service = WarService(db_session, client)
    service.sync_river_race_log("#PRIVATE")
    with pytest.raises(ValueError, match="Stale"):
        service.sync_current_river_race("#PRIVATE")
    client.get_river_race_log.return_value = responses(
        202, 2, 1
    ).get_river_race_log.return_value
    client.get_current_river_race.return_value["sectionIndex"] = 3
    service.sync_river_race_log("#PRIVATE")
    service.sync_current_river_race("#PRIVATE")
    assert db_session.query(RiverRace).filter_by(is_completed=True).count() == 2
    live = db_session.query(RiverRace).filter_by(is_completed=False).one()
    assert (live.season_id, live.section_index) == ("202", 3)


def test_worker_refuses_production_configuration(monkeypatch):
    """Refuse internal worker execution unless temporary configuration is present.

    Args:
        monkeypatch: Fixture restoring modified environment variables.

    Returns:
        None. Assertions verify the worker refuses a file-backed database.
    """
    monkeypatch.setenv("DATABASE_URL", "sqlite:///production.db")
    assert run_worker() == {"ok": False, "error_type": "IsolationRequired"}
