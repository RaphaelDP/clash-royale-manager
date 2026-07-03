"""
================================================================================
Filename: clan_service.py
Description: Service for managing clan data, including fetching and updating members.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-07
Version: 0.2.3
Python Version: 3.12
Dependencies: sqlalchemy, app.database.models
================================================================================
"""

from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.core.utils import convert_timestamp_to_datetime
from app.database.models.member import Member

# from app.database.models.snapshot import Snapshot
from app.services.clash_api import ClashAPIClient
from app.core.logger import logger


class ClanService:
    """
    Service for managing clan data, including fetching, updating, and storing members.
    """

    def __init__(self, db_session, api_client=None):
        """
        Initialize the ClanService with a database session.

        Args:
            db_session: SQLAlchemy database session for interacting with the database.
            api_client: Optional ClashAPIClient instance. If not provided, a new instance will be created.
        """
        self.db: Session = db_session
        self.api_client: ClashAPIClient = api_client or ClashAPIClient()

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

            current_tags: set[str] = {member["tag"] for member in members_data}

            members: List[Member] = []
            for member_data in members_data:
                member: Member = self._upsert_member(member_data)
                members.append(member)

            self._remove_departed_members(current_tags)

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
        existing_member: Member | None = (
            self.db.query(Member).filter_by(tag=tag).first()
        )

        if existing_member:
            # Update existing member
            existing_member.name = member_data.get("name", existing_member.name)
            existing_member.role = member_data.get("role", existing_member.role)
            existing_member.trophies = member_data.get(
                "trophies", existing_member.trophies
            )
            existing_member.donations = member_data.get(
                "donations", existing_member.donations
            )
            existing_member.last_seen = convert_timestamp_to_datetime(
                member_data.get("lastSeen", "")
            )
            return existing_member

        # If not existing, create new member
        new_member: Member = Member(
            tag=tag,
            name=member_data.get("name", ""),
            role=member_data.get("role", ""),
            trophies=member_data.get("trophies", 0),
            donations=member_data.get("donations", 0),
            last_seen=convert_timestamp_to_datetime(member_data.get("lastSeen", "")),
        )
        self.db.add(new_member)
        self.db.flush()  # Flush to assign an ID if needed
        return new_member

    def _remove_departed_members(self, current_tags: set[str]) -> None:
        """
        Remove members from the database who are no longer in the clan.

        Args:
            current_tags: Set of member tags currently in the clan.
        """
        departed_members: List[Member] = (
            self.db.query(Member).filter(~Member.tag.in_(current_tags)).all()
        )
        for member in departed_members:
            logger.info(
                "Removing departed member %s (%s) from database.",
                member.name,
                member.tag,
            )
            self.db.delete(member)
