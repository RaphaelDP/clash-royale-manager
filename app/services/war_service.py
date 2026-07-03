"""
================================================================================
Filename: war_service.py
Description: Service for managing war data, including river races and participation.
Author: Raphael Smilet
Date Created: 2026-06-09
Last Modified: 2026-06-18
Version: 0.4.2
Python Version: 3.12
Dependencies: sqlalchemy, app.database.models, app.core.logger, app.core.utils, app.services.clash_api
================================================================================

"""

from typing import List, Dict, Any
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from app.core.logger import logger
from app.core.utils import convert_timestamp_to_datetime
from app.database.models import WarSeason, RiverRace, Member, WarParticipation
from app.services.clash_api import ClashAPIClient


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

    def sync_river_race_log(self, clan_tag: str) -> None:
        """
        Sync the river race log for a clan from the Clash Royale API.
        Only stores data for the specified clan.

        Args:
            clan_tag: The clan tag (e.g., "#Q8YG902J").
        """
        try:
            river_race_log: List[Dict[str, Any]] = self.api_client.get_river_race_log(
                clan_tag
            )

            for race_data in river_race_log:

                # Create or update the war season
                war_season: WarSeason = self._create_or_update_season(
                    season_id=str(race_data.get("seasonId", "")),
                    start_date=convert_timestamp_to_datetime(
                        race_data.get("createdDate", "")
                    ),
                )

                # Create or update the river race
                river_race: RiverRace = self._create_or_update_river_race(
                    season_id=war_season.season_id,
                    section_index=race_data.get("sectionIndex", 0),
                    created_date=convert_timestamp_to_datetime(
                        race_data.get("createdDate", "")
                    ),
                )

                # Find your clan's data in the standings
                your_clan_data = self._find_clan_data(
                    race_data.get("standings", []), clan_tag
                )
                if not your_clan_data:
                    logger.warning(
                        "No data found for clan %s in race %s-%s",
                        clan_tag,
                        race_data.get("seasonId"),
                        race_data.get("sectionIndex"),
                    )
                    continue

                # Create or update participations for your clan's members
                for participant in your_clan_data.get("participants", []):
                    self._create_or_update_participation(
                        river_race_id=river_race.id,
                        member_tag=participant.get("tag", ""),
                        fame=participant.get("fame", 0),
                        repair_points=participant.get("repairPoints", 0),
                        boat_attacks=participant.get("boatAttacks", 0),
                        decks_used=participant.get("decksUsed", 0),
                        decks_used_today=participant.get("decksUsedToday", 0),
                    )

            self.db.commit()
            logger.info("Synced river race log for clan %s.", clan_tag)
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to sync river race log: %s", e)
            raise

    def sync_current_river_race(self, clan_tag: str) -> None:
        """
        Sync the current river race for a clan from the Clash Royale API.

        Args:
            clan_tag: The clan tag (e.g., "#Q8YG902J").
        """
        try:
            current_race_data: Dict[str, Any] = self.api_client.get_current_river_race(
                clan_tag
            )

            # Extract your clan's data from the response
            your_clan_data = current_race_data.get("clan", {})
            if not your_clan_data:
                logger.warning(
                    "No current river race data found for clan %s.", clan_tag
                )
                return

            # Use the latest season from the database
            latest_season: WarSeason | None = (
                self.db.query(WarSeason).order_by(WarSeason.id.desc()).first()
            )
            if not latest_season:
                logger.warning("No war seasons found. Sync river race log first.")
                return


            # Create or update the river race
            river_race: RiverRace = self._create_or_update_river_race(
                season_id=latest_season.season_id,
                section_index=current_race_data.get("sectionIndex", 0),
                created_date=datetime.now(UTC),  # Use current time (API doesn't provide createdDate)
            )



            # Create or update participations for your clan's members
            for participant in your_clan_data.get("participants", []):
                self._create_or_update_participation(
                    river_race_id=river_race.id,
                    member_tag=participant.get("tag", ""),
                    fame=participant.get("fame", 0),
                    repair_points=participant.get("repairPoints", 0),
                    boat_attacks=participant.get("boatAttacks", 0),
                    decks_used=participant.get("decksUsed", 0),
                    decks_used_today=participant.get("decksUsedToday", 0),
                )

            self.db.commit()
            logger.info("Synced current river race for clan %s.", clan_tag)
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to sync current river race: %s", e)
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
    ) -> RiverRace:
        """
        Create or update a river race.

        Args:
            season_id: The associated war season ID.
            section_index: Index of the river race section.
            created_date: Creation date of the river race.

        Returns:
            RiverRace: The created or updated RiverRace object.
        """
        existing_race: RiverRace | None = (
            self.db.query(RiverRace)
            .filter_by(season_id=season_id, section_index=section_index)
            .first()
        )
        if existing_race:
            return existing_race
        new_race: RiverRace = RiverRace(
            season_id=season_id,
            section_index=section_index,
            created_date=created_date,
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
    ) -> WarParticipation:
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

        Returns:
            WarParticipation: The created or updated WarParticipation object.
        """
        existing_participation: WarParticipation | None = (
            self.db.query(WarParticipation)
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

        river_race: RiverRace = (
            self.db.query(RiverRace).filter_by(id=river_race_id).first()
        )
        member: Member = self.db.query(Member).filter_by(tag=member_tag).first()

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
