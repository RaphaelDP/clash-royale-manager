"""
================================================================================
Filename: test_reliability.py
Description: Regression tests for packaging, migrations, synchronization, caching, and scheduling.
Author: Raphael Smilet
Date Created: 2026-09-30
Last Modified: 2026-09-30
Version: 0.1.0
Python Version: 3.12
================================================================================
"""

# Tenacity decorates methods dynamically; API sessions are mocked in these tests.
# pylint: disable=no-member

from contextlib import closing, nullcontext
import copy
from datetime import datetime, timedelta
import json
import sqlite3
from unittest.mock import MagicMock
from zipfile import ZipFile

from alembic import command
from apscheduler.schedulers.background import BackgroundScheduler
import pytest
import requests
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session
from tenacity import wait_none

from app.core.job_lock import job_lock
from app.database.base import Base
from app.database.models import (
    Member,
    RiverRace,
    WarSeason,
    WarParticipation,
    Snapshot,
    JobRunState,
)
from app.scheduler import scheduler as module
from app.scheduler import jobs
from app.services.clan_service import ClanService
from app.services.clash_api import ClashAPIClient
from app.services.dashboard_service import DashboardService
from app.services.member_service import MemberService
from app.services.scheduler_config import (
    DEFAULT_SCHEDULE,
    save_schedule,
    load_schedule,
    validate_schedule,
)
from app.services.snapshot_service import SnapshotService
from app.services.war_service import WarService
from scripts.init_db import init_db, migration_config
from scripts.package_release import build_archive
from scripts.restore_db import restore_database


def test_archive_rebuild_drops_old_secrets_and_preserves_migrations(tmp_path):
    """Archive rebuild drops old secrets and preserves migrations."""
    root = tmp_path / "project"
    (root / "app/database/migrations/versions").mkdir(parents=True)
    (root / "app/database/migrations/versions/test.py").write_text("pass")
    (root / ".env.example").write_text("EXAMPLE=")
    (root / ".env").write_text("synthetic-test-secret")
    (root / "backups").mkdir()
    (root / "backups/test.db").write_text("synthetic")
    (root / "app/private-link").symlink_to(root / ".env")
    destination = tmp_path / "release.zip"
    with ZipFile(destination, "w") as archive:
        archive.writestr(".env", "old-synthetic-secret")
    build_archive(root, destination)
    with ZipFile(destination) as archive:
        assert set(archive.namelist()) == {
            ".env.example",
            "app/database/migrations/versions/test.py",
        }


def test_fresh_schema_matches_models_and_repeated_init(tmp_path):
    """Fresh schema matches models and repeated init."""
    engine = create_engine(f"sqlite:///{tmp_path / 'fresh.db'}")
    init_db(engine)
    init_db(engine)
    inspector = inspect(engine)
    for name, table in Base.metadata.tables.items():
        assert {column["name"] for column in inspector.get_columns(name)} == set(
            table.columns.keys()
        )
    engine.dispose()


def test_repair_already_stamped_schema_preserves_members(tmp_path):
    """Repair already stamped schema preserves members."""
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        command.upgrade(migration_config(connection), "f117b96b7d59")
        connection.execute(text("ALTER TABLE members DROP COLUMN days_in_clan"))
        connection.execute(
            text(
                "INSERT INTO members (id, tag, name, role, trophies, donations) "
                "VALUES (1, '#TEST', 'Test', 'member', 10, 0)"
            )
        )
    init_db(engine)
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT name, days_in_clan FROM members")
        ).one() == ("Test", 0)
    engine.dispose()


def test_unversioned_current_schema_adoption_preserves_history(tmp_path):
    """Unversioned current schema adoption preserves history."""
    engine = create_engine(f"sqlite:///{tmp_path / 'unversioned.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Member(tag="#TEST", name="Test", role="member", days_in_clan=42))
        db.commit()
    init_db(engine)
    with Session(engine) as db:
        assert db.query(Member).one().days_in_clan == 42
    engine.dispose()


def test_unknown_schema_is_not_stamped(tmp_path):
    """Unknown schema is not stamped."""
    engine = create_engine(f"sqlite:///{tmp_path / 'unknown.db'}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE unrelated (id INTEGER)"))
    with pytest.raises(RuntimeError, match="Unrecognized"):
        init_db(engine)
    assert "alembic_version" not in inspect(engine).get_table_names()
    engine.dispose()


