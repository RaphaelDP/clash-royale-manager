"""
================================================================================
Filename: test_member_service.py
Description: Unit tests for the MemberService class.
Author: Raphael Smilet
Date Created: 2026-07-03
Last Modified: 2026-07-07
Version: 0.5.0
Python Version: 3.12
Dependencies: pytest, app.services.member_service, app.database.models
================================================================================
"""

from datetime import timedelta
import pytest
from app.database.models import Member
from app.core.utils import convert_timestamp_to_datetime, get_time


def test_create_or_update_member(db_session, member_service, mock_clan_data):
    """Test the create_or_update_member method of MemberService."""

    new_member = member_service.create_or_update_member(
        tag=mock_clan_data["memberList"][0].get("tag", ""),
        name=mock_clan_data["memberList"][0].get("name", ""),
        role=mock_clan_data["memberList"][0].get("role", ""),
        trophies=mock_clan_data["memberList"][0].get("trophies", 0),
        donations=mock_clan_data["memberList"][0].get("donations", 0),
        last_seen=mock_clan_data["memberList"][0].get("lastSeen", ""),
    )

    db_session.flush()

    assert new_member.tag == "#TEST_PLAYER1"
    assert new_member.name == "Player 1"
    assert new_member.role == "Leader"
    assert new_member.trophies == 5000
    assert new_member.donations == 100
    assert new_member.last_seen is not None

    updated_data = mock_clan_data["memberList"][0].copy()
    updated_data["trophies"] = 6767

    updated_member = member_service.create_or_update_member(
        tag=updated_data.get("tag", ""),
        name=updated_data.get("name", ""),
        role=updated_data.get("role", ""),
        trophies=updated_data.get("trophies", 0),
        donations=updated_data.get("donations", 0),
        last_seen=updated_data.get("lastSeen", ""),
    )

    assert updated_member.trophies == 6767
    assert updated_member.tag == "#TEST_PLAYER1"

    members = db_session.query(Member).all()

    assert len(members) == 1
    assert members[0].tag == "#TEST_PLAYER1"


# Business Rule Tests


def test_create_or_update_member_does_not_duplicate(
    db_session, member_service, mock_clan_data
):
    """Business rule: Synchronizing the same player twice must never create duplicates."""

    # Sync the same player twice
    member_service.create_or_update_member(
        tag=mock_clan_data["memberList"][0].get("tag", ""),
        name=mock_clan_data["memberList"][0].get("name", ""),
        role=mock_clan_data["memberList"][0].get("role", ""),
        trophies=mock_clan_data["memberList"][0].get("trophies", 0),
        donations=mock_clan_data["memberList"][0].get("donations", 0),
        last_seen=mock_clan_data["memberList"][0].get("lastSeen", ""),
    )
    member_service.create_or_update_member(
        tag=mock_clan_data["memberList"][0].get("tag", ""),
        name=mock_clan_data["memberList"][0].get("name", ""),
        role=mock_clan_data["memberList"][0].get("role", ""),
        trophies=6767,  # Updated value
        donations=mock_clan_data["memberList"][0].get("donations", 0),
        last_seen=mock_clan_data["memberList"][0].get("lastSeen", ""),
    )

    members = db_session.query(Member).all()
    assert len(members) == 1
    assert members[0].trophies == 6767


def test_remove_unknown_member_fetches_from_api(db_session, member_service, mocker):
    """Business rule: If a member already left before synchronization, recover from API."""
    # Mock API response for a left member
    mock_player_data = {
        "tag": "#LEFT_MEMBER",
        "name": "Left Player",
        "role": "member",
        "trophies": 3000,
        "donations": 50,
        "lastSeen": "20260601T120000.000Z",
    }
    mocker.patch.object(
        member_service.api_client,
        "get_player",
        return_value=mock_player_data,
    )
    # Remove a non-existent member (should fetch from API)
    member_service.remove_member_from_clan("#LEFT_MEMBER", reason="left")
    # Verify API was called once
    member_service.api_client.get_player.assert_called_once_with("#LEFT_MEMBER")
    # Verify member was inserted with role="left"
    members = db_session.query(Member).all()
    assert len(members) == 1
    assert members[0].tag == "#LEFT_MEMBER"
    assert members[0].role == "left"


def test_remove_unknown_member_api_failure(db_session, member_service, mocker):
    """Business rule: If API fails, no member should be created."""
    mocker.patch.object(
        member_service.api_client,
        "get_player",
        side_effect=Exception("API Error"),
    )
    with pytest.raises(Exception, match="API Error"):
        member_service.remove_member_from_clan("#UNKNOWN", reason="left")
    # Verify no member was created
    members = db_session.query(Member).all()
    assert len(members) == 0


def test_promote_unknown_member(db_session, member_service):
    """Business rule: Promoting an unknown member should fail silently."""
    assert member_service.promote_member("#UNKNOWN", "elder") is False
    # Verify no database modification
    members = db_session.query(Member).all()
    assert len(members) == 0


