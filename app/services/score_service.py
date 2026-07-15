"""
================================================================================
Filename: score_service.py
Description: Service for calculating promotion and kick scores for members.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-07-10
Version: 0.2.0
Python Version: 3.12
Dependencies: sqlalchemy, app.database.models, app.core.constants
================================================================================

NOTE: This is a minimal v0.7.0 implementation using the original 4-weight
formula (war activity / war performance / donations / trophy level). It will
be replaced by the full 7-component Contribution Score in v0.8.0.

War Performance is a fame-efficiency proxy (there is no wins/losses concept
in the current river race schema) rather than a literal win rate; the
'war_win_rate' field name is kept as-is to match the existing PromotionScore
schema, no migration needed for this minimal version.
"""

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.logger import logger
from app.core.constants import (
    WAR_ACTIVITY_WEIGHT,
    WAR_WIN_RATE_WEIGHT,
    DONATIONS_WEIGHT,
    TROPHY_LEVEL_WEIGHT,
    DONATION_TARGET,
    MAX_FAME_PER_RACE,
)
from app.core.utils import get_time, count
from app.database.models import Member, RiverRace, WarParticipation, PromotionScore


class ScoreService:
    """
    Service for calculating promotion and kick scores for clan members.

    Minimal v0.7.0 formula (replaced by the full Contribution Score in v0.8.0):
        - War Activity: 40%    (participated races / all-time available races)
        - War Performance: 30% (avg fame per participated race / MAX_FAME_PER_RACE)
        - Donations: 20%       (current donations / DONATION_TARGET)
        - Trophy Level: 10%    (trophies / clan max trophies)
    """

    def __init__(self, db_session: Session):
        self.db = db_session

    def _war_activity_score(self, member_tag: str) -> float:
        """
        Participated races / all COMPLETED races ever logged, all-time
        across every season. Scoped to completed races only, so a
        currently in-progress war doesn't distort the score before it's
        over. NOTE: this penalizes members who joined after some races
        already happened, since there's no join-date tracking yet (planned
        as the Seniority component in v0.8.0).
        """
        available_races = (
            self.db.query(count(RiverRace.id))
            .filter(RiverRace.is_completed.is_(True))
            .scalar()
            or 0
        )
        if not available_races:
            return 0

        participated_races = (
            self.db.query(count(func.distinct(WarParticipation.river_race_id)))
            .join(RiverRace, RiverRace.id == WarParticipation.river_race_id)
            .filter(
                WarParticipation.member_tag == member_tag,
                RiverRace.is_completed.is_(True),
            )
            .scalar()
            or 0
        )

        return min(100, (participated_races / available_races) * 100)

    def _war_performance_score(self, member_tag: str) -> float:
        """
        Average fame per participated COMPLETED race, normalized against
        the theoretical max fame achievable in a single river race.
        """
        avg_fame = (
            self.db.query(func.avg(WarParticipation.fame))
            .join(RiverRace, RiverRace.id == WarParticipation.river_race_id)
            .filter(
                WarParticipation.member_tag == member_tag,
                RiverRace.is_completed.is_(True),
            )
            .scalar()
            or 0
        )

        return min(100, (avg_fame / MAX_FAME_PER_RACE) * 100)

    def _donations_score(self, member: Member) -> float:
        """
        Current donations against the clan donation target.
        """
        return min(100, (member.donations / DONATION_TARGET) * 100)

    def _trophy_level_score(self, member: Member) -> float:
        """
        Trophies relative to the clan's current maximum (active members only).
        """
        clan_max_trophies = (
            self.db.query(func.max(Member.trophies))
            .filter(Member.role.notin_(["left", "fired"]))
            .scalar()
            or 0
        )

        if not clan_max_trophies:
            return 0

        return min(100, (member.trophies / clan_max_trophies) * 100)

    def calculate_promotion_score(self, member_tag: str) -> PromotionScore | None:
        """
        Calculate and persist a promotion score for one member.

        Creates a new PromotionScore row (preserving history) and updates
        Member.promotion_score / promotion_score_updated_at with the latest
        value.

        Args:
            member_tag: The member's Clash Royale tag.

        Returns:
            PromotionScore: the newly created score row, or None if the
            member doesn't exist.
        """
        member: Member | None = self.db.query(Member).filter_by(tag=member_tag).first()
        if not member:
            logger.warning("Cannot calculate score: member %s not found.", member_tag)
            return None

        war_activity = self._war_activity_score(member_tag)
        war_performance = self._war_performance_score(member_tag)
        donations = self._donations_score(member)
        trophy_level = self._trophy_level_score(member)

        final_score = (
            war_activity * WAR_ACTIVITY_WEIGHT
            + war_performance * WAR_WIN_RATE_WEIGHT
            + donations * DONATIONS_WEIGHT
            + trophy_level * TROPHY_LEVEL_WEIGHT
        )

        now: datetime = get_time()

        promotion_score = PromotionScore(
            member=member,
            score=final_score,
            war_activity=war_activity,
            war_win_rate=war_performance,
            donations=donations,
            trophy_level=trophy_level,
            calculated_at=now,
        )
        self.db.add(promotion_score)

        member.promotion_score = final_score
        member.promotion_score_updated_at = now

        self.db.commit()

        logger.info(
            "Calculated promotion score for %s: %.2f "
            "(activity=%.1f, performance=%.1f, donations=%.1f, trophies=%.1f)",
            member_tag,
            final_score,
            war_activity,
            war_performance,
            donations,
            trophy_level,
        )

        return promotion_score

    def calculate_all_scores(self) -> list[PromotionScore]:
        """
        Calculate and persist scores for every active member. Intended to
        be run as part of the automated data-collection pipeline.

        Returns:
            list[PromotionScore]: the newly created score rows.
        """
        active_members = (
            self.db.query(Member).filter(Member.role.notin_(["left", "fired"])).all()
        )

        scores: list[PromotionScore] = []
        for member in active_members:
            score = self.calculate_promotion_score(member.tag)
            if score:
                scores.append(score)

        logger.info("Calculated promotion scores for %d members.", len(scores))
        return scores