def test_upgrade_from_initial_schema_preserves_member_data(tmp_path):
    """Upgrade from initial schema preserves member data."""
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as connection:
        command.upgrade(migration_config(connection), "67a87d4beb2d")
        connection.execute(
            text(
                "INSERT INTO members (id, tag, name, role, trophies, donations, clan_joined_at) "
                "VALUES (1, '#TEST', 'Test', 'member', 10, 0, '2026-01-01 00:00:00')"
            )
        )
    init_db(engine)
    with Session(engine) as db:
        assert db.query(Member).one().days_in_clan > 0
    engine.dispose()


def test_roster_failure_rolls_back_earlier_member_changes(db_session, member_factory):
    """Roster failure rolls back earlier member changes."""
    member = member_factory(tag="#A", name="Original")
    db_session.add(member)
    db_session.commit()
    api = MagicMock()
    api.get_clan.return_value = {
        "memberList": [
            {"tag": "#A", "name": "Changed", "role": "member"},
            {"tag": "#B", "name": "Bad", "role": "member", "lastSeen": "invalid"},
        ]
    }
    with pytest.raises(ValueError):
        ClanService(db_session, api).sync_clan_members("#TEST")
    db_session.expire_all()
    assert db_session.query(Member).one().name == "Original"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"memberList": None},
        {"members": 2, "memberList": []},
        {"memberList": [{"tag": "#A"}]},
    ],
)
def test_incomplete_roster_cannot_mark_members_departed(
    db_session, member_factory, payload
):
    """Incomplete roster cannot mark members departed."""
    member = member_factory(role="member")
    db_session.add(member)
    db_session.commit()
    api = MagicMock()
    api.get_clan.return_value = payload
    with pytest.raises(ValueError):
        ClanService(db_session, api).sync_clan_members("#TEST")
    assert db_session.query(Member).one().role == "member"


def seed_race(db, season="200", section=3, completed=True):
    """Seed race."""
    member = Member(tag="#A", name="A", role="member")
    race = RiverRace(
        war_season=WarSeason(season_id=season, start_date=datetime(2026, 9, 1)),
        section_index=section,
        created_date=datetime(2026, 9, 28),
        is_completed=completed,
    )
    db.add(WarParticipation(member=member, river_race=race, fame=2500, decks_used=16))
    db.commit()
    return race


def test_live_season_uses_chronology_and_rollover(db_session):
    """Live season uses chronology and rollover."""
    seed_race(db_session)
    db_session.add(WarSeason(season_id="199", start_date=datetime(2026, 8, 1)))
    db_session.commit()
    api = MagicMock()
    api.get_current_river_race.return_value = {
        "clan": {"tag": "#TEST", "participants": []},
        "sectionIndex": 0,
    }
    WarService(db_session, api).sync_current_river_race("#TEST")
    assert (
        db_session.query(RiverRace).filter_by(is_completed=False).one().season_id
        == "201"
    )


def test_live_response_cannot_overwrite_completed_results(db_session):
    """Live response cannot overwrite completed results."""
    race = seed_race(db_session)
    api = MagicMock()
    api.get_current_river_race.return_value = {
        "clan": {"tag": "#TEST", "participants": [{"tag": "#A", "fame": 0}]},
        "sectionIndex": race.section_index,
    }
    WarService(db_session, api).sync_current_river_race("#TEST")
    assert db_session.query(WarParticipation).one().fame == 2500


def test_failed_war_batch_rolls_back_all_races(db_session):
    """Failed war batch rolls back all races."""
    api = MagicMock()
    api.get_river_race_log.return_value = [
        {
            "seasonId": 200,
            "sectionIndex": 0,
            "createdDate": "20260901T090000.000Z",
            "standings": [
                {"clan": {"tag": "#TEST", "participants": [{"tag": "#A", "name": "A"}]}}
            ],
        },
        {"seasonId": 200, "sectionIndex": 1, "createdDate": "invalid"},
    ]
    with pytest.raises(ValueError):
        WarService(db_session, api).sync_river_race_log("#TEST")
    assert db_session.query(RiverRace).count() == 0
    assert db_session.query(Member).count() == 0


def test_unknown_activity_and_zero_decks(db_session):
    """Unknown activity and zero decks."""
    seed_race(db_session, completed=False)
    participation = db_session.query(WarParticipation).one()
    participation.decks_used = 0
    db_session.commit()
    dashboard = DashboardService(db_session, MagicMock())
    assert dashboard.get_inactivity_ranking()[0]["days_since_last_seen"] is None
    assert dashboard.get_current_race_status()["participated_count"] == 0