def test_invalid_role_transitions(db_session, member_service, member_factory):
    """Business rule: Test all impossible role transitions."""
    # Create a member
    member = member_factory(role="member")
    db_session.add(member)
    db_session.commit()

    # Test invalid transitions
    invalid_transitions = [
        ("member", "leader"),  # member → leader (invalid)
        ("elder", "leader"),  # elder → leader (invalid)
        ("member", "coLeader"),  # member → coLeader (invalid)
        ("coLeader", "leader"),  # coLeader → leader (invalid)
        ("left", "elder"),  # left → elder (invalid)
    ]
    for current_role, new_role in invalid_transitions:
        member.role = current_role
        db_session.commit()
        assert member_service.promote_member(member.tag, new_role) is False


def test_single_leader_rule(db_session, member_service, member_factory):
    """Business rule: Only one leader allowed per clan."""
    # Create a leader
    leader = member_factory(role="leader")
    db_session.add(leader)
    db_session.commit()

    # Create a coLeader
    co_leader = member_factory(role="coLeader")
    db_session.add(co_leader)
    db_session.commit()

    # Try to promote coLeader to leader (should fail)
    assert member_service.promote_member(co_leader.tag, "leader") is False
    # Verify leader is still the same
    updated_leader = db_session.query(Member).filter_by(role="leader").first()
    assert updated_leader.tag == leader.tag


def test_get_member_history(member_service, populated_member_graph):
    """Business rule: get_member_history returns all related data."""
    member = populated_member_graph["member"]
    history = member_service.get_member_history(member.tag)
    assert history["member"] == member
    assert len(history["snapshots"]) == 1
    assert len(history["war_participations"]) == 1
    assert len(history["promotion_scores"]) == 1


def test_get_member_history_unknown(member_service):
    """Business rule: get_member_history returns empty dict for unknown members."""
    assert member_service.get_member_history("#UNKNOWN") == {}


def test_add_ex_member(db_session, member_service, member_factory):
    """Business rule: add_ex_member marks a member as left."""
    member = member_factory()
    db_session.add(member)
    db_session.commit()

    member_service.add_ex_member(member.tag)
    updated_member = db_session.query(Member).filter_by(tag=member.tag).first()
    assert updated_member.role == "left"


def test_add_ex_member_unknown(db_session, member_service):
    """Business rule: add_ex_member should not raise for unknown members."""
    member_service.add_ex_member("#UNKNOWN")
    # Verify no database modification
    members = db_session.query(Member).all()
    assert len(members) == 0


def test_get_active_members(member_service, test_members):
    """Business rule: get_active_members excludes left/fired members."""
    member_service.remove_member_from_clan(tag=test_members[0].tag, reason="left")
    active_members = member_service.get_active_members()
    assert all(m.role not in ["left", "fired"] for m in active_members)
    assert len(active_members) == 1
    assert active_members[0].tag == test_members[1].tag


def test_get_inactive_members_ignores_left_members(
    db_session, member_service, member_factory
):
    """Business rule: get_inactive_members ignores left/fired members."""
    # Create a left member with very old last_seen
    left_member = member_factory(
        role="left", last_seen=convert_timestamp_to_datetime("20160601T120000.000Z")
    )
    db_session.add(left_member)
    db_session.commit()

    # Should return empty list (left members are ignored)
    inactive_members = member_service.get_inactive_members(days_threshold=7)
    assert len(inactive_members) == 0


def test_get_inactive_members_threshold(db_session, member_service, member_factory):
    """Business rule: get_inactive_members respects the threshold."""
    # Create members with different last_seen dates
    recent_member = member_factory(last_seen=get_time() - timedelta(days=6))
    old_member = member_factory(last_seen=get_time() - timedelta(days=8))
    db_session.add_all([recent_member, old_member])
    db_session.commit()

    # Threshold = 7 days
    inactive_members = member_service.get_inactive_members(days_threshold=7)
    assert len(inactive_members) == 1
    assert inactive_members[0].tag == old_member.tag


def test_remove_member_from_clan(db_session, member_service, member_factory):
    """Test marking a member as left/fired."""
    member = member_factory()
    db_session.add(member)
    db_session.flush()

    # Mark as left
    member_service.remove_member_from_clan(tag=member.tag, reason="left")
    updated_member = db_session.query(Member).filter_by(tag=member.tag).first()
    assert updated_member.role == "left"


def test_promote_member(db_session, member_service, member_factory):
    """Test promoting a member."""

    member = member_factory(role="member")
    db_session.add(member)
    db_session.flush()

    # Promote to elder
    assert member_service.promote_member(member.tag, "elder") is True
    updated_member = db_session.query(Member).filter_by(tag=member.tag).first()
    assert updated_member.role == "elder"

    # Invalid promotion (member → leader)
    assert member_service.promote_member(member.tag, "leader") is False

    # Promote to coLeader
    assert member_service.promote_member(member.tag, "coLeader") is True
    updated_member = db_session.query(Member).filter_by(tag=member.tag).first()
    assert updated_member.role == "coLeader"


def test_get_inactive_members(db_session, member_service, member_factory):
    """Test filtering inactive members."""
    active_member = member_factory()  # Recent
    inactive_member = member_factory(
        last_seen=convert_timestamp_to_datetime("20160601T120000.000Z")
    )  # Old

    db_session.add_all([active_member, inactive_member])
    db_session.flush()

    inactive_members = member_service.get_inactive_members(days_threshold=7)
    assert len(inactive_members) == 1
    assert inactive_members[0].tag == inactive_member.tag
