"""
================================================================================
Filename: dashboard_service.py
Description: Service providing aggregated SQL statistics for the Streamlit dashboard.
Author: Raphael Smilet
Date Created: 2026-07-07
Last Modified: 2026-07-10
Version: 0.6.0
Python Version: 3.12
Dependencies: sqlalchemy, app.database.models
================================================================================
"""

from __future__ import annotations

from typing import Any
from datetime import timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func, select

from app.database.models import (
    Member,
    Snapshot,
    ContributionScore,
    WarSeason,
    RiverRace,
    WarParticipation,
)
from app.services.score_service import ScoreService
from app.services.clash_api import ClashAPIClient
from app.services.member_service import MemberService
from app.core.utils import count, get_time, activity_score_from_days
from app.core.constants import (
    EXPECTED_FAME_PER_PLAYER,
    DONATION_TARGET,
    GROWTH_TARGET_TROPHIES,
    RETENTION_WINDOW_DAYS,
    RETENTION_WINDOW_TOLERANCE_DAYS,
    GROWTH_WINDOW_DAYS,
    INACTIVE_DAYS,
    VERY_INACTIVE_DAYS,
    CLAN_HEALTH_WEIGHTS,
    MAX_DECKS_PER_RACE,
    MAX_FAME_PER_RACE,
)


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

        member_count = len(self.member_service.get_active_members() or 0)

        avg_trophies = (
            self.db.query(func.avg(Member.trophies)).scalar()
            if member_count != 0
            else 0
        )

        total_donations = self.db.query(
            func.coalesce(func.sum(Member.donations), 0)
        ).scalar()

        avg_contribution_score = (
            self.db.query(func.avg(Member.contribution_score))
            .filter(Member.contribution_score.isnot(None))
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
            "average_promotion_score": round(avg_contribution_score, 2),
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
            "promotion_scores": self.db.query(count(ContributionScore.id)).scalar()
            or 0,
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

    def get_contribution_stats(self) -> dict[str, Any]:
        """
        Promotion score statistics.
        """

        return {
            "average_score": (
                self.db.query(func.avg(ContributionScore.score)).scalar() or 0
            ),
            "max_score": self.db.query(func.max(ContributionScore.score)).scalar(),
            "min_score": self.db.query(func.min(ContributionScore.score)).scalar(),
            "latest_calculation": (
                self.db.query(func.max(ContributionScore.calculated_at)).scalar()
            ),
        }

    # ==========================================================================
    # Contribution dashboard
    # ==========================================================================

    def get_contribution_dashboard(self) -> dict[str, Any]:
        """
        Aggregated contribution dashboard: counts, extremes, and a ranking
        built from each member's most recent ContributionScore.
        """
        latest_scores = (
            select(
                ContributionScore.member_tag,
                func.max(ContributionScore.calculated_at).label("latest_calculated_at"),
            )
            .group_by(ContributionScore.member_tag)
            .subquery()
        )

        rows = (
            self.db.query(
                Member.name,
                ContributionScore.score,
                ContributionScore.war_activity,
                ContributionScore.war_performance,
                ContributionScore.donations,
                ContributionScore.trophy_level,
                ContributionScore.activity,
                ContributionScore.consistency,
                ContributionScore.seniority,
            )
            .join(Member, Member.tag == ContributionScore.member_tag)
            .join(
                latest_scores,
                (ContributionScore.member_tag == latest_scores.c.member_tag)
                & (
                    ContributionScore.calculated_at
                    == latest_scores.c.latest_calculated_at
                ),
            )
            .order_by(ContributionScore.score.desc())
            .all()
        )

        ranking = [
            {
                "name": row.name,
                "score": row.score,
                "war_activity": row.war_activity,
                "war_performance": row.war_performance,
                "donations": row.donations,
                "trophy_level": row.trophy_level,
                "activity": row.activity,
                "consistency": row.consistency,
                "seniority": row.seniority,
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

    def get_kick_candidates(self, _days_threshold: int = 14) -> list[dict[str, Any]]:
        """
        Kick candidates from the rank-based recommendation system: members
        flagged with action == "kick" (2 consecutive races under the fame
        sanction threshold). _days_threshold is unused - kept for backward
        signature compatibility with callers passing an inactivity slider
        value; kicking is now driven by fame, not raw inactivity.
        """
        recommendations = self.get_promotion_recommendations()
        return [r for r in recommendations if r["action"] == "kick"]

    def get_promotion_recommendations(self) -> list[dict[str, Any]]:
        """
        Rank-based promotion/demotion/kick recommendations (v0.8.0).
        Delegates to ScoreService, which owns the decision logic.
        """
        score_service = ScoreService(self.db)
        return score_service.get_promotion_recommendations()

    def get_last_completed_race(self) -> RiverRace | None:
        """
        Returns the most recent completed RiverRace, or None if none exist."""
        score_service = ScoreService(self.db)
        return score_service.get_last_completed_race()

    # ==========================================================================
    # Clan health & activity (v0.6.0)
    # ==========================================================================

    def _get_average_trophy_gain(self, window_days: int) -> float:
        """
        Average trophy gain per member over the last `window_days`, comparing
        each member's earliest vs. latest snapshot within the window.

        Computed in Python rather than a SQL self-join: finding first/last
        snapshot per member that way is fragile, and clan-sized snapshot
        volumes make this cheap enough to do safely in memory.
        """
        window_start = get_time() - timedelta(days=window_days)

        rows = (
            self.db.query(Snapshot.member_tag, Snapshot.collected_at, Snapshot.trophies)
            .filter(Snapshot.collected_at >= window_start)
            .order_by(Snapshot.member_tag, Snapshot.collected_at)
            .all()
        )

        first_trophies: dict[str, int] = {}
        last_trophies: dict[str, int] = {}

        for member_tag, _collected_at, trophies in rows:
            if member_tag not in first_trophies:
                first_trophies[member_tag] = trophies
            last_trophies[member_tag] = trophies

        gains = [
            last_trophies[tag] - trophies for tag, trophies in first_trophies.items()
        ]
        return (sum(gains) / len(gains)) if gains else 0

    def _inactivity_penalty_score(self, inactive_count: int) -> float:
        """
        Step-function penalty based on inactive member count:
        0->100, 5->80, 10->60, 15->40, 20+->0
        """
        thresholds = [(0, 100), (5, 80), (10, 60), (15, 40), (20, 0)]
        score = 100
        for count_threshold, value in thresholds:
            if inactive_count >= count_threshold:
                score = value
        return score

    def get_clan_health_score(self) -> dict[str, Any]:
        """
        Composite Clan Health Score (0-100), weighted across 8 components.
        Leadership Depth is a fixed placeholder (100) pending defined
        thresholds. See v0.8.0 roadmap notes for the related Contribution
        Score design.
        """
        active_roster_count = (
            self.db.query(count(Member.id))
            .filter(Member.role.notin_(["left", "fired"]))
            .scalar()
            or 0
        )

        # --- 1. Activity (25%) ---
        recently_active_count = (
            self.db.query(count(Member.id))
            .filter(
                Member.role.notin_(["left", "fired"]),
                Member.last_seen.isnot(None),
                Member.last_seen >= get_time() - timedelta(days=INACTIVE_DAYS),
            )
            .scalar()
            or 0
        )
        activity_score = (
            (recently_active_count / active_roster_count) * 100
            if active_roster_count
            else 0
        )

        # --- 2 & 3. War Participation (20%) & War Efficiency (15%) ---
        last_race = self.get_last_completed_race()

        if last_race:
            participants_count = (
                self.db.query(count(func.distinct(WarParticipation.member_tag)))
                .filter(WarParticipation.river_race_id == last_race.id)
                .scalar()
                or 0
            )
            avg_fame = (
                self.db.query(func.avg(WarParticipation.fame))
                .filter(WarParticipation.river_race_id == last_race.id)
                .scalar()
                or 0
            )
            war_participation_score = (
                (participants_count / active_roster_count) * 100
                if active_roster_count
                else 0
            )
            war_efficiency_score = (avg_fame / EXPECTED_FAME_PER_PLAYER) * 100
        else:
            war_participation_score = 0
            war_efficiency_score = 0

        # --- 4. Donations (10%) ---
        avg_donations = (
            self.db.query(func.avg(Member.donations))
            .filter(Member.role.notin_(["left", "fired"]))
            .scalar()
            or 0
        )
        donations_score = (avg_donations / DONATION_TARGET) * 100

        # --- 5. Retention (10%) ---
        window_center = get_time() - timedelta(days=RETENTION_WINDOW_DAYS)
        window_start = window_center - timedelta(days=RETENTION_WINDOW_TOLERANCE_DAYS)
        window_end = window_center + timedelta(days=RETENTION_WINDOW_TOLERANCE_DAYS)

        members_last_month_count = (
            self.db.query(count(func.distinct(Snapshot.member_tag)))
            .filter(
                Snapshot.collected_at >= window_start,
                Snapshot.collected_at <= window_end,
            )
            .scalar()
            or 0
        )
        members_remaining_count = (
            self.db.query(count(func.distinct(Snapshot.member_tag)))
            .join(Member, Member.tag == Snapshot.member_tag)
            .filter(
                Snapshot.collected_at >= window_start,
                Snapshot.collected_at <= window_end,
                Member.role.notin_(["left", "fired"]),
            )
            .scalar()
            or 0
        )
        retention_score = (
            (members_remaining_count / members_last_month_count) * 100
            if members_last_month_count
            else 100  # no data from ~30 days ago yet -> can't measure churn, assume full retention
        )

        # --- 6. Growth (10%) ---
        avg_gain = self._get_average_trophy_gain(GROWTH_WINDOW_DAYS)
        growth_score = (avg_gain / GROWTH_TARGET_TROPHIES) * 100

        # --- 7. Leadership Depth (5%) — placeholder ---
        # TODO: define exact thresholds/scoring for leader/coLeader/elder counts.
        leadership_score = 100

        # --- 8. Inactivity Penalty (5%) ---
        member_service = MemberService(self.db, self.api_clash)
        inactive_count = len(member_service.get_inactive_members(VERY_INACTIVE_DAYS))
        inactivity_score = self._inactivity_penalty_score(inactive_count)

        components = {
            "activity": activity_score,
            "war_participation": war_participation_score,
            "war_efficiency": war_efficiency_score,
            "donations": donations_score,
            "retention": retention_score,
            "growth": growth_score,
            "leadership": leadership_score,
            "inactivity": inactivity_score,
        }
        # Clamp every component to [0, 100] so the weighted sum stays bounded
        components = {k: min(100, max(0, v)) for k, v in components.items()}

        weights = CLAN_HEALTH_WEIGHTS

        final_score = sum(components[key] * weight for key, weight in weights.items())

        return {
            "final_score": round(final_score, 1),
            "components": {key: round(value, 1) for key, value in components.items()},
        }

    def get_inactivity_ranking(
        self,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Ranks active members by inactivity (days since last seen), most
        inactive first.
        """
        members = (
            self.db.query(Member.tag, Member.name, Member.last_seen)
            .filter(Member.role.notin_(["left", "fired"]))
            .all()
        )

        now = get_time()

        ranking = []
        for tag, name, last_seen in members:
            days_since = (now - last_seen).days if last_seen else None

            if days_since > 0:
                ranking.append(
                    {
                        "tag": tag,
                        "name": name,
                        "days_since_last_seen": days_since,
                        "activity_score": activity_score_from_days(days_since),
                    }
                )

        ranking.sort(
            key=lambda entry: (
                entry["days_since_last_seen"] is None,
                -(entry["days_since_last_seen"] or 0),
            )
        )

        return ranking[:limit] if limit else ranking

    def get_race_comparison(self, season_id: str) -> list[dict[str, Any]]:
        """
        Per-race totals/averages within a season, for side-by-side
        comparison. Participation rate is approximated using the CURRENT
        active member count, since historical roster size per race isn't
        tracked.
        """
        active_member_count = (
            self.db.query(count(Member.id))
            .filter(Member.role.notin_(["left", "fired"]))
            .scalar()
            or 0
        )

        rows = (
            self.db.query(
                RiverRace.section_index,
                RiverRace.created_date,
                func.coalesce(func.sum(WarParticipation.fame), 0).label("total_fame"),
                func.coalesce(func.avg(WarParticipation.fame), 0).label("avg_fame"),
                func.coalesce(func.sum(WarParticipation.repair_points), 0).label(
                    "total_repairs"
                ),
                func.coalesce(func.sum(WarParticipation.decks_used), 0).label(
                    "total_decks"
                ),
                func.coalesce(func.sum(WarParticipation.boat_attacks), 0).label(
                    "total_boat_attacks"
                ),
                count(func.distinct(WarParticipation.member_tag)).label("participants"),
            )
            .outerjoin(WarParticipation, WarParticipation.river_race_id == RiverRace.id)
            .filter(RiverRace.season_id == season_id)
            .group_by(RiverRace.id, RiverRace.section_index, RiverRace.created_date)
            .order_by(RiverRace.section_index)
            .all()
        )

        return [
            {
                "section_index": row.section_index,
                "created_date": row.created_date,
                "total_fame": row.total_fame,
                "avg_fame": round(row.avg_fame, 1),
                "total_repairs": row.total_repairs,
                "total_decks": row.total_decks,
                "total_boat_attacks": row.total_boat_attacks,
                "participants": row.participants,
                "participation_rate": (
                    round(row.participants / active_member_count * 100, 1)
                    if active_member_count
                    else 0
                ),
            }
            for row in rows
        ]

    def get_current_race_status(self) -> dict[str, Any] | None:
        """
        Live view of the currently in-progress river race: who among active
        members has attacked so far vs. who hasn't. Returns None if there's
        no in-progress race.
        """
        current_race = (
            self.db.query(RiverRace)
            .filter(RiverRace.is_completed.is_(False))
            .order_by(RiverRace.created_date.desc())
            .first()
        )

        if not current_race:
            return None

        active_members = (
            self.db.query(Member).filter(Member.role.notin_(["left", "fired"])).all()
        )

        participated_tags = {
            row.member_tag
            for row in (
                self.db.query(WarParticipation.member_tag)
                .filter(WarParticipation.river_race_id == current_race.id)
                .all()
            )
        }

        participated = [
            {"tag": m.tag, "name": m.name}
            for m in active_members
            if m.tag in participated_tags
        ]
        not_participated = [
            {"tag": m.tag, "name": m.name}
            for m in active_members
            if m.tag not in participated_tags
        ]

        return {
            "season_id": current_race.season_id,
            "section_index": current_race.section_index,
            "created_date": current_race.created_date,
            "participated_count": len(participated),
            "not_participated_count": len(not_participated),
            "participated": participated,
            "not_participated": not_participated,
        }

    # ==========================================================================
    # War dashboard
    # ==========================================================================

    def _get_efficiency(
        self,
        fame: int | float,
        decks_used: int,
        number_of_races: int,
    ) -> float:
        """
        Calculates war efficiency: fame performance relative to deck
        attendance, independent of total volume. Capped at 100% to handle
        small-sample anomalies (e.g. a single lucky duel win from very few
        decks used) - same principle as WAR_PERFORMANCE_SUBMETRIC_CAP and
        MIN_RACES_FOR_CONSISTENCY elsewhere in the scoring system.

        Formula:
            Fame Efficiency = fame / max possible fame
            Attendance = decks_used / max available decks
            Efficiency = min(100, (Fame Efficiency / Attendance) * 100)
        """
        max_fame = number_of_races * MAX_FAME_PER_RACE
        max_decks = number_of_races * MAX_DECKS_PER_RACE

        if not decks_used or not max_fame or not max_decks:
            return 0.0

        fame_efficiency = fame / max_fame
        attendance = decks_used / max_decks

        raw_efficiency = (fame_efficiency / attendance) * 100

        return min(round(raw_efficiency, 1), 100.0)

    def get_war_player_ranking(
        self, season_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Player performance ranking scoped to a single war season, by fame.
        Includes a fame-per-deck 'efficiency' figure for comparing quality
        of play independent of total participation volume.
        """
        race_ids = select(RiverRace.id).where(RiverRace.season_id == season_id)
        number_of_races = (
            self.db.query(count(RiverRace.id))
            .filter(RiverRace.season_id == season_id)
            .scalar()
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
                "efficiency": self._get_efficiency(
                    row.fame, row.decks, number_of_races
                ),
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
                count(func.distinct(WarParticipation.member_tag)).label("participants"),
            )
            .outerjoin(WarParticipation, WarParticipation.river_race_id == RiverRace.id)
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

        number_of_races_query = self.db.query(count(RiverRace.id))
        if season_id is not None:
            number_of_races_query = number_of_races_query.filter(
                RiverRace.season_id == season_id
            )
        number_of_races = number_of_races_query.scalar()

        query = self.db.query(
            func.coalesce(func.sum(WarParticipation.fame), 0).label("fame"),
            func.coalesce(func.sum(WarParticipation.repair_points), 0).label(
                "repair_points"
            ),
            func.coalesce(func.sum(WarParticipation.boat_attacks), 0).label(
                "boat_attacks"
            ),
            func.coalesce(func.sum(WarParticipation.decks_used), 0).label("decks_used"),
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
            "efficiency": self._get_efficiency(
                row.fame, row.decks_used, number_of_races
            ),
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

    def get_top_members_by_contribution_score(self, limit: int = 10) -> list[Member]:
        """
        Top members ordered by contribution score.
        """
        return (
            self.db.query(Member)
            .filter(Member.contribution_score.isnot(None))
            .order_by(Member.contribution_score.desc())
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

        race_ids = select(RiverRace.id).where(RiverRace.season_id == season_id)

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
