"""
================================================================================
Filename: dashboard_service.py
Description: Service providing aggregated SQL statistics for the Streamlit dashboard.
Author: Raphael Smilet
Date Created: 2026-07-07
Last Modified: 2026-07-07
Version: 0.5.0
Python Version: 3.12
Dependencies: sqlalchemy, app.database.models
================================================================================
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import func, select

from app.database.models import (
    Member,
    Snapshot,
    PromotionScore,
    WarSeason,
    RiverRace,
    WarParticipation,
)

from app.services.clash_api import ClashAPIClient
from app.services.member_service import MemberService
from app.core.utils import count


class DashboardService:
    """
    Service exposing aggregated dashboard metrics.

    Every method performs SQL aggregation whenever possible in order to avoid
    loading unnecessary ORM objects into memory.
    """

    def __init__(self, db_session: Session, api_clash: ClashAPIClient = None) -> None:
        self.db = db_session
        self.api_clash = api_clash or ClashAPIClient()
        self.member_service = MemberService(db_session, self.api_clash)

    # ==========================================================================
    # Clan overview
    # ==========================================================================

    def get_overview_stats(self) -> dict[str, Any]:
        """
        Global clan KPIs.
        """

        member_count = self.member_service.get_active_members or 0

        avg_trophies = (
            self.db.query(func.avg(Member.trophies)).scalar() if member_count !=0  else 0
        )

        total_donations = self.db.query(
            func.coalesce(func.sum(Member.donations), 0)
        ).scalar()

        avg_promotion_score = (
            self.db.query(func.avg(Member.promotion_score))
            .filter(Member.promotion_score.isnot(None))
            .scalar()
            or 0
        )

        active_members = (
            self.db.query(count(Member.id))
            .filter(Member.role.notin_(["left", "fired"]))
            .scalar()
            or 0
        )

        return {
            "member_count": member_count,
            "active_members": active_members,
            "average_trophies": round(avg_trophies or 0),
            "total_donations": total_donations,
            "average_promotion_score": round(avg_promotion_score, 2),
        }

    def get_members_filter_by_role(self, role: str | None = None) -> list[Member]:
        """
        Returns all members in the database.
        """

        query = self.db.query(Member)
        if role:
            query = query.filter(Member.role == role)
        return query.all()

    # ==========================================================================
    # Database statistics
    # ==========================================================================

    def get_database_stats(self) -> dict[str, int]:
        """
        Number of stored entities.
        """

        return {
            "members": self.db.query(count(Member.id)).scalar() or 0,
            "snapshots": self.db.query(count(Snapshot.id)).scalar() or 0,
            "promotion_scores": self.db.query(count(PromotionScore.id)).scalar() or 0,
            "war_seasons": self.db.query(count(WarSeason.id)).scalar() or 0,
            "river_races": self.db.query(count(RiverRace.id)).scalar() or 0,
            "participations": self.db.query(count(WarParticipation.id)).scalar() or 0,
        }

    # ==========================================================================
    # War overview
    # ==========================================================================

    def get_war_stats(self) -> dict[str, Any]:
        """
        Aggregated war statistics.
        """

        race_count = self.db.query(count(RiverRace.id)).scalar() or 0
        participation_count = self.db.query(count(WarParticipation.id)).scalar() or 0

        return {
            "season_count": self.db.query(count(WarSeason.id)).scalar() or 0,
            "race_count": race_count,
            "participation_count": participation_count,
            "total_fame": (
                self.db.query(
                    func.coalesce(func.sum(WarParticipation.fame), 0)
                ).scalar()
            ),
            "total_repair_points": (
                self.db.query(
                    func.coalesce(func.sum(WarParticipation.repair_points), 0)
                ).scalar()
            ),
            "total_boat_attacks": (
                self.db.query(
                    func.coalesce(func.sum(WarParticipation.boat_attacks), 0)
                ).scalar()
            ),
            "total_decks_used": (
                self.db.query(
                    func.coalesce(func.sum(WarParticipation.decks_used), 0)
                ).scalar()
            ),
            "average_fame": (
                self.db.query(func.avg(WarParticipation.fame)).scalar() or 0
            ),
            "average_decks": (
                self.db.query(func.avg(WarParticipation.decks_used)).scalar() or 0
            ),
        }

    # ==========================================================================
    # Snapshot statistics
    # ==========================================================================

    def get_snapshot_stats(self) -> dict[str, Any]:
        """
        Snapshot statistics.
        """

        return {
            "snapshot_count": self.db.query(count(Snapshot.id)).scalar() or 0,
            "oldest_snapshot": self.db.query(func.min(Snapshot.collected_at)).scalar(),
            "latest_snapshot": self.db.query(func.max(Snapshot.collected_at)).scalar(),
            "average_trophies": (
                self.db.query(func.avg(Snapshot.trophies)).scalar() or 0
            ),
            "average_donations": (
                self.db.query(func.avg(Snapshot.donations)).scalar() or 0
            ),
        }

    # ==========================================================================
    # Promotion statistics
    # ==========================================================================

    def get_promotion_stats(self) -> dict[str, Any]:
        """
        Promotion score statistics.
        """

        return {
            "average_score": (
                self.db.query(func.avg(PromotionScore.score)).scalar() or 0
            ),
            "max_score": self.db.query(func.max(PromotionScore.score)).scalar(),
            "min_score": self.db.query(func.min(PromotionScore.score)).scalar(),
            "latest_calculation": (
                self.db.query(func.max(PromotionScore.calculated_at)).scalar()
            ),
        }

# ==========================================================================
    # Promotion dashboard
    # ==========================================================================

    def get_promotion_dashboard(self) -> dict[str, Any]:
        """
        Aggregated promotion dashboard: counts, extremes, and a ranking built
        from each member's most recent PromotionScore.
        """
        latest_scores = (
            self.db.query(
                PromotionScore.member_tag,
                func.max(PromotionScore.calculated_at).label("latest_calculated_at"),
            )
            .group_by(PromotionScore.member_tag)
            .subquery()
        )

        rows = (
            self.db.query(
                Member.name,
                PromotionScore.score,
                PromotionScore.war_activity,
                PromotionScore.war_win_rate,
                PromotionScore.donations,
                PromotionScore.trophy_level,
            )
            .join(Member, Member.tag == PromotionScore.member_tag)
            .join(
                latest_scores,
                (PromotionScore.member_tag == latest_scores.c.member_tag)
                & (
                    PromotionScore.calculated_at
                    == latest_scores.c.latest_calculated_at
                ),
            )
            .order_by(PromotionScore.score.desc())
            .all()
        )

        ranking = [
            {
                "name": row.name,
                "score": row.score,
                "war_activity": row.war_activity,
                "war_win_rate": row.war_win_rate,
                "donations": row.donations,
                "trophy_level": row.trophy_level,
            }
            for row in rows
        ]

        scores = [entry["score"] for entry in ranking]

        return {
            "score_count": len(ranking),
            "average_score": (sum(scores) / len(scores)) if scores else 0,
            "highest_score": max(scores) if scores else 0,
            "ranking": ranking,
        }

    def get_inactive_members(self, days_threshold: int = 14) -> list[dict[str, Any]]:
        """
        Members inactive for more than `days_threshold` days, as dashboard-ready
        dicts. Delegates the inactivity rule to MemberService (single source of
        truth for that logic).
        """
        inactive_members = self.member_service.get_inactive_members(days_threshold)

        return [
            {
                "tag": member.tag,
                "name": member.name,
                "role": member.role,
                "last_seen": member.last_seen,
                "trophies": member.trophies,
                "donations": member.donations,
            }
            for member in inactive_members
        ]

    def get_kick_candidates(self, days_threshold: int = 14) -> list[dict[str, Any]]:
        """
        Placeholder for kick-candidate detection.

        TODO (v0.8.0 - Decision Support Release): implement real kick-scoring
        using the KICK_SCORE_INACTIVE / KICK_SCORE_MISSED_WARS /
        KICK_SCORE_NO_DONATIONS constants (app.core.constants), once
        ScoreService.calculate_promotion_score is implemented. Returns an
        empty list for now so the dashboard renders without crashing.
        """
        return []

    # ==========================================================================
    # War dashboard
    # ==========================================================================

    def get_war_player_ranking(
        self, season_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Player performance ranking scoped to a single war season, by fame.
        """
        race_ids = (
            select(RiverRace.id)
            .where(RiverRace.season_id == season_id)
        )

        rows = (
            self.db.query(
                Member.tag,
                Member.name,
                func.sum(WarParticipation.fame).label("fame"),
                func.sum(WarParticipation.repair_points).label("repair"),
                func.sum(WarParticipation.boat_attacks).label("boats"),
                func.sum(WarParticipation.decks_used).label("decks"),
            )
            .join(WarParticipation, WarParticipation.member_tag == Member.tag)
            .filter(WarParticipation.river_race_id.in_(race_ids))
            .group_by(Member.tag, Member.name)
            .order_by(func.sum(WarParticipation.fame).desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "member_tag": row.tag,
                "name": row.name,
                "fame": row.fame,
                "repair": row.repair,
                "boats": row.boats,
                "decks": row.decks,
            }
            for row in rows
        ]

    def get_river_races(self, season_id: str) -> list[dict[str, Any]]:
        """
        River races for a season with participant counts, ordered by section.
        """
        rows = (
            self.db.query(
                RiverRace.section_index,
                RiverRace.created_date,
                count(func.distinct(WarParticipation.member_tag)).label(
                    "participants"
                ),
            )
            .outerjoin(
                WarParticipation, WarParticipation.river_race_id == RiverRace.id
            )
            .filter(RiverRace.season_id == season_id)
            .group_by(RiverRace.id, RiverRace.section_index, RiverRace.created_date)
            .order_by(RiverRace.section_index)
            .all()
        )

        return [
            {
                "section_index": row.section_index,
                "created_date": row.created_date,
                "participants": row.participants,
            }
            for row in rows
        ]

    def get_player_war_stats(
        self, member_tag: str, season_id: str | None = None
    ) -> dict[str, Any]:
        """
        Aggregated war stats for a single player.
        If season_id is given, stats are scoped to that season; otherwise
        stats are all-time across every season.
        """
        query = self.db.query(
            func.coalesce(func.sum(WarParticipation.fame), 0).label("fame"),
            func.coalesce(func.sum(WarParticipation.repair_points), 0).label(
                "repair_points"
            ),
            func.coalesce(func.sum(WarParticipation.boat_attacks), 0).label(
                "boat_attacks"
            ),
            func.coalesce(func.sum(WarParticipation.decks_used), 0).label(
                "decks_used"
            ),
        ).filter(WarParticipation.member_tag == member_tag)

        if season_id is not None:
            query = query.join(
                RiverRace, RiverRace.id == WarParticipation.river_race_id
            ).filter(RiverRace.season_id == season_id)

        row = query.one()

        return {
            "fame": row.fame,
            "repair_points": row.repair_points,
            "boat_attacks": row.boat_attacks,
            "decks_used": row.decks_used,
        }


    # ==========================================================================
    # Charts
    # ==========================================================================

    def get_daily_snapshot_history(self) -> list[dict]:
        """
        Daily averages for line charts.
        """

        rows = (
            self.db.query(
                func.date(Snapshot.collected_at).label("date"),
                func.avg(Snapshot.trophies).label("avg_trophies"),
                func.avg(Snapshot.donations).label("avg_donations"),
            )
            .group_by(func.date(Snapshot.collected_at))
            .order_by(func.date(Snapshot.collected_at))
            .all()
        )

        return [
            {
                "date": row.date,
                "avg_trophies": float(row.avg_trophies),
                "avg_donations": float(row.avg_donations),
            }
            for row in rows
        ]

    def get_role_distribution(self) -> list[dict]:
        """
        Number of members by role.
        """

        rows = (
            self.db.query(
                Member.role,
                count(Member.id),
            )
            .group_by(Member.role)
            .order_by(count(Member.id).desc())
            .all()
        )

        return [
            {
                "role": role,
                "count": count,
            }
            for role, count in rows
        ]

    def get_top_members_by_trophies(self, limit: int = 10) -> list[Member]:
        """
        Top members ordered by trophies.
        """

        return self.db.query(Member).order_by(Member.trophies.desc()).limit(limit).all()

    def get_top_members_by_donations(self, limit: int = 10) -> list[Member]:
        """
        Top members ordered by donations.
        """

        return (
            self.db.query(Member).order_by(Member.donations.desc()).limit(limit).all()
        )

    def get_top_members_by_promotion_score(
        self,
        limit: int = 10,
    ) -> list[Member]:
        """
        Top members ordered by promotion score.
        """

        return (
            self.db.query(Member)
            .filter(Member.promotion_score.isnot(None))
            .order_by(Member.promotion_score.desc())
            .limit(limit)
            .all()
        )

    def get_top_war_players(self, limit: int = 10) -> list:
        """
        Total war performance aggregated by player.
        """

        return (
            self.db.query(
                Member.tag,
                Member.name,
                func.sum(WarParticipation.fame).label("fame"),
                func.sum(WarParticipation.repair_points).label("repair"),
                func.sum(WarParticipation.boat_attacks).label("boats"),
                func.sum(WarParticipation.decks_used).label("decks"),
            )
            .join(
                WarParticipation,
                WarParticipation.member_tag == Member.tag,
            )
            .group_by(Member.tag, Member.name)
            .order_by(func.sum(WarParticipation.fame).desc())
            .limit(limit)
            .all()
        )

    # ==========================================================================
    # Season helpers
    # ==========================================================================

    def get_available_seasons(self) -> list[WarSeason]:
        """
        Returns all seasons ordered by newest first.
        """

        return self.db.query(WarSeason).order_by(WarSeason.start_date.desc()).all()

    def get_season_summary(self, season_id: str) -> dict[str, Any]:
        """
        Aggregated statistics for one season.
        """

        race_ids = (
            select(RiverRace.id)
            .where(RiverRace.season_id == season_id)
        )

        return {
            "race_count": (
                self.db.query(count(RiverRace.id))
                .filter(RiverRace.season_id == season_id)
                .scalar()
                or 0
            ),
            "participants": (
                self.db.query(count(func.distinct(WarParticipation.member_tag)))
                .filter(WarParticipation.river_race_id.in_(race_ids))
                .scalar()
                or 0
            ),
            "total_fame": (
                self.db.query(func.coalesce(func.sum(WarParticipation.fame), 0))
                .filter(WarParticipation.river_race_id.in_(race_ids))
                .scalar()
            ),
            "total_repairs": (
                self.db.query(
                    func.coalesce(func.sum(WarParticipation.repair_points), 0)
                )
                .filter(WarParticipation.river_race_id.in_(race_ids))
                .scalar()
            ),
            "total_decks": (
                self.db.query(func.coalesce(func.sum(WarParticipation.decks_used), 0))
                .filter(WarParticipation.river_race_id.in_(race_ids))
                .scalar()
            ),
        }
