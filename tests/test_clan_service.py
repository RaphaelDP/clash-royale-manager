"""
================================================================================
Filename: test_clan_service.py
Description: Unit tests for the ClanService class.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-07
Version: 0.2.2
Python Version: 3.12
Dependencies: pytest, app.services.clan_service, app.database.session
================================================================================
"""

import pytest
from app.database.models.member import Member
from app.services.clan_service import ClanService


def test_upsert_member(db_session, mock_clan_data):
    """Test the _upsert_member method of ClanService."""
    clan_service = ClanService(db_session)
    member_data = mock_clan_data["memberList"][0]

    # Test creating a new member
    new_member = clan_service._upsert_member(member_data)
    db_session.flush()  # Flush to assign an ID

    assert new_member.tag == "#TEST_PLAYER1"
    assert new_member.name == "Player 1"
    assert new_member.role == "Leader"
    assert new_member.trophies == 5000
    assert new_member.donations == 100
    assert new_member.last_seen is not None

    # Test updating an existing member
    updated_data = member_data.copy()
    updated_data["trophies"] = 6767
    updated_member = clan_service._upsert_member(updated_data)
    assert updated_member.trophies == 6767
    assert updated_member.tag == "#TEST_PLAYER1"


def test_sync_clan_members(db_session, mocker, mock_clan_data):
    """Test the sync_clan_members method of ClanService."""
    # Mock the API client
    mock_client = mocker.MagicMock()
    mock_client.get_clan.return_value = mock_clan_data

    clan_service = ClanService(db_session, api_client=mock_client)
    members = clan_service.sync_clan_members("#TEST123")

    # Check that members were synced
    assert len(members) == 2
    assert members[0].tag == "#TEST_PLAYER1"
    assert members[1].tag == "#TEST_PLAYER2"


def test_sync_clan_members_rollback(db_session, mocker):
    """Test that sync_clan_members rolls back on error."""

    # Mock the API client to raise an exception
    mock_client = mocker.MagicMock()
    mock_client.get_clan.side_effect = Exception("API Error")
    clan_service = ClanService(db_session, api_client=mock_client)

    with pytest.raises(Exception, match="API Error"):
        clan_service.sync_clan_members("#TEST123")

    # # Check that no members were added
    members = db_session.query(Member).all()
    assert len(members) == 0


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

    member = db_session.query(Member).filter_by(tag="#TEST_PLAYER1").first()

    assert member.trophies == 6000
