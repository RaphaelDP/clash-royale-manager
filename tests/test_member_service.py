"""
================================================================================
Filename: test_member_service.py
Description: Unit tests for the MemberService class.
Author: Raphael Smilet
Date Created: 2026-07-03
Last Modified: 2026-07-03
Version: 0.5.0
Python Version: 3.12
Dependencies: pytest, app.services.member_service, app.database.models
================================================================================
"""


from app.database.models import Member
from app.core.utils import convert_timestamp_to_datetime



def test_create_or_update_member(db_session, member_service, mock_clan_data):
    """Test the _create_or_update_member method of MemberService."""

    member_data = mock_clan_data["memberList"][0]

    new_member = member_service.create_or_update_member(tag=member_data.get("tag", ""),
                                                        name=member_data.get("name", ""),
                                                        role=member_data.get("role", ""),
                                                        trophies=member_data.get("trophies", 0),
                                                        donations=member_data.get("donations", 0),
                                                        last_seen=member_data.get("lastSeen", ""))  

    db_session.flush()

    assert new_member.tag == "#TEST_PLAYER1"
    assert new_member.name == "Player 1"
    assert new_member.role == "Leader"
    assert new_member.trophies == 5000
    assert new_member.donations == 100
    assert new_member.last_seen is not None

    updated_data = member_data.copy()

    updated_data["trophies"] = 6767

    updated_member = member_service.create_or_update_member(tag=member_data.get("tag", ""),
                                                        name=member_data.get("name", ""),
                                                        role=member_data.get("role", ""),
                                                        trophies=updated_data.get("trophies", 0),
                                                        donations=member_data.get("donations", 0),
                                                        last_seen=member_data.get("lastSeen", ""))  


    assert updated_member.trophies == 6767
    assert updated_member.tag == "#TEST_PLAYER1"

    members = db_session.query(Member).all()

    assert len(members) == 1
    assert members[0].tag == "#TEST_PLAYER1"




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




def test_get_active_members(member_service, test_members):
    """Test filtering active members."""

    member_service.remove_member_from_clan(tag=test_members[0].tag, reason="left")
    active_members = member_service.get_active_members()

    
    assert len(active_members) == 1
    assert active_members[0].tag == test_members[1].tag

def test_get_inactive_members(db_session, member_service, member_factory):
    """Test filtering inactive members."""
    active_member=member_factory()  # Recent
    inactive_member = member_factory(last_seen=convert_timestamp_to_datetime("20160601T120000.000Z"))  # Old

    db_session.add_all([active_member, inactive_member])
    db_session.flush()

    inactive_members = member_service.get_inactive_members(days_threshold=7)
    assert len(inactive_members) == 1
    assert inactive_members[0].tag == inactive_member.tag