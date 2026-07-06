"""
================================================================================
Filename: conftest.py
Description: Pytest fixtures for testing the Clash Royale Manager application.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-18
Version: 0.4.0
Python Version: 3.12
Dependencies: pytest, pytest-mock, sqlalchemy
================================================================================
"""

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.utils import get_time
from app.database.base import Base
from app.database.models import (
    Member,
    Snapshot,
    PromotionScore,
    WarSeason,
    RiverRace,
    WarParticipation,
)
from app.services.war_service import WarService
from app.services.member_service import MemberService

# =============================================================================
# Database
# =============================================================================


@pytest.fixture
def db_session():
    """
    Create an isolated in-memory SQLite database for each test.
    """
    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(  # pylint: disable=invalid-name
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    session = SessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


# =============================================================================
# ORM factories
# =============================================================================


@pytest.fixture
def member_factory():
    """
    Factory creating Member instances.
    """
    counter = 0

    def _create(**kwargs):
        nonlocal counter
        counter += 1

        defaults = {
            "tag": f"#TEST_PLAYER{counter}",
            "name": f"Player {counter}",
            "role": "Member",
            "trophies": 5000,
            "donations": 100,
            "last_seen": get_time(),
        }

        defaults.update(kwargs)

        return Member(**defaults)

    return _create


@pytest.fixture
def war_season_factory():
    """
    Factory creating WarSeason instances.
    """
    counter = 0

    def _create(**kwargs):
        nonlocal counter
        counter += 1

        defaults = {
            "season_id": f"2026-{counter:02d}",
            "start_date": get_time(),
            "end_date": None,
        }

        defaults.update(kwargs)

        return WarSeason(**defaults)

    return _create


@pytest.fixture
def river_race_factory(war_season_factory):
    """
    Factory creating RiverRace instances.
    """

    def _create(war_season=None, **kwargs):

        if war_season is None:
            war_season = war_season_factory()

        defaults = {
            "war_season": war_season,
            "section_index": 0,
            "created_date": get_time(),
        }

        defaults.update(kwargs)

        return RiverRace(**defaults)

    return _create


@pytest.fixture
def war_participation_factory(
    member_factory,
    river_race_factory,
):
    """
    Factory creating WarParticipation instances.
    """

    def _create(
        member=None,
        river_race=None,
        **kwargs,
    ):
        if member is None:
            member = member_factory()

        if river_race is None:
            river_race = river_race_factory()

        defaults = {
            "member": member,
            "river_race": river_race,
            "fame": 50,
            "repair_points": 5,
            "boat_attacks": 2,
            "decks_used": 1,
            "decks_used_today": 1,
        }

        defaults.update(kwargs)

        return WarParticipation(**defaults)

    return _create


@pytest.fixture
def snapshot_factory(member_factory):
    """
    Factory creating Snapshot instances.
    """

    def _create(member=None, **kwargs):

        if member is None:
            member = member_factory()

        defaults = {
            "member": member,
            "trophies": member.trophies,
            "donations": member.donations,
            "collected_at": get_time(),
        }

        defaults.update(kwargs)

        return Snapshot(**defaults)

    return _create


@pytest.fixture
def promotion_score_factory(member_factory):
    """
    Factory creating Promotion Score instances.
    """

    def _create(member=None, **kwargs):

        if member is None:
            member = member_factory()

        defaults = {
            "member": member,
            "score": 95.5,
            "war_activity": 0.4,
            "war_win_rate": 0.3,
            "donations": 0.2,
            "trophy_level": 0.1,
            "calculated_at": get_time(),
        }

        defaults.update(kwargs)

        return PromotionScore(**defaults)

    return _create


# =============================================================================
# Convenience fixtures
# =============================================================================


@pytest.fixture
def test_members(db_session, member_factory):
    """
    Create a set of test members in the database.
    """
    members = [
        member_factory(
            tag="#TEST_PLAYER1",
            name="Player 1",
            role="Leader",
            trophies=5000,
            donations=100,
            last_seen=datetime(2026, 6, 17, 18, 4, 4),
        ),
        member_factory(
            tag="#TEST_PLAYER2",
            name="Player 2",
            role="Member",
            trophies=4000,
            donations=50,
            last_seen=datetime(2026, 6, 17, 21, 37, 20),
        ),
    ]

    db_session.add_all(members)
    db_session.commit()

    return members


@pytest.fixture
def populated_member_graph(
    db_session,
    member_factory,
    snapshot_factory,
    war_season_factory,
    river_race_factory,
    war_participation_factory,
    promotion_score_factory,
):
    """
    Create a member with related snapshots, war participations, and promotion scores.
    """

    member = member_factory(
        tag="#TEST123",
        name="Raph",
        trophies=8000,
        donations=100,
    )

    war_season = war_season_factory(
        season_id="2026-01",
    )

    river_race = river_race_factory(
        war_season=war_season,
        section_index=1,
    )

    snapshot = snapshot_factory(
        member=member,
        trophies=8000,
        donations=100,
    )

    war_participation = war_participation_factory(
        member=member,
        river_race=river_race,
        fame=50,
        repair_points=5,
        boat_attacks=2,
    )

    promotion_score = promotion_score_factory(
        member=member,
        score=95.5,
    )

    db_session.add_all(
        [
            member,
            war_season,
            river_race,
            snapshot,
            war_participation,
            promotion_score,
        ]
    )

    db_session.flush()

    db_session.commit()

    return {
        "member": member,
        "war_season": war_season,
        "river_race": river_race,
        "snapshot": snapshot,
        "war_participation": war_participation,
        "promotion_score": promotion_score,
    }


# =============================================================================
# Services
# =============================================================================


@pytest.fixture
def war_service(db_session, mocker):
    """
    Create a WarService instance with a mocked API client.
    """
    mocker.patch(
        "app.services.war_service.ClashAPIClient",
        return_value=mocker.MagicMock(),
    )

    return WarService(db_session)


@pytest.fixture
def member_service(db_session, mocker):
    """
    Create a MemberService instance with a mocked API client.
    """
    mocker.patch(
        "app.services.member_service.ClashAPIClient",
        return_value=mocker.MagicMock(),
    )

    return MemberService(db_session)


# =============================================================================
# Mock API payloads
# =============================================================================


@pytest.fixture
def mock_clan_data():
    """
    Mock partial Clash Royale API response to https://api.clashroyale.com/v1/clans/%TEST123
    """
    return {
        "tag": "#TEST123",
        "name": "Test Clan",
        "memberList": [
            {
                "tag": "#TEST_PLAYER1",
                "name": "Player 1",
                "role": "Leader",
                "lastSeen": "20260617T180404.000Z",
                "trophies": 5000,
                "donations": 100,
            },
            {
                "tag": "#TEST_PLAYER2",
                "name": "Player 2",
                "role": "Member",
                "lastSeen": "20260617T213720.000Z",
                "trophies": 4000,
                "donations": 50,
            },
        ],
    }


@pytest.fixture
def mock_river_race_log_with_standings():
    """
    Mock partial Clash Royale API response to https://api.clashroyale.com/v1/clans/%TEST123/riverracelog
    """
    return [
        {
            "seasonId": "132",
            "sectionIndex": 0,
            "createdDate": "20260608T093443.000Z",
            "standings": [
                {
                    "rank": 1,
                    "clan": {
                        "tag": "#TEST123",
                        "name": "Test Clan",
                        "participants": [
                            {
                                "tag": "#TEST_PLAYER1",
                                "name": "Player 1",
                                "fame": 100,
                                "repairPoints": 10,
                                "boatAttacks": 5,
                                "decksUsed": 3,
                                "decksUsedToday": 2,
                            },
                            {
                                "tag": "#TEST_PLAYER2",
                                "name": "Player 2",
                                "fame": 200,
                                "repairPoints": 20,
                                "boatAttacks": 8,
                                "decksUsed": 5,
                                "decksUsedToday": 3,
                            },
                        ],
                    },
                }
            ],
        }
    ]


@pytest.fixture
def mock_current_river_race():
    """
    Mock partial Clash Royale API response to https://api.clashroyale.com/v1/clans/%TEST123/riverracelog
    """
    return {
        "state": "full",
        "clan": {
            "tag": "#TEST123",
            "name": "Test Clan",
            "participants": [
                {
                    "tag": "#TEST_PLAYER1",
                    "name": "Player 1",
                    "fame": 50,
                    "repairPoints": 5,
                    "boatAttacks": 1,
                    "decksUsed": 1,
                    "decksUsedToday": 1,
                },
                {
                    "tag": "#TEST_PLAYER2",
                    "name": "Player 2",
                    "fame": 75,
                    "repairPoints": 7,
                    "boatAttacks": 2,
                    "decksUsed": 2,
                    "decksUsedToday": 2,
                },
            ],
            "periodPoints": 3000,
            "clanScore": 3309,
        },
        "sectionIndex": 2,
        "periodIndex": 17,
        "periodType": "warDay",
        "periodLogs": [
            {
                "periodIndex": 3,
                "items": [
                    {
                        "clan": {"tag": "#Q8YG902J"},
                        "pointsEarned": 28500,
                        "progressStartOfDay": 0,
                        "progressEndOfDay": 3435,
                        "endOfDayRank": 0,
                        "progressEarned": 3000,
                        "numOfDefensesRemaining": 15,
                        "progressEarnedFromDefenses": 435,
                    },
                ],
            },
            {
                "periodIndex": 4,
                "items": [
                    {
                        "clan": {"tag": "#QUUGLJUU"},
                        "pointsEarned": 31300,
                        "progressStartOfDay": 1435,
                        "progressEndOfDay": 4811,
                        "endOfDayRank": 0,
                        "progressEarned": 3000,
                        "numOfDefensesRemaining": 14,
                        "progressEarnedFromDefenses": 376,
                    },
                ],
            },
        ],
    }