def test_automatic_snapshots_are_active_only_and_idempotent(db_session, member_factory):
    """Automatic snapshots are active only and idempotent."""
    db_session.add_all([member_factory(role="member"), member_factory(role="left")])
    db_session.commit()
    service = SnapshotService(db_session)
    assert len(service.create_daily_snapshots(None)) == 1
    assert not service.create_daily_snapshots(None)
    assert db_session.query(Snapshot).count() == 1


def test_corrupt_profile_cache_recovers_and_refresh_bypasses_http_cache(
    tmp_path, monkeypatch, db_session, member_factory
):
    """Corrupt profile cache recovers and refresh bypasses http cache."""
    monkeypatch.chdir(tmp_path)
    member = member_factory(tag="#ABC")
    db_session.add(member)
    db_session.commit()
    path = tmp_path / "data/cache/players/ABC.json"
    path.parent.mkdir(parents=True)
    path.write_text("{broken")
    api = MagicMock()
    api.get_player.return_value = {"wins": 4}
    result = MemberService(db_session, api).get_player_profile(
        "#ABC", all_stats=True, refresh=True
    )
    assert result["api"] == {"wins": 4}
    api.get_player.assert_called_once_with("#ABC", refresh=True)
    assert json.loads(path.read_text()) == {"wins": 4}
    api.get_player.side_effect = RuntimeError("offline")
    result = MemberService(db_session, api).get_player_profile(
        "#ABC", all_stats=True, refresh=True
    )
    assert result["api_refresh_failed"]
    assert result["api"] == {"wins": 4}


def test_corrupt_cache_and_failed_api_returns_empty_fallback(
    tmp_path, monkeypatch, db_session, member_factory
):
    """Corrupt cache and failed api returns empty fallback."""
    monkeypatch.chdir(tmp_path)
    db_session.add(member_factory(tag="#ABC"))
    db_session.commit()
    path = tmp_path / "data/cache/players/ABC.json"
    path.parent.mkdir(parents=True)
    path.write_text("{broken")
    api = MagicMock()
    api.get_player.side_effect = RuntimeError("offline")
    result = MemberService(db_session, api).get_player_profile("#ABC", all_stats=True)
    assert result["api"] == {}
    assert result["api_refresh_failed"]


def test_schedule_validation_and_atomic_persistence(tmp_path, monkeypatch):
    """Schedule validation and atomic persistence."""
    path = tmp_path / "scheduler.json"
    monkeypatch.setenv("SCHEDULER_CONFIG_FILE", str(path))
    schedule = load_schedule()
    schedule["intervals"]["update_clan_members"] = 15
    save_schedule(schedule)
    assert load_schedule() == schedule
    invalid = copy.deepcopy(schedule)
    invalid["daily"]["backup_database"] = "99:99"
    with pytest.raises(ValueError):
        save_schedule(invalid)
    assert load_schedule() == schedule


@pytest.mark.parametrize("value", [0, -1, True, 1441, 1.5])
def test_reject_invalid_intervals(value):
    """Reject invalid intervals."""
    schedule = copy.deepcopy(DEFAULT_SCHEDULE)
    schedule["intervals"]["update_war_data"] = value
    with pytest.raises(ValueError):
        validate_schedule(schedule)


def test_daily_job_repeated_success_runs_once(db_session, tmp_path, monkeypatch):
    """Daily job repeated success runs once."""
    monkeypatch.setenv("JOB_LOCK_DIR", str(tmp_path))
    calls = []
    for _ in range(2):
        assert jobs._run_job(
            "daily_test", lambda db: calls.append(1), db_session, daily=True
        )
    assert calls == [1]


def test_failed_daily_job_can_retry(db_session, tmp_path, monkeypatch):
    """Failed daily job can retry."""
    monkeypatch.setenv("JOB_LOCK_DIR", str(tmp_path))

    def fail(db):
        raise ValueError("failed")

    assert not jobs._run_job("daily_test", fail, db_session, daily=True)
    assert jobs._run_job("daily_test", lambda db: None, db_session, daily=True)
    assert db_session.query(JobRunState).one().last_error is None


