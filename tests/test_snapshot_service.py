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


def test_create_daily_snapshots(db_session, test_members):
    """Test the create_daily_snapshots method of SnapshotService."""

    snapshot_service = SnapshotService(db_session)

    db_session.add_all(test_members)
    db_session.commit()

    # Create a snapshot
    snapshots = snapshot_service.create_daily_snapshots(test_members)
    assert len(snapshots) == 2
    assert snapshots[0].member_tag == "#TEST_PLAYER1"
    assert snapshots[1].trophies == 4000
    assert snapshots[0].donations == 100
    assert snapshots[1].collected_at is not None


def test_get_last_snapshots_for_member(db_session, test_members):
    """Verify snapshots can be retrieved for a member."""

    snapshot_service = SnapshotService(db_session)


    # Create snapshots for the member
    snapshot_service.create_daily_snapshots(test_members)

    # Retrieve snapshots for the member
    member_tag = test_members[0].tag
    snapshots = snapshot_service.get_last_snapshots_for_member(member_tag)
    assert len(snapshots) == 1
    assert snapshots[0].member_tag == member_tag

    # Create another snapshot to verify multiple snapshots are stored
    snapshot_service.create_daily_snapshots(test_members)
    # Retrieve snapshots again to verify multiple snapshots are stored
    member_tag = test_members[1].tag
    snapshots = snapshot_service.get_last_snapshots_for_member(member_tag)
    assert len(snapshots) == 2
    assert snapshots[1].member_tag == member_tag
