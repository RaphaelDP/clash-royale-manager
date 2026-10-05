"""
================================================================================
Filename: member_service.py
Description: Service for managing clan members, including creation, updates, and departures.
Author: Raphael Smilet
Date Created: 2026-07-03
Last Modified: 2026-10-02
Version: 0.5.4
Python Version: 3.12
Dependencies: sqlalchemy, app.database.models, app.core.logger, app.core.utils
================================================================================
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, List
from sqlalchemy import and_, func
from sqlalchemy.orm import Session, joinedload

from app.core.logger import logger
from app.core.utils import convert_timestamp_to_datetime, get_time
from app.database.models import Member, RiverRace, WarParticipation, JobRunState
from app.services.clash_api import ClashAPIClient


class MemberService:
    """Service for managing clan members."""

    def __init__(self, db_session: Session, api_client: ClashAPIClient = None) -> None:
        """
        Initialize MemberService with its configured dependencies.

        Args:
            db_session: SQLAlchemy database session for interacting with the database.
            api_client: Optional ClashAPIClient; a new client is created when omitted.

        Returns:
            None.
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
        *,
        commit: bool = True,
    ) -> Member:
        """
        Create or update a member in the database. Preserves war history even if the member
        leaves later.

        Args:
            tag: Member's Clash Royale tag.
            name: Member's name.
            role: Member's role (leader, coLeader, elder, member, left, fired).
            trophies: Current trophy count.
            donations: Current donation count.
            last_seen: UTC API timestamp string, or None to store unknown activity.
            commit: Commit changes immediately when true; otherwise only flush them.

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
            existing_member.clan_joined_at = self.get_effective_join_date(
                existing_member
            )
            logger.debug("Updated member %s with role %s.", tag, role)
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
                clan_joined_at=get_time(),
            )
            self.db.add(new_member)
            logger.info("Created new member %s with role %s.", tag, role)

        if commit:
            self.db.commit()
        else:
            self.db.flush()
        return existing_member or new_member

    def remove_member_from_clan(
        self, tag: str, reason: str = "left", *, commit: bool = True
    ) -> Member | None:
        """
        Mark a member as left/fired but preserve their war history. Sets role to 'left' or
        'fired' and clears active fields.

        Args:
            tag: Member's Clash Royale tag.
            reason: Reason for removal ('left' or 'fired').
            commit: Commit changes immediately when true; otherwise only flush them.

        Returns:
            Member | None: Updated member, or None when the tag is unknown.
        """
        member: Member | None = self.db.query(Member).filter_by(tag=tag).first()
        if member:
            member.role = reason
            member.last_seen = get_time()  # Record when they left
            if commit:
                self.db.commit()
            else:
                self.db.flush()
            logger.info("Member %s marked as %s.", tag, reason)
            return member

        logger.warning("Member %s not found.", tag)
        exmember_data = self.api_client.get_player(tag)
        self.create_or_update_member(
            tag=exmember_data.get("tag", ""),
            name=exmember_data.get("name", ""),
            role=reason,
            trophies=exmember_data.get("trophies", 0),
            donations=exmember_data.get("donations", 0),
            last_seen=exmember_data.get("lastSeen", ""),
            commit=commit,
        )
        return self.db.query(Member).filter_by(tag=tag).first()

    def promote_member(self, tag: str, new_role: str) -> bool:
        """
        Promote a member to a new role (e.g., member → elder, elder → coLeader). Validates
        role transitions and clan rules.

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

    def _inactive_members_query(self, days_threshold: int = 7):
        """
        Get a query for members who have been inactive for more than the specified number of
        days.

        Args:
            days_threshold: Number of days of inactivity to consider a member inactive.
                Defaults to 7.

        Returns:
            Query: SQLAlchemy query for inactive members.
        """
        cutoff_date = get_time() - timedelta(days=days_threshold)

        return self.db.query(Member).filter(
            and_(
                Member.last_seen.isnot(None),
                Member.last_seen < cutoff_date,
                Member.role.notin_(["left", "fired"]),
            )
        )

    def get_inactive_members(self, days_threshold: int = 7):
        """
        Get a list of members who have been inactive for more than the specified number of
        days.

        Args:
            days_threshold: Number of days of inactivity to consider a member inactive.
                Defaults to 7.

        Returns:
            List[Member]: List of inactive members.
        """
        return self._inactive_members_query(days_threshold).all()

    def count_inactive_members(self, days_threshold: int = 7):
        """
        Count the number of members who have been inactive for more than the specified
        number of days.

        Args:
            days_threshold: Number of days of inactivity to consider a member inactive.
                Defaults to 7.

        Returns:
            int: Count of inactive members.
        """
        return self._inactive_members_query(days_threshold).count()

    def get_active_members(self) -> List[Member]:
        """
        Get all active members (role != 'left' or 'fired').

        Args:
            None.

        Returns:
            List[Member]: List of active members.
        """
        return self.db.query(Member).filter(Member.role.notin_(["left", "fired"])).all()

    def increment_days_in_clan(self) -> int:
        """
        Increment days_in_clan by 1 for every currently-active member (role not in
        left/fired). Guarded by JobRunState so calling this more than once on the same
        calendar day is a safe no-op - intended to run once daily via the scheduler, but
        also safe to call from collect_data.py for manual/on-demand runs.

        Args:
            None.

        Returns:
            int: number of members incremented (0 if already run today).
        """
        today = get_time().date()

        state = (
            self.db.query(JobRunState)
            .filter_by(job_name="increment_membership_days")
            .first()
        )
        legacy = (
            self.db.query(JobRunState)
            .filter_by(job_name="increment_days_in_clan")
            .first()
        )
        if legacy:
            if state is None:
                legacy.job_name = "increment_membership_days"
                state = legacy
            else:
                dates = [d for d in (state.last_run_date, legacy.last_run_date) if d]
                state.last_run_date = max(dates) if dates else None
                self.db.delete(legacy)
            self.db.commit()
        if state and state.last_run_date == today:
            logger.info(
                "increment_days_in_clan already ran today (%s); skipping.", today
            )
            return 0

        active_members = (
            self.db.query(Member).filter(Member.role.notin_(["left", "fired"])).all()
        )
        for member in active_members:
            member.days_in_clan = (member.days_in_clan or 0) + 1

        if state:
            state.last_run_date = today
            state.last_attempt_at = get_time()
            state.last_success_at = get_time()
            state.last_error = None
        else:
            state = JobRunState(
                job_name="increment_membership_days",
                last_run_date=today,
                last_attempt_at=get_time(),
                last_success_at=get_time(),
            )
            self.db.add(state)

        self.db.commit()
        logger.info(
            "Incremented days_in_clan for %d active members.", len(active_members)
        )
        return len(active_members)

    def get_effective_join_date(self, member: Member) -> datetime | None:
        """
        Best-known date this member has been in the clan, correcting for clan_joined_at
        potentially being stamped later than reality (e.g. a historical war-log backfill can
        create a Member row - and stamp clan_joined_at "now" - well after their actual first
        appearance). Uses whichever is earlier: clan_joined_at, or their first known
        completed-race participation.

        Args:
            member: Member model whose stored metrics or relationships are used.

        Returns:
            datetime | None: Earliest known join/participation date, or None.
        """
        earliest_participation_date = (
            self.db.query(func.min(RiverRace.created_date))
            .join(WarParticipation, WarParticipation.river_race_id == RiverRace.id)
            .filter(
                WarParticipation.member_tag == member.tag,
                RiverRace.is_completed.is_(True),
            )
            .scalar()
        )

        candidates = [
            d
            for d in (member.clan_joined_at, earliest_participation_date)
            if d is not None
        ]
        return min(candidates) if candidates else None

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

        war_participations = (
            self.db.query(WarParticipation)
            .join(WarParticipation.river_race)
            .options(joinedload(WarParticipation.river_race))
            .filter(WarParticipation.member_tag == tag)
            .order_by(
                RiverRace.created_date.desc(),
                RiverRace.section_index.desc(),
            )
            .all()
        )

        return {
            "member": member,
            "snapshots": member.snapshots,
            "war_participations": war_participations,
            "contribution_scores": member.contribution_scores,
        }

    def add_ex_member(self, tag: str) -> None:
        """
        Add a member to the ex-members list (role = 'left').

        Args:
            tag: Member's Clash Royale tag.

        Returns:
            None.
        """
        member: Member | None = self.db.query(Member).filter_by(tag=tag).first()
        if member:
            member.role = "left"
            self.db.commit()
            logger.info("Member %s added to ex-members list.", tag)
        else:
            logger.warning("Member %s not found. Cannot add to ex-members list.", tag)

    @staticmethod
    def calculate_winrate(profile: dict[str, Any]) -> float:
        """Calculate wins as a percentage of decided battles.

        Args:
            profile: API profile containing wins and losses; missing counts are zero.
                battleCount is excluded because it can include draws.

        Returns:
            float: Percentage rounded to one decimal place, or zero without results.
        """
        wins = profile.get("wins", 0)
        losses = profile.get("losses", 0)
        decided_battles = wins + losses
        return round(wins / decided_battles * 100, 1) if decided_battles else 0.0

    def get_player_profile(
        self, member_tag: str, all_stats: bool = False, refresh: bool = False
    ) -> dict[str, Any]:
        """
        Returns all information known about a member.

        Args:
            member_tag: Clash Royale player tag.
            all_stats: If True, also returns cached/live Clash Royale API data.
            refresh: If True, forces a refresh of the Clash Royale API data, even if
                cached data exists.

        Returns:
            Dictionary containing local database information merged with Clash Royale API
            data.
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
            "contribution_score": member.contribution_score,
            "contribution_score_updated_at": member.contribution_score_updated_at,
        }

        if not all_stats:
            return member_data

        cache_dir = Path("data/cache/players")
        safe_tag = member_tag.lstrip("#")
        if not safe_tag or not safe_tag.isalnum():
            raise ValueError("Invalid player tag for profile cache.")
        cache_file = cache_dir / f"{safe_tag}.json"
        cached = None
        cache_updated_at = None
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            if not isinstance(cached, dict):
                cached = None
            else:
                cache_updated_at = datetime.fromtimestamp(cache_file.stat().st_mtime)
        except (OSError, ValueError):
            pass
        player_data = cached
        error = None
        if refresh or cached is None:
            try:
                player_data = self.api_client.get_player(member_tag, refresh=True)
                if not isinstance(player_data, dict):
                    raise ValueError("Invalid player profile response.")
                cache_dir.mkdir(parents=True, exist_ok=True)

                descriptor, temporary = tempfile.mkstemp(dir=cache_dir, suffix=".tmp")
                try:
                    with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                        json.dump(player_data, file)
                    os.replace(temporary, cache_file)
                finally:
                    Path(temporary).unlink(missing_ok=True)
                cache_updated_at = datetime.fromtimestamp(cache_file.stat().st_mtime)
            except Exception as exc:
                error = str(exc)
                player_data = cached
                logger.warning(
                    "Player profile refresh failed for %s: %s", member_tag, exc
                )
        member_data.update(
            api=player_data or {},
            api_data_updated_at=cache_updated_at,
            api_refresh_failed=error is not None,
        )
        if error:
            member_data["api_refresh_error"] = error
        return member_data