def test_job_lock_prevents_overlap(tmp_path, monkeypatch):
    """Job lock prevents overlap."""
    monkeypatch.setenv("JOB_LOCK_DIR", str(tmp_path))
    with job_lock("test") as first:
        with job_lock("test") as second:
            assert first and not second
    with job_lock("test") as third:
        assert third


def test_backup_job_reports_missing_backup(db_session, monkeypatch):
    """Backup job reports missing backup."""
    monkeypatch.setattr(jobs, "run_database_backup", lambda: None)
    assert not jobs.backup_database(db_session)
    assert "No database backup" in db_session.query(JobRunState).one().last_error


def test_restore_roundtrip_and_existing_destination(tmp_path):
    """Restore roundtrip and existing destination."""
    source, destination = tmp_path / "backup.db", tmp_path / "restored.db"
    with closing(sqlite3.connect(source)) as db:
        db.execute("CREATE TABLE example (value INTEGER)")
        db.execute("INSERT INTO example VALUES (42)")
        db.commit()
    original = source.read_bytes()
    restore_database(source, destination)
    with closing(sqlite3.connect(destination)) as db:
        assert db.execute("SELECT value FROM example").fetchone() == (42,)
    assert source.read_bytes() == original
    with pytest.raises(FileExistsError):
        restore_database(source, destination)


def test_invalid_restore_preserves_destination(tmp_path):
    """Invalid restore preserves destination."""
    source, destination = tmp_path / "invalid.db", tmp_path / "existing.db"
    source.write_bytes(b"not sqlite")
    destination.write_bytes(b"preserve this")
    with pytest.raises(sqlite3.DatabaseError):
        restore_database(source, destination, replace=True)
    assert destination.read_bytes() == b"preserve this"


def test_scheduler_runtime_reload_and_invalid_config(db_session, tmp_path, monkeypatch):
    """Scheduler runtime reload and invalid config."""
    path = tmp_path / "scheduler.json"
    monkeypatch.setenv("SCHEDULER_CONFIG_FILE", str(path))
    monkeypatch.setattr(module, "SessionLocal", lambda: nullcontext(db_session))
    scheduler = BackgroundScheduler()
    scheduler.start(paused=True)
    try:
        schedule = save_schedule(copy.deepcopy(DEFAULT_SCHEDULE))
        module.apply_schedule(scheduler, schedule, catch_up=True)
        scheduler.runtime_config = copy.deepcopy(schedule)
        assert len(scheduler.get_jobs()) == 7
        schedule["enabled"] = False
        save_schedule(schedule)
        module.reload_scheduler(scheduler)
        assert not scheduler.get_jobs()
        schedule["enabled"] = True
        schedule["intervals"]["update_war_data"] = 12
        save_schedule(schedule)
        module.reload_scheduler(scheduler)
        assert scheduler.get_job("update_war_data").trigger.interval == timedelta(
            minutes=12
        )
        path.write_text("{invalid")
        module.reload_scheduler(scheduler)
        assert len(scheduler.get_jobs()) == 7
    finally:
        scheduler.shutdown()


def test_api_forbidden_is_not_retried():
    """Api forbidden is not retried."""
    client = ClashAPIClient.__new__(ClashAPIClient)
    client.base_url, client.headers, client.session = (
        "https://example.invalid",
        {},
        MagicMock(),
    )
    response = requests.Response()
    response.status_code = 403
    client.session.get.side_effect = requests.HTTPError(response=response)
    with pytest.raises(requests.HTTPError):
        ClashAPIClient._request.retry_with(wait=wait_none())(client, "/test")
    assert client.session.get.call_count == 1


def test_api_connection_failure_is_retried():
    """Api connection failure is retried."""
    client = ClashAPIClient.__new__(ClashAPIClient)
    client.base_url, client.headers, client.session = (
        "https://example.invalid",
        {},
        MagicMock(),
    )
    response = MagicMock()
    response.json.return_value = {"ok": True}
    client.session.get.side_effect = [requests.ConnectionError("offline"), response]
    assert ClashAPIClient._request.retry_with(wait=wait_none())(client, "/test") == {
        "ok": True
    }
    assert client.session.get.call_count == 2


def test_player_refresh_disables_http_cache():
    """Player refresh disables http cache."""
    client = ClashAPIClient.__new__(ClashAPIClient)
    client.session, client._request = MagicMock(), MagicMock()
    client.get_player("#ABC", refresh=True)
    client.session.cache_disabled.assert_called_once_with()
    client._request.assert_called_once_with("/players/%23ABC")
