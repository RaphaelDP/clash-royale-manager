"""
Filename: test_war_training.py
Description: Verify training exclusion, phase transitions and historical preservation.
Author: Raphael Smilet
Date Created: 2026-10-06
Last Modified: 2026-10-07
Version: 0.1.1
"""

from unittest.mock import MagicMock
import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from scripts.init_db import migration_config
from app.core.utils import get_time
from app.database.models import Member, RiverRace, WarParticipation, WarSeason
from app.services.war_service import WarService
from app.services.dashboard_service import DashboardService


def payload(phase="training", period=1):
    """Create an API snapshot with synthetic practice counters that must not be counted.

    Args:
        phase: API phase name.
        period: API season day index.

    Returns:
        dict: Synthetic current river race.
    """
    return {
        "seasonId": "137",
        "sectionIndex": 0,
        "periodType": phase,
        "periodIndex": period,
        "clan": {
            "tag": "#TEST",
            "participants": [
                {
                    "tag": "#PLAYER",
                    "name": "Player",
                    "fame": 500,
                    "decksUsed": 4,
                    "decksUsedToday": 4,
                }
            ],
        },
    }


def test_training_creates_weekly_race_without_participation(db_session):
    """Persist Training day 2 on the weekly race without counting practice as war attendance.

    Args:
        db_session: Isolated database fixture.

    Returns:
        None. Assertions verify no scored records and no nonparticipant warnings.
    """
    api = MagicMock()
    api.get_current_river_race.return_value = payload()
    WarService(db_session, api).sync_current_river_race("#TEST")
    assert db_session.query(RiverRace).one().type_of_day == "training"
    assert db_session.query(WarParticipation).count() == 0
    status = DashboardService(db_session, api).get_current_race_status()
    assert status["phase"] == "training"
    assert status["training_day"] == 2
    assert status["not_participated"] == []
    assert "not_participated_count" not in status


@pytest.mark.parametrize("phase", ["warDay", "colosseum"])
def test_training_to_battle_and_stale_training_protection(db_session, phase):
    """Start counting on battle days and reject training responses that go backward.

    Args:
        db_session: Isolated database fixture.
        phase: Regular or Colosseum battle phase.

    Returns:
        None. Assertions verify scoring starts and stale training cannot erase it.
    """
    api = MagicMock()
    service = WarService(db_session, api)
    api.get_current_river_race.return_value = payload()
    service.sync_current_river_race("#TEST")
    api.get_current_river_race.return_value = payload(phase, 3)
    service.sync_current_river_race("#TEST")
    assert db_session.query(WarParticipation).one().decks_used == 4
    assert db_session.query(RiverRace).one().type_of_day == "battle"
    api.get_current_river_race.return_value = payload()
    with pytest.raises(ValueError):
        service.sync_current_river_race("#TEST")
    assert db_session.query(WarParticipation).one().fame == 500
    assert db_session.query(RiverRace).one().type_of_day == "battle"


@pytest.mark.parametrize("completed", [False, True])
def test_training_corrects_only_uncompleted_legacy_snapshots(db_session, completed):
    """Exclude prior training imports without deleting authoritative completed history.

    Args:
        db_session: Isolated database fixture.
        completed: Whether the existing row is authoritative history.

    Returns:
        None. Assertions verify only uncompleted training participation is removed.
    """
    race = RiverRace(
        war_season=WarSeason(season_id="137", start_date=get_time()),
        section_index=0,
        created_date=get_time(),
        is_completed=completed,
    )
    member = Member(tag="#PLAYER", name="Player", role="member")
    db_session.add(
        WarParticipation(member=member, river_race=race, fame=500, decks_used=4)
    )
    db_session.commit()
    api = MagicMock()
    api.get_current_river_race.return_value = payload()
    WarService(db_session, api).sync_current_river_race("#TEST")
    assert db_session.query(RiverRace).count() == 1
    assert db_session.query(WarParticipation).count() == int(completed)
    assert db_session.query(Member).count() == 1


def test_phase_migration_preserves_weekly_identity(tmp_path):
    """Move legacy phase metadata onto a race and preserve it across downgrade.

    Args:
        tmp_path: Isolated temporary directory.

    Returns:
        None. Assertions verify migration data and schema integrity.
    """
    engine = create_engine(f"sqlite:///{tmp_path / 'migration.db'}")
    with engine.begin() as connection:
        config = migration_config(connection)
        command.upgrade(config, "a2026100601")
        connection.execute(
            text(
                "INSERT INTO war_phase "
                "(id, period_type, period_index, section_index, season_id, observed_at) "
                "VALUES (1, 'training', 1, 0, '137', '2026-10-06 12:00:00')"
            )
        )
        command.upgrade(config, "head")
        assert "war_phase" not in inspect(connection).get_table_names()
        row = connection.execute(
            text(
                "SELECT season_id, section_index, type_of_day, period_index FROM river_races"
            )
        ).one()
        assert tuple(row) == ("137", 0, "training", 1)
        command.downgrade(config, "a2026100601")
        assert (
            connection.execute(text("SELECT period_type FROM war_phase")).scalar()
            == "training"
        )
        command.upgrade(config, "head")
        assert (
            connection.execute(text("SELECT count(*) FROM river_races")).scalar() == 1
        )
    engine.dispose()


def test_training_does_not_inflate_season_statistics(db_session):
    """Keep the weekly training row out of battle statistics.

    Args:
        db_session: Isolated database fixture.

    Returns:
        None. Assertions verify training exclusion.
    """
    api = MagicMock()
    api.get_current_river_race.return_value = payload()
    WarService(db_session, api).sync_current_river_race("#TEST")
    service = DashboardService(db_session, api)
    assert service.get_season_summary("137")["race_count"] == 0
