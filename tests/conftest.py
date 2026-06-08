"""
================================================================================
Filename: conftest.py
Description: Pytest fixtures for testing the Clash Royale Manager application.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-08
Version: 0.3.0
Python Version: 3.11
Dependencies: pytest, pytest-mock, app.services.score_service
================================================================================
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.database.models.member import Member


@pytest.fixture
def db_session()-> sessionmaker:
    """
    Create an isolated in-memory SQLite database for each test.
    """
    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker( # pylint: disable=invalid-name
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    session = SessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_members() -> list[Member]:
    """
    Return Member ORM objects for database tests.
    """
    return [
        Member(
            tag="#TEST_PLAYER1",
            name="Player 1",
            role="Leader",
            trophies=5000,
            donations=100,
        ),
        Member(
            tag="#TEST_PLAYER2",
            name="Player 2",
            role="Member",
            trophies=4000,
            donations=50,
        ),
    ]


@pytest.fixture
def mock_clan_data() -> dict:
    """
    Mock Clash Royale API response.
    """
    return {
        "tag": "#TEST123",
        "name": "Test Clan",
        "memberList": [
            {
                "tag": "#TEST_PLAYER1",
                "name": "Player 1",
                "role": "Leader",
                "trophies": 5000,
                "donations": 100,
            },
            {
                "tag": "#TEST_PLAYER2",
                "name": "Player 2",
                "role": "Member",
                "trophies": 4000,
                "donations": 50,
            },
        ],
    }
