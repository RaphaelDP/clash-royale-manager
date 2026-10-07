"""
================================================================================
Filename: war_service.py
Description: Service for managing war data, including river races and participation.
Author: Raphael Smilet
Date Created: 2026-06-09
Last Modified: 2026-10-07
Version: 0.4.10
Python Version: 3.12
Dependencies: sqlalchemy, app.database.models, app.core.logger, app.core.utils, app.services.clash_api
================================================================================

"""

from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from sqlalchemy.orm import Session
from app.core.logger import logger
from app.core.constants import MAX_LIVE_HISTORY_AGE_DAYS
from app.core.utils import convert_timestamp_to_datetime, get_time
from app.database.models import WarSeason, RiverRace, Member, WarParticipation
from app.services.clash_api import ClashAPIClient
from app.services.member_service import MemberService


class WarService:
    """Service for managing war data, including river races and participation."""

    def __init__(self, db_session: Session, api_client: ClashAPIClient = None) -> None:
        """
        Initialize WarService with its configured dependencies.

        Args:
            db_session: SQLAlchemy database session for interacting with the database.
            api_client: Optional ClashAPIClient; a new client is created when omitted.

        Returns:
            None.
        """
        self.db: Session = db_session
        self.api_client: ClashAPIClient = api_client or ClashAPIClient()
        self.member_service: MemberService = MemberService(db_session, self.api_client)

    @staticmethod
    def summarize_participations(
        participations: list[WarParticipation],
    ) -> dict[str, int]:
        """Aggregate the supplied player's historical and live participation records.

        Args:
            participations: Records already selected for the desired player and scope.
                Zero-deck records count as participation rows, not as attacks.

        Returns:
            dict[str, int]: Record count and summed fame, boat attacks, and decks.
                Empty input produces zero for every metric.
        """
        return {
            "count": len(participations),
            "total_fame": sum(record.fame for record in participations),
            "total_boats": sum(record.boat_attacks for record in participations),
            "total_decks": sum(record.decks_used for record in participations),
        }

    def observe_identity(
        self,
        clan_tag: str,
        confirm_season: str | None = None,
        confirm_section: int | None = None,
    ) -> dict[str, Any]:
        """Synchronize a fresh API sample and project identity-only evidence.

        Use a disposable database: this method commits historical and live race
        synchronization through the normal service methods. Runtime isolation,
        credential loading, and output persistence belong to the caller.

        Args:
            clan_tag: Requested clan tag, excluded from the returned evidence.
            confirm_season: Optional expected season, supplied together with section.
            confirm_section: Expected nonnegative section to confirm in fresh history.

        Returns:
            dict[str, Any]: UTC observation time, explicit-ID presence, live
            section, and race identities with scheduler-local timestamps. When a target
            is supplied, confirmation is confirmed or pending; live inference alone
            never confirms a target.

        Raises:
            Exception: API or synchronization failure; callers must avoid exposing
                raw request errors that may contain private response details.
        """
        if confirm_season is not None or confirm_section is not None:
            if (
                not isinstance(confirm_season, str)
                or not confirm_season.strip()
                or not isinstance(confirm_section, int)
                or isinstance(confirm_section, bool)
                or confirm_section < 0
            ):
                raise ValueError(
                    "Confirmation requires a season and nonnegative section."
                )
        with self.api_client.session.cache_disabled():
            history = self.api_client.get_river_race_log(clan_tag)
            current = self.api_client.get_current_river_race(clan_tag)
        # Replay exactly the captured pair through normal validation and writes.
        captured = SimpleNamespace(
            get_river_race_log=lambda _: history,
            get_current_river_race=lambda _: current,
        )
        service = WarService(self.db, captured)
        service.sync_river_race_log(clan_tag)
        service.sync_current_river_race(clan_tag)
        races = (
            self.db.query(RiverRace)
            .order_by(RiverRace.created_date, RiverRace.id)
            .all()
        )
        result = {
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "ok": True,
            "explicit_live_season": current.get("seasonId") is not None,
            "live_section": current["sectionIndex"],
            "period_type": current.get("periodType"),
            "period_index": current.get("periodIndex"),
            "races": [
                {
                    "season": race.season_id,
                    "section": race.section_index,
                    "completed": race.is_completed,
                    "timestamp": race.created_date.isoformat(),
                }
                for race in races
            ],
        }
        if confirm_season is not None:
            # Require this API log to contain the target, not a pre-existing DB row.
            confirmed = any(
                str(race.get("seasonId")) == confirm_season
                and race.get("sectionIndex") == confirm_section
                for race in history
            )
            result["confirmation"] = {
                "season": confirm_season,
                "section": confirm_section,
                "status": "confirmed" if confirmed else "pending",
            }
        return result

    def _sync_participants(self, race, participants):
        """
        Validate and upsert one race's participants in the caller's transaction.

        Unknown historical players are retained as departed members. No commit is made.

        Args:
            race: RiverRace instance whose participant records are synchronized.
            participants: API participant dictionaries for the selected clan and race.

        Returns:
            None.
        """
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
        """
        Store complete historical results atomically; never hide partial failures.

        Args:
            clan_tag: Clash Royale clan tag, including its leading #.

        Returns:
            None.
        """
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
        """
        Resolve live identity from chronological history, protecting closed results.

        Args:
            clan_tag: Clash Royale clan tag, including its leading #.

        Returns:
            None.
        """
        try:
            data = self.api_client.get_current_river_race(clan_tag)
            clan = data.get("clan")
            if not isinstance(clan, dict) or clan.get("tag") != clan_tag:
                raise ValueError("Missing or mismatched live race clan.")
            section = data.get("sectionIndex")
            if isinstance(section, bool) or not isinstance(section, int) or section < 0:
                raise ValueError("Missing live race section index.")
            period_type = data.get("periodType")
            if period_type not in (None, "training", "warDay", "colosseum"):
                raise ValueError(
                    "Unrecognized API war phase; participation was not updated."
                )
            season_id = self._resolve_live_season(data, section)
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
            self._store_live_phase(data, race)
            if race.type_of_day == "training":
                race.war_participations.clear()
            else:
                self._sync_participants(race, clan.get("participants"))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def _store_live_phase(self, data, race):
        """Store the weekly race phase, rejecting stale observations.

        Args:
            data: Validated current-race API response.
            race: Open weekly race whose phase is being synchronized.

        Returns:
            None. The caller owns the transaction.
        """
        index = data.get("periodIndex")
        if index is not None and (
            isinstance(index, bool) or not isinstance(index, int) or index < 0
        ):
            raise ValueError("Invalid API war period index.")
        latest = (
            self.db.query(RiverRace)
            .filter_by(season_id=race.season_id)
            .filter(RiverRace.period_index.isnot(None))
            .order_by(RiverRace.period_index.desc())
            .first()
        )
        if latest is not None and index is not None and index < latest.period_index:
            raise ValueError(
                "Regressing API war period; previous observation preserved."
            )
        kind = data.get("periodType")
        if race.type_of_day == "battle" and kind == "training":
            raise ValueError(
                "Training response cannot replace an observed battle phase."
            )
        if kind is not None:
            race.type_of_day = "training" if kind == "training" else "battle"
        race.period_index = index if index is not None else race.period_index
        race.observed_at = get_time()

    def _resolve_live_season(self, data: dict[str, Any], section: int) -> str:
        """Resolve a live season only from an explicit ID or recent adjacent history.

        A bare season row is insufficient evidence. Inferred identity requires a
        completed race no more than MAX_LIVE_HISTORY_AGE_DAYS old and no future
        timestamp. An adjacent section or numeric season reset remains a heuristic;
        an actual season-boundary response still needs acceptance testing.

        Args:
            data: Live API response, optionally containing an explicit seasonId.
            section: Validated nonnegative live section index.

        Returns:
            str: Explicit or conservatively inferred season identifier.

        Raises:
            ValueError: Identity is malformed, historical evidence is unavailable
                or stale, or the section transition is ambiguous.
        """
        explicit = data.get("seasonId")
        if explicit is not None:
            if (
                isinstance(explicit, bool)
                or not isinstance(explicit, (str, int))
                or not str(explicit).strip()
                or isinstance(explicit, int)
                and explicit < 0
            ):
                raise ValueError("Invalid explicit live season ID.")
            return str(explicit).strip()

        latest = (
            self.db.query(RiverRace)
            .filter(RiverRace.is_completed.is_(True))
            .order_by(RiverRace.created_date.desc(), RiverRace.id.desc())
            .first()
        )
        if latest is None or latest.created_date is None:
            raise ValueError(
                "No historical season with completed race data is available; "
                "refresh war history before syncing the live race."
            )
        age = get_time() - latest.created_date
        if not timedelta(0) <= age <= timedelta(days=MAX_LIVE_HISTORY_AGE_DAYS):
            raise ValueError(
                "Stale or future-dated war history cannot identify the live season; "
                "refresh war history. Existing race results were preserved."
            )
        if section in (latest.section_index, latest.section_index + 1):
            return latest.season_id
        if section == 0 and latest.section_index > 0 and latest.season_id.isdigit():
            return str(int(latest.season_id) + 1)
        raise ValueError(
            "Ambiguous live season: non-adjacent race sections; "
            "refresh war history. Existing race results were preserved."
        )

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
                sync_river_race_log, False from sync_current_river_race). An existing
                race only ever flips False -> True, never back.

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
                existing_race.type_of_day = "battle"
                existing_race.created_date = created_date
                self.db.flush()
            return existing_race
        new_race: RiverRace = RiverRace(
            season_id=season_id,
            section_index=section_index,
            created_date=created_date,
            is_completed=is_completed,
            type_of_day="battle" if is_completed else "unknown",
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
            river_race: Optional pre-fetched RiverRace, avoiding a redundant query when
                the caller already has it (both sync loops do).
            existing_participations: Optional {member_tag: WarParticipation} map for
                this river_race, pre-fetched once per race sync instead of querying per
                participant. Falls back to a per-call query when not provided (e.g.
                direct calls, including tests).
            member_lookup: Optional {tag: Member} map of already-known members,
                pre-fetched once per sync batch instead of querying per participant.
                Same fallback behavior.

        Returns:
            WarParticipation | None: Upserted record, or None if race/member resolution
            fails.
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
