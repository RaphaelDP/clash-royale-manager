"""
================================================================================
Filename: clan_service.py
Description: Service for managing clan data, including fetching and updating members.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-10-01
Version: 0.2.5
Python Version: 3.12
Dependencies: sqlalchemy, app.database.models
================================================================================
"""

from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.database.models.member import Member

# from app.database.models.snapshot import Snapshot
from app.services.clash_api import ClashAPIClient
from app.services.member_service import MemberService
from app.core.logger import logger


class ClanService:
    """
    Service for managing clan data, including fetching, updating, and storing members.
    """

    def __init__(self, db_session, api_client=None):
        """
        Initialize ClanService with its configured dependencies.

        Args:
            db_session: SQLAlchemy database session for interacting with the database.
            api_client: Optional ClashAPIClient; a new client is created when omitted.

        Returns:
            None.
        """
        self.db: Session = db_session
        self.api_client: ClashAPIClient = api_client or ClashAPIClient()
        self.member_service: MemberService = MemberService(db_session, self.api_client)

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
            members_data = clan_data.get("memberList")
            if not isinstance(members_data, list):
                raise ValueError(
                    "Clan response is missing memberList; roster unchanged."
                )
            if clan_data.get("tag", clan_tag) != clan_tag:
                raise ValueError("Clan response tag does not match the requested clan.")
            if "members" in clan_data and clan_data["members"] != len(members_data):
                raise ValueError("Incomplete clan roster response.")
            if any(
                not isinstance(m, dict)
                or not m.get("tag")
                or not m.get("name")
                or not m.get("role")
                for m in members_data
            ):
                raise ValueError("Invalid member in clan roster.")
            if len({m["tag"] for m in members_data}) != len(members_data):
                raise ValueError("Duplicate member tags in clan roster.")

            current_tags: set[str] = {member["tag"] for member in members_data}

            members: List[Member] = []
            for member_data in members_data:
                member: Member = self.member_service.create_or_update_member(
                    tag=member_data.get("tag", ""),
                    name=member_data.get("name", ""),
                    role=member_data.get("role", ""),
                    trophies=member_data.get("trophies", 0),
                    donations=member_data.get("donations", 0),
                    last_seen=member_data.get("lastSeen", ""),
                    commit=False,
                )
                members.append(member)

            self._remove_departed_members(current_tags)

            self.db.commit()
            logger.info("Synced %d members for clan %s.", len(members), clan_tag)
            return members
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to sync clan members: %s", e)
            raise

    def _remove_departed_members(self, current_tags: set[str]) -> None:
        """
        Mark absent active members as left without deleting their history.

        Changes are flushed into the caller-owned roster transaction.

        Args:
            current_tags: Set of member tags currently in the clan.

        Returns:
            None.
        """
        active_members = self.member_service.get_active_members()
        departed_tags = {m.tag for m in active_members if m.tag not in current_tags}
        for tag in departed_tags:
            self.member_service.remove_member_from_clan(
                tag, reason="left", commit=False
            )
            logger.info("Member %s left the clan.", tag)
