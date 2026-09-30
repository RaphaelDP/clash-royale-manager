"""
================================================================================
Filename: test_dashboard_pages.py
Description: Integration tests for dashboard pages, data preparation, and actions.
Author: Raphael Smilet
Date Created: 2026-09-30
Last Modified: 2026-09-30
Version: 0.1.1
Python Version: 3.12
Dependencies: pytest, sqlalchemy, streamlit.testing, dashboard.functions
================================================================================
"""

# Pytest fixtures and patched API signatures require these parameters.
# pylint: disable=unused-argument


from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from streamlit.testing.v1 import AppTest

from app.core.utils import get_time
from app.database.base import Base
from app.database.models import Member, Snapshot, WarSeason, RiverRace, WarParticipation
from app.services.dashboard_service import DashboardService
from app.services.member_service import MemberService
from app.services.score_service import ScoreService
from dashboard import functions

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["home.py"] + [
    f"pages/{path.name}" for path in sorted((ROOT / "dashboard/pages").glob("*.py"))
]


@pytest.fixture
def dashboard_db(tmp_path, monkeypatch):
    """Dashboard db."""
    monkeypatch.setenv("SCHEDULER_CONFIG_FILE", str(tmp_path / "scheduler.json"))
    engine = create_engine(f"sqlite:///{tmp_path / 'dashboard.db'}")
    Base.metadata.create_all(engine)
    api = MagicMock()

    @contextmanager
    def session():
        with Session(engine) as db:
            yield db

    monkeypatch.setattr(functions, "get_session", session)
    monkeypatch.setattr(
        functions,
        "DashboardService",
        lambda db, api_clash=None: DashboardService(db, api),
    )
    monkeypatch.setattr(functions, "MemberService", lambda db: MemberService(db, api))
    monkeypatch.setattr(functions.settings, "CR_API_TOKEN", "test-token")
    monkeypatch.setattr(functions.settings, "CLAN_TAG", "#TEST")
    monkeypatch.setattr(functions.settings, "LOG_FILE", str(tmp_path / "missing.log"))

    def profile(service, tag, all_stats=False, refresh=False):
        member = service.db.query(Member).filter_by(tag=tag).first()
        if member is None:
            return {}
        return {
            **member.to_dict(),
            "api": {
                "wins": 3,
                "losses": 1,
                "currentDeck": [{"name": "Knight", "level": 10}],
                "badges": [{"name": "Test", "level": 1}],
            },
            "api_refresh_failed": refresh,
            "api_data_updated_at": get_time(),
        }

    monkeypatch.setattr(MemberService, "get_player_profile", profile)
    yield session
    engine.dispose()


@pytest.fixture
def populated_dashboard(dashboard_db):
    """Populated dashboard."""
    now = get_time()
    with dashboard_db() as db:
        leader = Member(
            tag="#LEADER",
            name="Leader",
            role="leader",
            trophies=0,
            donations=0,
            last_seen=now,
            days_in_clan=30,
        )
        member = Member(
            tag="#MEMBER",
            name="Member",
            role="member",
            trophies=0,
            donations=0,
            last_seen=now - timedelta(days=20),
            days_in_clan=30,
        )
        season = WarSeason(season_id="200", start_date=now - timedelta(days=14))
        completed = RiverRace(
            war_season=season,
            section_index=0,
            created_date=now - timedelta(days=7),
            is_completed=True,
        )
        live = RiverRace(
            war_season=season, section_index=1, created_date=now, is_completed=False
        )
        db.add_all(
            [
                leader,
                member,
                Snapshot(member=leader, trophies=0, donations=0, collected_at=now),
                WarParticipation(
                    member=leader, river_race=completed, fame=3000, decks_used=16
                ),
                WarParticipation(
                    member=member, river_race=completed, fame=500, decks_used=4
                ),
                WarParticipation(member=leader, river_race=live, fame=0, decks_used=0),
            ]
        )
        db.commit()
        ScoreService(db).calculate_all_scores()
    return dashboard_db


@pytest.mark.parametrize("page", PAGES)
def test_pages_render_empty_database(dashboard_db, page):
    """Pages render empty database."""
    app = AppTest.from_file(str(ROOT / "dashboard" / page)).run()
    assert not app.exception, [error.message for error in app.exception]


@pytest.mark.parametrize("page", PAGES)
def test_pages_render_populated_database(populated_dashboard, page):
    """Pages render populated database."""
    app = AppTest.from_file(str(ROOT / "dashboard" / page)).run()
    assert not app.exception, [error.message for error in app.exception]


def test_player_refresh_and_role_selection(populated_dashboard):
    """Player refresh and role selection."""
    app = AppTest.from_file(str(ROOT / "dashboard/pages/_03_player.py")).run()
    assert len(app.button) == 1
    app.button[0].click().run()
    assert not app.exception
    assert any("latest available data" in warning.value for warning in app.warning)
    app.selectbox[0].select("member").run()
    assert not app.exception
    assert app.header[0].value == "Member"


def test_player_data_is_usable_after_session_closes(populated_dashboard):
    """Player data is usable after session closes."""
    data = functions.get_player_page_data("#LEADER", refresh=False)
    assert data["winrate"] == 75
    assert data["war"]["total_fame"] == 3000
    assert len(data["war"]["df"]) == 2
    assert not data["score_chart"].empty
    assert not data["snapshot_chart"].empty


def test_promotions_and_war_controls(populated_dashboard):
    """Promotions and war controls."""
    app = AppTest.from_file(str(ROOT / "dashboard/pages/_04_promotions.py")).run()
    app.selectbox[0].select("war_activity").run()
    app.slider[0].set_value(30).run()
    assert not app.exception
    app = AppTest.from_file(str(ROOT / "dashboard/pages/_05_wars.py")).run()
    app.slider[0].set_value(1).run()
    app.checkbox[0].check().run()
    assert not app.exception


def test_failed_refresh_is_visible_and_unlocks(populated_dashboard, monkeypatch):
    """Failed refresh is visible and unlocks."""
    monkeypatch.setattr(functions, "update_war_data", lambda **kwargs: False)
    app = AppTest.from_file(str(ROOT / "dashboard/pages/_05_wars.py")).run()
    app.button[0].click().run()
    assert not app.exception
    assert any("action failed" in error.value for error in app.error)
    assert app.session_state["dashboard_action_running"] is False


def test_member_filters_and_exports(populated_dashboard):
    """Member filters and exports."""
    data = functions.get_members_page_data(["leader"], 0, 0, False)
    assert data["summary"]["displayed_members"] == 1
    assert data["role_distribution"]["role"].tolist() == ["leader"]
    assert functions.get_members_page_data([], 0, 0, False)["members_df"].empty
    promotions = functions.get_promotions_page_data()
    assert promotions["ranking_csv"].startswith(b"name,score,")
    settings = functions.get_settings_page_data()
    assert "test-token" not in settings["configuration_export"]
    assert settings["api_token_mask"] == "*" * 32
