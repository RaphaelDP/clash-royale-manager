"""
================================================================================
Filename: test_snapshot_service.py
Description: Unit tests for the SnapshotService class.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-08
Version: 0.3.1
Python Version: 3.12
Dependencies: pytest, app.services.snapshot_service, app.database.session
================================================================================
"""

from app.services.snapshot_service import SnapshotService


def test_create_daily_snapshots(
    db_session,
    test_members,
):
    """Test the create_daily_snapshots method of SnapshotService."""

    snapshot_service = SnapshotService(db_session)

    snapshots = snapshot_service.create_daily_snapshots(test_members)

    assert len(snapshots) == 2

    assert snapshots[0].member_tag == test_members[0].tag
    assert snapshots[1].member_tag == test_members[1].tag

    assert snapshots[0].trophies == test_members[0].trophies
    assert snapshots[1].trophies == test_members[1].trophies

    assert snapshots[0].donations == test_members[0].donations
    assert snapshots[1].donations == test_members[1].donations

    assert snapshots[0].collected_at is not None
    assert snapshots[1].collected_at is not None

    saved_snapshots = snapshot_service.get_last_snapshots_for_member(
        test_members[0].tag
    )

    assert len(saved_snapshots) == 1
    assert db_session.query(type(snapshots[0])).count() == 2


def test_get_last_snapshots_for_member(
    db_session,
    test_members,
):
    """Verify snapshots can be retrieved for a member."""

    snapshot_service = SnapshotService(db_session)

    snapshot_service.create_daily_snapshots(test_members)

    member_tag = test_members[0].tag

    snapshots = snapshot_service.get_last_snapshots_for_member(member_tag)

    assert len(snapshots) == 1
    assert snapshots[0].member_tag == member_tag

    snapshot_service.create_daily_snapshots(test_members)

    member_tag = test_members[1].tag

    snapshots = snapshot_service.get_last_snapshots_for_member(member_tag)

    assert len(snapshots) == 2
    assert all(snapshot.member_tag == member_tag for snapshot in snapshots)
