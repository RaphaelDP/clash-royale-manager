"""
================================================================================
Filename: test_clan_service.py
Description: Unit tests for the ClanService class.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-07
Version: 0.2.0
Python Version: 3.12
Dependencies: pytest, app.services.clan_service, app.database.session
================================================================================
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.base import Base
from app.database.models.member import Member

# from app.database.models.snapshot import Snapshot
from app.services.clan_service import ClanService


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )  # pylint: disable=invalid-name
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_clan_data():
    """Mock data for a clan with members."""
    return {
        "tag": "#TEST123",
        "name": "Test Clan",
        "memberList": [
            {
                "tag": "#PLAYER1",
                "name": "Player 1",
                "role": "Leader",
                "trophies": 5000,
                "donations": 100,
            },
            {
                "tag": "#PLAYER2",
                "name": "Player 2",
                "role": "Member",
                "trophies": 4000,
                "donations": 50,
            },
        ],
    }


# @pytest.fixture
# def mock_api_client(mocker):
#     """Mock the ClashAPIClient to avoid real API calls."""
#     mock_client = mocker.MagicMock()
#     mock_client.get_clan.return_value = {
#         "tag": "#TEST123",
#         "name": "Test Clan",
#         "memberList": [
#             {
#                 "tag": "#PLAYER1",
#                 "name": "Player 1",
#                 "role": "Leader",
#                 "trophies": 5000,
#                 "donations": 100,
#             },
#         ],
#     }
#     return mock_client


def test_upsert_member(db_session, mock_clan_data):
    """Test the _upsert_member method of ClanService."""
    clan_service = ClanService(db_session)
    member_data = mock_clan_data["memberList"][0]

    # Test creating a new member
    new_member = clan_service._upsert_member(member_data)
    db_session.flush()  # Flush to assign an ID

    assert new_member.tag == "#PLAYER1"
    assert new_member.name == "Player 1"
    assert new_member.role == "Leader"
    assert new_member.trophies == 5000
    assert new_member.donations == 100
    assert new_member.last_seen is not None

    # Test updating an existing member
    updated_data = member_data.copy()
    updated_data["trophies"] = 5500
    updated_member = clan_service._upsert_member(updated_data)
    assert updated_member.trophies == 5500
    assert updated_member.tag == "#PLAYER1"


# def test_create_snapshot(db_session, mock_clan_data):
#     """Test the _create_snapshot method of ClanService."""
#     clan_service = ClanService(db_session)
#     member_data = mock_clan_data["memberList"][0]

#     # Create a member first
#     member = clan_service._upsert_member(member_data)

#     # Create a snapshot
#     snapshot = clan_service._create_snapshot(member, member_data)
#     assert snapshot.member_tag == "#PLAYER1"
#     assert snapshot.trophies == 5000
#     assert snapshot.donations == 100
#     assert snapshot.collected_at is not None


def test_sync_clan_members(db_session, mocker, mock_clan_data):
    """Test the sync_clan_members method of ClanService."""
    # Mock the API client
    mock_client = mocker.MagicMock()
    mock_client.get_clan.return_value = mock_clan_data

    clan_service = ClanService(db_session, api_client=mock_client)
    members = clan_service.sync_clan_members("#TEST123")

    # Check that members were synced
    assert len(members) == 2
    assert members[0].tag == "#PLAYER1"
    assert members[1].tag == "#PLAYER2"

    # # Check that snapshots were created
    # snapshots = db_session.query(Snapshot).all()
    # assert len(snapshots) == 2
    # assert snapshots[0].member_tag == "#PLAYER1"
    # assert snapshots[1].member_tag == "#PLAYER2"


def test_sync_clan_members_rollback(db_session, mocker):
    """Test that sync_clan_members rolls back on error."""

    # Mock the API client to raise an exception
    mock_client = mocker.MagicMock()
    mock_client.get_clan.side_effect = Exception("API Error")
    clan_service = ClanService(db_session, api_client=mock_client)

    with pytest.raises(Exception, match="API Error"):
        clan_service.sync_clan_members("#TEST123")

    # # Check that no members or snapshots were added
    members = db_session.query(Member).all()
    # snapshots = db_session.query(Snapshot).all()
    assert len(members) == 0
    # assert len(snapshots) == 0


def test_sync_clan_members_updates_existing_member(db_session, mocker, mock_clan_data):
    """Test that sync_clan_members updates existing members."""

    mock_client = mocker.MagicMock()
    mock_client.get_clan.return_value = mock_clan_data

    clan_service = ClanService(db_session, api_client=mock_client)

    clan_service.sync_clan_members("#TEST123")

    updated_clan_data = {
        **mock_clan_data,
        "memberList": [
            {
                **mock_clan_data["memberList"][0],
                "trophies": 6000,
            },
            mock_clan_data["memberList"][1],
        ],
    }

    mock_client.get_clan.return_value = updated_clan_data

    clan_service.sync_clan_members("#TEST123")

    member = db_session.query(Member).filter_by(tag="#PLAYER1").first()

    assert member.trophies == 6000
