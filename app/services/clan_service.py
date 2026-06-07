"""
================================================================================
Filename: clan_service.py
Description: Service for managing clan data, including fetching and updating members.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-07
Version: 0.2.0
Python Version: 3.12
Dependencies: sqlalchemy, app.database.models
================================================================================
"""

from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.database.models.member import Member
# from app.database.models.snapshot import Snapshot
from app.services.clash_api import ClashAPIClient
from app.core.logger import logger


class ClanService:
    """
    Service for managing clan data, including fetching, updating, and storing members.
    """

    def __init__(self, db_session):
        """
        Initialize the ClanService with a database session.

        Args:
            db_session: SQLAlchemy database session for interacting with the database.
        """
        self.db: Session = db_session
        self.api_client: ClashAPIClient = ClashAPIClient()




    def sync_clan_members(self, clan_tag: str) -> List[Member]:
        """
        Fetch clan members from the API and update the database.

        Args:
            clan_tag: The clan tag (e.g., "#ABC123").

        Returns:
            List[Member]: List of updated/created Member objects.
        """
        try:
            clan_data: Dict[str, Any] = self.api_client.get_clan(clan_tag)
            members_data: List[Dict[str, Any]] = clan_data.get("memberList", [])

            members: List[Member] = []
            for member_data in members_data:
                member: Member = self._upsert_member(member_data)
                members.append(member)
                # self._create_snapshot(member, member_data)

            self.db.commit()
            logger.info("Synced %d members for clan %s.", len(members), clan_tag)
            return members
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to sync clan members: %s", e)
            raise

    def _upsert_member(self, member_data: Dict[str, Any]) -> Member:
        """
        Update or insert a member into the database.

        Args:
            member_data: Member data from the Clash Royale API.

        Returns:
            Member: The updated/created Member object.
        """
        tag: str = member_data.get("tag", "")
        existing_member: Member | None = self.db.query(Member).filter_by(tag=tag).first()
        now = datetime.now()
    
        if existing_member:
            # Update existing member
            existing_member.name = member_data.get("name", existing_member.name)
            existing_member.role = member_data.get("role", existing_member.role)
            existing_member.trophies = member_data.get("trophies", existing_member.trophies)
            existing_member.donations = member_data.get("donations", existing_member.donations)
            existing_member.last_seen = now
            return existing_member
        
        # If not existing, create new member
        new_member: Member = Member(
            tag=tag,
            name=member_data.get("name", ""),
            role=member_data.get("role", ""),
            trophies=member_data.get("trophies", 0),
            donations=member_data.get("donations", 0),
            last_seen=now,
        )
        self.db.add(new_member)
        self.db.flush()  # Flush to assign an ID if needed
        return new_member

    # def _create_snapshot(self, member: Member, member_data: Dict[str, Any]) -> Snapshot:
    #     """
    #     Create a snapshot for a member to track historical data.

    #     Args:
    #         member: The Member object.
    #         member_data: Member data from the Clash Royale API.

    #     Returns:
    #         Snapshot: The created Snapshot object.
    #     """
    #     snapshot: Snapshot = Snapshot(
    #         member_tag=member.tag,
    #         trophies=member_data.get("trophies", 0),
    #         donations=member_data.get("donations", 0),
    #         collected_at=now,
    #     )
    #     self.db.add(snapshot)
    #     return snapshot
