"""
================================================================================
Filename: war_service.py
Description: Service for managing war data, including river races and participation.
Author: Raphael Smilet
Date Created: 2026-06-09
Last Modified: 2026-09-30
Version: 0.4.3
Python Version: 3.12
Dependencies: sqlalchemy, app.database.models, app.core.logger, app.core.utils, app.services.clash_api
================================================================================

"""

from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.logger import logger
from app.core.utils import convert_timestamp_to_datetime, get_time
from app.database.models import WarSeason, RiverRace, Member, WarParticipation
from app.services.clash_api import ClashAPIClient
from app.services.member_service import MemberService


class WarService:
    """Service for managing war data, including river races and participation."""

    def __init__(self, db_session: Session, api_client: ClashAPIClient = None) -> None:
        """
        Initialize the WarService with a database session and API client.
        Args:
            db_session: SQLAlchemy database session for interacting with the database.
            api_client: Optional ClashAPIClient instance. If not provided, a new instance will be

        """
        self.db: Session = db_session
        self.api_client: ClashAPIClient = api_client or ClashAPIClient()
        self.member_service: MemberService = MemberService(db_session, self.api_client)

    def _sync_participants(self, race, participants):
        if not isinstance(participants, list):
            raise ValueError("Missing war participants list.")
        existing = {
            p.member_tag: p
            for p in self.db.query(WarParticipation)
            .filter_by(river_race_id=race.id)
            .all()
        }
        tags = [p.get("tag") for p in participants]
        if any(not tag for tag in tags) or len(tags) != len(set(tags)):
            raise ValueError("Invalid or duplicate war participant tags.")
        members = {
            m.tag: m for m in self.db.query(Member).filter(Member.tag.in_(tags)).all()
        }
        for participant in participants:
            tag = participant["tag"]
            if tag not in members:
                # Historical participants need no additional live API lookup.
                member = Member(
                    tag=tag,
                    name=participant.get("name") or tag,
                    role="left",
                    days_in_clan=0,
                )
                self.db.add(member)
                self.db.flush()
                members[tag] = member
            record = self._create_or_update_participation(
                river_race_id=race.id,
                member_tag=tag,
                fame=participant.get("fame", 0),
                repair_points=participant.get("repairPoints", 0),
                boat_attacks=participant.get("boatAttacks", 0),
                decks_used=participant.get("decksUsed", 0),
                decks_used_today=participant.get("decksUsedToday", 0),
                river_race=race,
                existing_participations=existing,
                member_lookup=members,
            )
            if record is None:
                raise ValueError(f"Unable to store participant {tag}.")
            existing[tag] = record

    def sync_river_race_log(self, clan_tag: str) -> None:
        """Store complete historical results atomically; never hide partial failures."""
        try:
            races = self.api_client.get_river_race_log(clan_tag)
            if not isinstance(races, list):
                raise ValueError("Invalid river race log.")
            for data in races:
                clan = self._find_clan_data(data.get("standings", []), clan_tag)
                if clan is None:
                    raise ValueError("Requested clan missing from race standings.")
                date = convert_timestamp_to_datetime(data.get("createdDate"))
                if (
                    date is None
                    or data.get("seasonId") is None
                    or not isinstance(data.get("sectionIndex"), int)
                ):
                    raise ValueError("Invalid historical race identity.")
                season = self._create_or_update_season(str(data["seasonId"]), date)
                race = self._create_or_update_river_race(
                    season.season_id, data["sectionIndex"], date, is_completed=True
                )
                self._sync_participants(race, clan.get("participants"))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def sync_current_river_race(self, clan_tag: str) -> None:
        """Resolve live identity from chronological history, protecting closed results."""
        try:
            data = self.api_client.get_current_river_race(clan_tag)
            clan = data.get("clan")
            if not isinstance(clan, dict) or clan.get("tag", clan_tag) != clan_tag:
                raise ValueError("Missing or mismatched live race clan.")
            section = data.get("sectionIndex")
            if not isinstance(section, int) or section < 0:
                raise ValueError("Missing live race section index.")
            latest = (
                self.db.query(RiverRace)
                .filter(RiverRace.is_completed.is_(True))
                .order_by(RiverRace.created_date.desc())
                .first()
            )
            season = (
                self.db.query(WarSeason).order_by(WarSeason.start_date.desc()).first()
            )
            if data.get("seasonId") is not None:
                season_id = str(data["seasonId"])
            elif latest is not None:
                season_id = latest.season_id
                if section < latest.section_index:
                    # A reset to section zero identifies the next numeric season.
                    if section != 0 or not season_id.isdigit():
                        raise ValueError(
                            "Ambiguous live season; completed results were preserved."
                        )
                    season_id = str(int(season_id) + 1)
            elif season is not None:
                season_id = season.season_id
            else:
                raise ValueError(
                    "No historical season available to identify the live race."
                )
            race = (
                self.db.query(RiverRace)
                .filter_by(season_id=season_id, section_index=section)
                .first()
            )
            if race is not None and race.is_completed:
                # The live endpoint may lag the log at a weekly/season boundary.
                return
            if self.db.query(WarSeason).filter_by(season_id=season_id).first() is None:
                self._create_or_update_season(season_id, get_time())
            race = self._create_or_update_river_race(
                season_id, section, get_time(), is_completed=False
            )
            self._sync_participants(race, clan.get("participants"))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def _find_clan_data(
        self, standings: List[Dict[str, Any]], clan_tag: str
    ) -> Dict[str, Any] | None:
        """
        Find your clan's data in the standings of a river race.

        Args:
            standings: List of standings from the API.
            clan_tag: The clan tag to search for.

        Returns:
            Dict[str, Any] | None: Your clan's data, or None if not found.
        """
        for standing in standings:
            clan_info = standing.get("clan", {})
            if clan_info.get("tag") == clan_tag:
                return clan_info
        return None

    def _create_or_update_season(
        self,
        season_id: str,
        start_date: datetime | None,
    ) -> WarSeason:
        """
        Create or update a war season.

        Args:
            season_id: Unique identifier for the war season.
            start_date: Start date of the season.

        Returns:
            WarSeason: The created or updated WarSeason object.
        """
        existing_season: WarSeason | None = (
            self.db.query(WarSeason).filter_by(season_id=season_id).first()
        )

        if existing_season:
            if start_date is not None and (
                existing_season.start_date is None
                or start_date < existing_season.start_date
            ):
                existing_season.start_date = start_date

            return existing_season

        new_season = WarSeason(
            season_id=season_id,
            start_date=start_date,
        )

        self.db.add(new_season)
        self.db.flush()
        return new_season

    def _create_or_update_river_race(
        self,
        season_id: str,
        section_index: int,
        created_date: datetime,
        is_completed: bool = False,
    ) -> RiverRace:
        """
        Create or update a river race.

        Args:
            season_id: The associated war season ID.
            section_index: Index of the river race section.
            created_date: Creation date of the river race.
            is_completed: Whether this race is confirmed complete (True from
                sync_river_race_log, False from sync_current_river_race). An
                existing race only ever flips False -> True, never back.

        Returns:
            RiverRace: The created or updated RiverRace object.
        """
        existing_race: RiverRace | None = (
            self.db.query(RiverRace)
            .filter_by(season_id=season_id, section_index=section_index)
            .first()
        )
        if existing_race:
            if is_completed:
                existing_race.is_completed = True
                existing_race.created_date = created_date
                self.db.flush()
            return existing_race
        new_race: RiverRace = RiverRace(
            season_id=season_id,
            section_index=section_index,
            created_date=created_date,
            is_completed=is_completed,
        )
        self.db.add(new_race)
        self.db.flush()
        return new_race

    def _create_or_update_participation(
        self,
        river_race_id: int,
        member_tag: str,
        fame: int,
        repair_points: int,
        boat_attacks: int,
        decks_used: int,
        decks_used_today: int,
        river_race: RiverRace | None = None,
        existing_participations: dict[str, WarParticipation] | None = None,
        member_lookup: dict[str, Member] | None = None,
    ) -> WarParticipation | None:
        """
        Create or update a war participation record.

        Args:
            river_race_id: The associated river race ID.
            member_tag: The member's Clash Royale tag.
            fame: Fame points earned.
            repair_points: Repair points earned.
            boat_attacks: Number of boat attacks.
            decks_used: Number of decks used.
            decks_used_today: Number of decks used today.
            river_race: Optional pre-fetched RiverRace, avoiding a
                redundant query when the caller already has it (both
                sync loops do).
            existing_participations: Optional {member_tag: WarParticipation}
                map for this river_race, pre-fetched once per race sync
                instead of querying per participant. Falls back to a
                per-call query when not provided (e.g. direct calls,
                including tests).
            member_lookup: Optional {tag: Member} map of already-known
                members, pre-fetched once per sync batch instead of
                querying per participant. Same fallback behavior.

        Returns:
            WarParticipation: The created or updated WarParticipation object.
        """

        if not member_tag:
            logger.warning(
                "Skipping participation with empty member_tag for river_race_id=%s, member_tag=%s",
                river_race_id,
                member_tag,
            )
            return None

        existing_participation = (
            existing_participations.get(member_tag)
            if existing_participations is not None
            else self.db.query(WarParticipation)
            .filter_by(river_race_id=river_race_id, member_tag=member_tag)
            .first()
        )

        if existing_participation:
            existing_participation.fame = fame
            existing_participation.repair_points = repair_points
            existing_participation.boat_attacks = boat_attacks
            existing_participation.decks_used = decks_used
            existing_participation.decks_used_today = decks_used_today
            return existing_participation

        if river_race is None:
            river_race = self.db.query(RiverRace).filter_by(id=river_race_id).first()

        member: Member | None = (
            member_lookup.get(member_tag)
            if member_lookup is not None
            else self.db.query(Member).filter_by(tag=member_tag).first()
        )
        if not member:
            try:
                member = self.member_service.remove_member_from_clan(
                    member_tag, reason="left", commit=False
                )
            except Exception as e:
                logger.error(
                    "Failed to find member with tag %s in the clan members history: %s",
                    member_tag,
                    e,
                )
                member = None

        if not member:
            logger.warning(
                "Skipping participation for unresolved member %s in river_race_id=%s.",
                member_tag,
                river_race_id,
            )
            return None

        new_participation: WarParticipation = WarParticipation(
            river_race=river_race,
            member=member,
            fame=fame,
            repair_points=repair_points,
            boat_attacks=boat_attacks,
            decks_used=decks_used,
            decks_used_today=decks_used_today,
        )
        self.db.add(new_participation)
        self.db.flush()
        return new_participation
