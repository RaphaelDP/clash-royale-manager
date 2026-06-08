"""
================================================================================
Filename: snapshot_service.py
Description: Service for creating and managing member data snapshots.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-06
Version: 0.3.1
Python Version: 3.11
Dependencies: sqlalchemy, app.database.models
================================================================================
"""

from typing import List
from datetime import datetime, UTC

from app.core.logger import logger
from app.database.models import Snapshot, Member


class SnapshotService:
    """
    Service for creating and managing member data snapshots.
    Snapshots track historical data like trophies and donations for activity analysis.
    """

    def __init__(self, db_session) -> None:
        """
        Initialize the SnapshotService with a database session.

        Args:
            db_session: SQLAlchemy database session for interacting with the database.
        """
        self.db = db_session

    def create_snapshot(self, member: Member) -> Snapshot:
        """
        Create a snapshot for a member.

        Args:
            member: The Member object for which to create the snapshot.
        Returns:
            Snapshot: The created Snapshot object.
        """
        snapshot = Snapshot(
            member_tag=member.tag,
            trophies=member.trophies,
            donations=member.donations,
            collected_at=datetime.now(UTC),
        )
        self.db.add(snapshot)
        logger.info(
            "Created snapshot for member %s at %s", member.tag, snapshot.collected_at
        )
        return snapshot

    def create_daily_snapshots(self, members: List[Member] | None) -> List[Snapshot]:
        """
        Create snapshots for all members in the database.

        Returns:
            List[Snapshot]: List of created Snapshot objects.
        """
        if members is None:
            members: List[Member] = self.db.query(Member).all()
        snapshots: List[Snapshot] = []
        for member in members:
            snapshot = self.create_snapshot(member)
            snapshots.append(snapshot)
        self.db.commit()
        self.db.flush()
        logger.info("Created %d snapshots for all members", len(snapshots))
        return snapshots

    def get_last_snapshots_for_member(
        self, member_tag: str, limit: int | None = 10
    ) -> List[Snapshot]:
        """
        Retrieve all snapshots for a specific member.

        Args:
            member_tag: The tag of the member to retrieve snapshots for.
            limit: Optional limit on the number of snapshots to retrieve.
        Returns:
            List[Snapshot]: List of Snapshot objects for the member.
        """
        query = (
            self.db.query(Snapshot)
            .filter(Snapshot.member_tag == member_tag)
            .order_by(Snapshot.collected_at.desc())
        )
        if limit is not None:
            query = query.limit(limit)
        snapshots: List[Snapshot] = query.all()
        logger.info("Retrieved %d snapshots for member %s", len(snapshots), member_tag)
        return snapshots
