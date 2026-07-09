"""
================================================================================
Filename: member_service.py
Description: Service for managing clan members, including creation, updates, and departures.
Author: Raphael Smilet
Date Created: 2026-07-03
Last Modified: 2026-07-03
Version: 0.5.0
Python Version: 3.12
Dependencies: sqlalchemy, app.database.models, app.core.logger, app.core.utils
================================================================================
"""

from pathlib import Path
import json
from typing import Any, List
from datetime import timedelta
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.logger import logger
from app.core.utils import convert_timestamp_to_datetime, get_time
from app.database.models import Member
from app.services.clash_api import ClashAPIClient


class MemberService:
    """Service for managing clan members."""

    def __init__(self, db_session: Session, api_client: ClashAPIClient = None) -> None:
        """
        Initialize the MemberService with a database session and API client.
        Args:
            db_session: SQLAlchemy database session for interacting with the database.
            api_client: Optional ClashAPIClient instance. If not provided, a new instance will be

        """
        self.db: Session = db_session
        self.api_client: ClashAPIClient = api_client or ClashAPIClient()

    def create_or_update_member(
        self,
        tag: str,
        name: str,
        role: str,
        trophies: int,
        donations: int,
        last_seen: str,
    ) -> Member:
        """
        Create or update a member in the database.
        Preserves war history even if the member leaves later.

        Args:
            tag: Member's Clash Royale tag.
            name: Member's name.
            role: Member's role (leader, coLeader, elder, member, left, fired).
            trophies: Current trophy count.
            donations: Current donation count.
            last_seen: Last seen datetime string from the API.

        Returns:
            Member: The created or updated Member object.
        """
        existing_member: Member | None = (
            self.db.query(Member).filter_by(tag=tag).first()
        )

        if existing_member:
            # Update existing member
            existing_member.name = name
            existing_member.role = role
            existing_member.trophies = trophies
            existing_member.donations = donations
            existing_member.last_seen = (
                convert_timestamp_to_datetime(last_seen) if last_seen else None
            )
            logger.info("Updated member %s with role %s.", tag, role)
        else:
            # Create new member
            new_member = Member(
                tag=tag,
                name=name,
                role=role,
                trophies=trophies,
                donations=donations,
                last_seen=(
                    convert_timestamp_to_datetime(last_seen) if last_seen else None
                ),
            )
            self.db.add(new_member)
            logger.info("Created new member %s with role %s.", tag, role)

        self.db.commit()
        return existing_member or new_member

    def remove_member_from_clan(self, tag: str, reason: str = "left") -> Member | None:
        """
        Mark a member as left/fired but preserve their war history.
        Sets role to 'left' or 'fired' and clears active fields.

        Args:
            tag: Member's Clash Royale tag.
            reason: Reason for removal ('left' or 'fired').
        """
        member: Member | None = self.db.query(Member).filter_by(tag=tag).first()
        if member:
            member.role = reason
            member.last_seen = get_time()  # Record when they left
            self.db.commit()
            logger.info("Member %s marked as %s.", tag, reason)
            return member
        else:
            logger.warning("Member %s not found.", tag)
            exmember_data = self.api_client.get_player(tag)
            self.create_or_update_member(
                tag=exmember_data.get("tag", ""),
                name=exmember_data.get("name", ""),
                role=reason,
                trophies=exmember_data.get("trophies", 0),
                donations=exmember_data.get("donations", 0),
                last_seen=exmember_data.get("lastSeen", ""),
            )
            return self.db.query(Member).filter_by(tag=tag).first()

    def promote_member(self, tag: str, new_role: str) -> bool:
        """
        Promote a member to a new role (e.g., member → elder, elder → coLeader).
        Validates role transitions and clan rules.

        Args:
            tag: Member's Clash Royale tag.
            new_role: New role (coLeader, elder, member).

        Returns:
            bool: True if promotion succeeded, False otherwise.
        """
        member: Member | None = self.db.query(Member).filter_by(tag=tag).first()
        if not member:
            logger.warning("Member %s not found. Cannot promote.", tag)
            return False

        # Validate role transitions
        valid_transitions = {
            "member": ["elder"],
            "elder": ["coLeader", "member"],
            "coLeader": ["elder", "member"],
        }

        if new_role not in valid_transitions.get(member.role, []):
            logger.warning("Invalid promotion: %s → %s.", member.role, new_role)
            return False

        # Check clan rules (e.g., only 1 leader)
        if new_role == "leader":
            existing_leader = self.db.query(Member).filter_by(role="leader").first()
            if existing_leader:
                logger.warning("Cannot promote: Only 1 leader allowed per clan.")
                return False

        old_role = member.role
        member.role = new_role
        self.db.commit()
        logger.info(
            "Promoted %s from %s to %s.",
            tag,
            old_role,
            new_role,
        )
        return True

    def get_active_members(self) -> List[Member]:
        """
        Get all active members (role != 'left' or 'fired').

        Returns:
            List[Member]: List of active members.
        """
        return self.db.query(Member).filter(Member.role.notin_(["left", "fired"])).all()

    def get_inactive_members(self, days_threshold: int = 7) -> List[Member]:
        """
        Get members inactive for more than `days_threshold` days.

        Args:
            days_threshold: Days since last activity to consider inactive.

        Returns:
            List[Member]: List of inactive members.
        """

        cutoff_date = get_time() - timedelta(days=days_threshold)
        return (
            self.db.query(Member)
            .filter(
                and_(
                    Member.last_seen.isnot(None),
                    Member.last_seen < cutoff_date,
                    Member.role.notin_(["left", "fired"]),
                )
            )
            .all()
        )

    def get_member_history(self, tag: str) -> dict:
        """
        Get a member's history (snapshots, war participations, etc.).

        Args:
            tag: Member's Clash Royale tag.

        Returns:
            dict: Member data with snapshots and war participations.
        """
        member: Member | None = self.db.query(Member).filter_by(tag=tag).first()
        if not member:
            return {}

        return {
            "member": member,
            "snapshots": member.snapshots,
            "war_participations": member.war_participations,
            "promotion_scores": member.promotion_scores,
        }

    def add_ex_member(self, tag: str) -> None:
        """
        Add a member to the ex-members list (role = 'left').

        Args:
            tag: Member's Clash Royale tag.
        """
        member: Member | None = self.db.query(Member).filter_by(tag=tag).first()
        if member:
            member.role = "left"
            self.db.commit()
            logger.info("Member %s added to ex-members list.", tag)
        else:
            logger.warning("Member %s not found. Cannot add to ex-members list.", tag)

    def get_player_profile(
        self, member_tag: str, all_stats: bool = False, refresh: bool = False
    ) -> dict[str, Any]:
        """
        Returns all information known about a member.

        Args:
            member_tag: Clash Royale player tag.
            all_stats: If True, also returns cached/live Clash Royale API data.

        Returns:
            Dictionary containing local database information merged with
            Clash Royale API data.
        """

        member = self.db.query(Member).filter(Member.tag == member_tag).first()

        if member is None:
            return {}

        member_data: dict[str, Any] = {
            "tag": member.tag,
            "name": member.name,
            "role": member.role,
            "trophies": member.trophies,
            "donations": member.donations,
            "last_seen": member.last_seen,
            "promotion_score": member.promotion_score,
            "promotion_score_updated_at": member.promotion_score_updated_at,
        }

        if not all_stats:
            return member_data

        cache_dir = Path("data/cache/players")
        cache_dir.mkdir(parents=True, exist_ok=True)

        cache_file = cache_dir / f"{member_tag.replace('#', '')}.json"

        player_data: dict[str, Any]

        if cache_file.exists() and not refresh:
            with cache_file.open("r", encoding="utf-8") as file:
                player_data = json.load(file)
        else:
            player_data = self.api_client.get_player(member_tag)

            with cache_file.open("w", encoding="utf-8") as file:
                json.dump(player_data, file, indent=4)

        member_data["api"] = player_data

        return member_data
