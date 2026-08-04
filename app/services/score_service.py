"""
================================================================================
Filename: score_service.py
Description: Service for calculating contribution scores and promotion/
    demotion/kick recommendations for members.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-07-13
Version: 0.3.0
Python Version: 3.12
Dependencies: sqlalchemy, app.database.models, app.core.constants
================================================================================

Contribution Score (v0.8.0):
    - War Activity: 30%     (participated / all-time completed races)
    - War Performance: 20%  (fame/decks/repairs/boats vs clan avg, last
                              RECENT_RACES_WINDOW races, each sub-metric
                              capped, weighted 40/30/20/10)
    - Donations: 15%        (30-day snapshot average / DONATION_TARGET)
    - Trophy Level: 10%     (trophies / clan 95th percentile trophies)
    - Activity: 10%         (bucketed days-since-last-seen score)
    - Consistency: 10%      (100 - coefficient of variation of fame over
                              the last RECENT_RACES_WINDOW races)
    - Seniority: 5%         (months in clan / SENIORITY_MONTHS_CAP)

Promotion/demotion recommendations are rank-based on the last completed
river race's fame, NOT the Contribution Score - the score is used to spot
patterns, but rank position drives the recommendation. This is a
READ-ONLY recommendation system: the public Clash Royale API can't write
role changes or kick members, so nothing here mutates Member.role.
"""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.logger import logger
from app.core.constants import (
    WAR_ACTIVITY_WEIGHT,
    WAR_PERFORMANCE_WEIGHT,
    CONTRIBUTION_DONATIONS_WEIGHT,
    CONTRIBUTION_TROPHY_WEIGHT,
    CONTRIBUTION_ACTIVITY_WEIGHT,
    CONSISTENCY_WEIGHT,
    SENIORITY_WEIGHT,
    WAR_PERFORMANCE_FAME_WEIGHT,
    WAR_PERFORMANCE_DECKS_WEIGHT,
    WAR_PERFORMANCE_REPAIRS_WEIGHT,
    WAR_PERFORMANCE_BOATS_WEIGHT,
    WAR_PERFORMANCE_SUBMETRIC_CAP,
    RECENT_RACES_WINDOW,
    DONATIONS_AVERAGE_WINDOW_DAYS,
    DONATION_TARGET,
    MIN_RACES_FOR_CONSISTENCY,
    SENIORITY_DAYS_CAP,
    TROPHY_PERCENTILE,
    SANCTION_FAME_THRESHOLD,
    PROMOTION_BAND_TOP,
    PROMOTION_BAND_ELDER,
    PROMOTION_BAND_DEMOTE_COLEADER,
)
from app.core.utils import get_time, count, activity_score_from_days
from app.database.models import (
    Member,
    RiverRace,
    WarParticipation,
    ContributionScore,
    Snapshot,
)

_ROLE_ORDER = ["member", "elder", "coLeader", "leader"]


class ScoreService:
    """
    Service for calculating contribution scores and generating rank-based
    promotion/demotion/kick recommendations.
    """

    def __init__(self, db_session: Session):
        self.db = db_session

    # ==========================================================================
    # Contribution Score components
    # ==========================================================================

    def _get_recent_race_ids(self) -> list[int]:
        """Last RECENT_RACES_WINDOW completed races, most recent first."""
        races = (
            self.db.query(RiverRace.id)
            .filter(RiverRace.is_completed.is_(True))
            .order_by(RiverRace.created_date.desc())
            .limit(RECENT_RACES_WINDOW)
            .all()
        )
        return [r.id for r in races]

    def _war_activity_score(self, member_tag: str) -> float:
        """
        Attacked races / races the member has a participation record for
        at all. A WarParticipation row's existence signals they were a
        clan member for that race (the Clash Royale API includes 0-fame
        entries for members who didn't attack) - its absence means they
        weren't in the clan for that race, so it's excluded rather than
        penalized.
        """
        available_races = (
            self.db.query(count(func.distinct(WarParticipation.river_race_id)))
            .join(RiverRace, RiverRace.id == WarParticipation.river_race_id)
            .filter(
                WarParticipation.member_tag == member_tag,
                RiverRace.is_completed.is_(True),
            )
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
                WarParticipation.decks_used > 0,
            )
            .scalar()
            or 0
        )

        return min(100, (participated_races / available_races) * 100)

    def _normalized_metric(
        self, member_tag: str, recent_race_ids: list[int], column
    ) -> float:
        """Member's average of `column` vs clan average, over recent_race_ids,
        capped. Excludes races where decks_used == 0 - a member present but
        not attacking has no performance to measure, so it shouldn't drag
        down (or inflate) either average."""
        member_avg = (
            self.db.query(func.avg(column))
            .filter(
                WarParticipation.member_tag == member_tag,
                WarParticipation.river_race_id.in_(recent_race_ids),
                WarParticipation.decks_used > 0,
            )
            .scalar()
        )
        if not member_avg:
            return 0

        clan_avg = (
            self.db.query(func.avg(column))
            .filter(
                WarParticipation.river_race_id.in_(recent_race_ids),
                WarParticipation.decks_used > 0,
            )
            .scalar()
            or 0
        )
        if not clan_avg:
            return 0

        return min(WAR_PERFORMANCE_SUBMETRIC_CAP, (member_avg / clan_avg) * 100)

    def _war_performance_score(
        self, member_tag: str, recent_race_ids: list[int]
    ) -> float:
        """40% fame + 30% decks + 20% repairs + 10% boats, each vs clan avg."""
        if not recent_race_ids:
            return 0

        fame_score = self._normalized_metric(
            member_tag, recent_race_ids, WarParticipation.fame
        )
        decks_score = self._normalized_metric(
            member_tag, recent_race_ids, WarParticipation.decks_used
        )
        repairs_score = self._normalized_metric(
            member_tag, recent_race_ids, WarParticipation.repair_points
        )
        boats_score = self._normalized_metric(
            member_tag, recent_race_ids, WarParticipation.boat_attacks
        )

        composite = (
            fame_score * WAR_PERFORMANCE_FAME_WEIGHT
            + decks_score * WAR_PERFORMANCE_DECKS_WEIGHT
            + repairs_score * WAR_PERFORMANCE_REPAIRS_WEIGHT
            + boats_score * WAR_PERFORMANCE_BOATS_WEIGHT
        )
        return min(100, composite)

    def _donations_score(self, member: Member) -> float:
        """30-day snapshot average donations / DONATION_TARGET x 100."""
        window_start = get_time() - timedelta(days=DONATIONS_AVERAGE_WINDOW_DAYS)

        avg_donations = (
            self.db.query(func.avg(Snapshot.donations))
            .filter(
                Snapshot.member_tag == member.tag,
                Snapshot.collected_at >= window_start,
            )
            .scalar()
        )

        if avg_donations is None:
            # No snapshot history in the window yet - fall back to current donations
            avg_donations = member.donations

        return min(100, (avg_donations / DONATION_TARGET) * 100)

    def _trophy_level_score(self, member: Member) -> float:
        """Trophies relative to the clan's TROPHY_PERCENTILE (computed in Python -
        percentile_cont is Postgres-only, this works identically on SQLite too)."""
        all_trophies = sorted(
            t
            for (t,) in self.db.query(Member.trophies)
            .filter(Member.role.notin_(["left", "fired"]))
            .all()
        )

        if not all_trophies:
            return 0

        percentile_index = min(
            len(all_trophies) - 1,
            int(len(all_trophies) * (TROPHY_PERCENTILE / 100)),
        )
        percentile_trophies = all_trophies[percentile_index]

        if not percentile_trophies:
            return 0

        return min(100, (member.trophies / percentile_trophies) * 100)

    def _activity_component_score(self, member: Member) -> float:
        days_since = (get_time() - member.last_seen).days if member.last_seen else None
        return activity_score_from_days(days_since)

    def _effective_join_date(self, member: Member) -> datetime | None:
        """
        Best-known date this member has been around, correcting for
        clan_joined_at potentially being stamped later than reality (e.g. a
        historical war-log backfill can create a Member row - and stamp
        clan_joined_at "now" - well after their actual first appearance).
        Uses whichever is earlier: clan_joined_at, or their first known
        completed-race participation.
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

    def _raw_consistency_score(
        self, member_tag: str, recent_race_ids: list[int]
    ) -> float | None:
        """
        100 - coefficient of variation of fame, over the member's actual
        participation records within recent_race_ids. No padding: a race
        with no row means they weren't a clan member for it (excluded); a
        race with a 0-fame row means they were present but skipped
        (counted - that's exactly the sporadic behavior this component
        should catch). Returns None if fewer than MIN_RACES_FOR_CONSISTENCY
        eligible races exist.
        """
        if not recent_race_ids:
            return None

        fames = [
            row.fame
            for row in self.db.query(WarParticipation.fame)
            .filter(
                WarParticipation.member_tag == member_tag,
                WarParticipation.river_race_id.in_(recent_race_ids),
            )
            .all()
        ]

        if len(fames) < MIN_RACES_FOR_CONSISTENCY:
            return None

        mean_fame = sum(fames) / len(fames)
        if mean_fame == 0:
            return 0

        variance = sum((f - mean_fame) ** 2 for f in fames) / len(fames)
        stddev = variance**0.5

        consistency = 100 - (stddev / mean_fame * 100)
        return min(100, max(0, consistency))

    def _clan_average_consistency(self, recent_race_ids: list[int]) -> float:
        """
        Mean raw consistency across active members who qualify (>=
        MIN_RACES_FOR_CONSISTENCY eligible races). Used as the fallback for
        members who don't have enough history yet.
        """
        active_members = (
            self.db.query(Member).filter(Member.role.notin_(["left", "fired"])).all()
        )

        qualifying_scores: list[float] = []
        for candidate in active_members:
            raw_score = self._raw_consistency_score(candidate.tag, recent_race_ids)
            if raw_score is not None:
                qualifying_scores.append(raw_score)

        if not qualifying_scores:
            return 0

        return sum(qualifying_scores) / len(qualifying_scores)

    def _consistency_score(self, member_tag: str, recent_race_ids: list[int]) -> float:
        """
        Member's raw consistency score, or the clan average (among
        qualifying members) if they don't have MIN_RACES_FOR_CONSISTENCY
        eligible races themselves yet.
        """
        raw_score = self._raw_consistency_score(member_tag, recent_race_ids)
        if raw_score is not None:
            return raw_score

        return self._clan_average_consistency(recent_race_ids)

    def _seniority_score(self, member: Member) -> float:
        return min(100, (member.days_in_clan / SENIORITY_DAYS_CAP) * 100)

    # ==========================================================================
    # Public: score calculation
    # ==========================================================================

    def calculate_contribution_score(self, member_tag: str) -> ContributionScore | None:
        """
        Calculate and persist a contribution score for one member.

        Creates a new ContributionScore row (preserving history) and updates
        Member.contribution_score / contribution_score_updated_at with the
        latest value.
        """
        member: Member | None = self.db.query(Member).filter_by(tag=member_tag).first()
        if not member:
            logger.warning("Cannot calculate score: member %s not found.", member_tag)
            return None

        recent_race_ids = self._get_recent_race_ids()

        war_activity = self._war_activity_score(member_tag)
        war_performance = self._war_performance_score(member_tag, recent_race_ids)
        donations = self._donations_score(member)
        trophy_level = self._trophy_level_score(member)
        activity = self._activity_component_score(member)
        consistency = self._consistency_score(member.tag, recent_race_ids)
        seniority = self._seniority_score(member)

        final_score = (
            war_activity * WAR_ACTIVITY_WEIGHT
            + war_performance * WAR_PERFORMANCE_WEIGHT
            + donations * CONTRIBUTION_DONATIONS_WEIGHT
            + trophy_level * CONTRIBUTION_TROPHY_WEIGHT
            + activity * CONTRIBUTION_ACTIVITY_WEIGHT
            + consistency * CONSISTENCY_WEIGHT
            + seniority * SENIORITY_WEIGHT
        )

        now: datetime = get_time()

        score = ContributionScore(
            member=member,
            score=final_score,
            war_activity=war_activity,
            war_performance=war_performance,
            donations=donations,
            trophy_level=trophy_level,
            activity=activity,
            consistency=consistency,
            seniority=seniority,
            calculated_at=now,
        )
        self.db.add(score)

        member.contribution_score = final_score
        member.contribution_score_updated_at = now

        self.db.commit()

        logger.info(
            "Calculated contribution score for %s: %.2f", member_tag, final_score
        )

        return score

    def calculate_all_scores(self) -> list[ContributionScore]:
        """
        Calculate and persist scores for every active member.
        """
        active_members = (
            self.db.query(Member).filter(Member.role.notin_(["left", "fired"])).all()
        )

        scores: list[ContributionScore] = []
        for member in active_members:
            score = self.calculate_contribution_score(member.tag)
            if score:
                scores.append(score)

        logger.info("Calculated contribution scores for %d members.", len(scores))
        return scores

    # ==========================================================================
    # Promotion / demotion / kick recommendations
    # ==========================================================================

    def _role_rank(self, role: str) -> int:
        return _ROLE_ORDER.index(role) if role in _ROLE_ORDER else -1

    def _one_step_up(self, role: str) -> str:
        if role == "member":
            return "elder"
        if role == "elder":
            return "coLeader"
        return role  # coLeader stays coLeader (can't reach leader this way)

    def _one_step_down(self, role: str) -> str:
        if role == "coLeader":
            return "elder"
        if role == "elder":
            return "member"
        return role  # member has no lower role

    def _role_for_rank_band(self, current_role: str, rank: int) -> str:
        if rank <= PROMOTION_BAND_TOP:
            return self._one_step_up(current_role)

        if rank <= PROMOTION_BAND_ELDER:
            if current_role == "member":
                return "elder"
            return current_role  # elder/coLeader stay as-is

        if rank <= PROMOTION_BAND_DEMOTE_COLEADER:
            if current_role == "coLeader":
                return "elder"
            return current_role  # member/elder stay as-is

        return "member"  # rank beyond PROMOTION_BAND_DEMOTE_COLEADER

    def _fame_in_race(self, member_tag: str, race_id: int | None) -> int:
        if race_id is None:
            return 0
        fame = (
            self.db.query(func.sum(WarParticipation.fame))
            .filter(
                WarParticipation.member_tag == member_tag,
                WarParticipation.river_race_id == race_id,
            )
            .scalar()
        )
        return fame or 0

    def get_promotion_recommendations(self) -> list[dict[str, Any]]:
        """
        Rank-based promotion/demotion/kick recommendations from the last
        completed river race, per the v0.8.0 rules:
            - Rank 1-15: promoted one step (coLeader stays coLeader)
            - Rank 16-25: promoted to elder if below (coLeader stays coLeader)
            - Rank 26-35: demoted one step only if coLeader
            - Rank 36-50+: demoted to member
            - Fame < SANCTION_FAME_THRESHOLD this race: demoted one step,
              overriding the band outcome
            - Fame < SANCTION_FAME_THRESHOLD 2 consecutive races: flagged
              for kick
        Leader is exempt throughout. Members who joined after the last
        completed race are excluded from ranking/sanctions entirely (not
        just penalized) - they weren't in the clan to participate, so 0
        fame isn't a real signal about them. Same logic applies to the
        previous race when checking for a 2-consecutive-race sanction: a
        member who joined between the two races can't be penalized for a
        race they weren't present for.

        READ-ONLY - does not modify Member.role; the public API can't
        write role changes, so this produces recommendations for manual
        action in-game.

        Returns:
            list[dict]: one entry per active member:
                {tag, name, current_role, rank, fame, recommended_role,
                 action, reason}
                action is one of: "promote", "demote", "kick", "no_change"
                rank is None for members excluded as not-yet-eligible.
        """
        last_race = (
            self.db.query(RiverRace)
            .filter(RiverRace.is_completed.is_(True))
            .order_by(RiverRace.created_date.desc())
            .first()
        )

        if not last_race:
            return []

        second_last_race = (
            self.db.query(RiverRace)
            .filter(
                RiverRace.is_completed.is_(True),
                RiverRace.id != last_race.id,
            )
            .order_by(RiverRace.created_date.desc())
            .first()
        )

        active_members = (
            self.db.query(Member).filter(Member.role.notin_(["left", "fired"])).all()
        )

        eligible_entries = []
        recommendations: list[dict[str, Any]] = []

        for member in active_members:
            was_present_in_last_race = (
                self.db.query(WarParticipation.id)
                .filter(
                    WarParticipation.member_tag == member.tag,
                    WarParticipation.river_race_id == last_race.id,
                )
                .first()
                is not None
            )

            if not was_present_in_last_race:
                recommendations.append(
                    {
                        "tag": member.tag,
                        "name": member.name,
                        "current_role": member.role,
                        "rank": None,
                        "fame": 0,
                        "recommended_role": member.role,
                        "action": "no_change",
                        "reason": "Not in the clan for the last completed race - not yet eligible.",
                    }
                )
                continue

            was_present_for_previous_race = second_last_race is not None and (
                self.db.query(WarParticipation.id)
                .filter(
                    WarParticipation.member_tag == member.tag,
                    WarParticipation.river_race_id == second_last_race.id,
                )
                .first()
                is not None
            )

            eligible_entries.append(
                {
                    "member": member,
                    "fame": self._fame_in_race(member.tag, last_race.id),
                    "previous_fame": self._fame_in_race(
                        member.tag,
                        second_last_race.id if was_present_for_previous_race else None,
                    ),
                    "was_present_for_previous_race": was_present_for_previous_race,
                }
            )

        ranked = sorted(
            eligible_entries, key=lambda entry: (-entry["fame"], entry["member"].tag)
        )

        for rank, entry in enumerate(ranked, start=1):
            member = entry["member"]
            fame = entry["fame"]
            previous_fame = entry["previous_fame"]
            current_role = member.role

            if current_role == "leader":
                recommendations.append(
                    {
                        "tag": member.tag,
                        "join_date": member.clan_joined_at,
                        "name": member.name,
                        "current_role": current_role,
                        "rank": rank,
                        "fame": fame,
                        "recommended_role": current_role,
                        "action": "no_change",
                        "reason": "Leader is exempt from automated recommendations.",
                    }
                )
                continue

            sanctioned_this_race = fame < SANCTION_FAME_THRESHOLD
            sanctioned_last_race = (
                entry["was_present_for_previous_race"]
                and previous_fame < SANCTION_FAME_THRESHOLD
            )

            if sanctioned_this_race and sanctioned_last_race:
                recommendations.append(
                    {
                        "tag": member.tag,
                        "join_date": member.clan_joined_at,
                        "name": member.name,
                        "current_role": current_role,
                        "rank": rank,
                        "fame": fame,
                        "recommended_role": current_role,
                        "action": "kick",
                        "reason": (
                            f"Scored under {SANCTION_FAME_THRESHOLD} fame in the last "
                            "2 consecutive races."
                        ),
                    }
                )
                continue

            if sanctioned_this_race:
                recommended_role = self._one_step_down(current_role)
                recommendations.append(
                    {
                        "tag": member.tag,
                        "join_date": member.clan_joined_at,
                        "name": member.name,
                        "current_role": current_role,
                        "rank": rank,
                        "fame": fame,
                        "recommended_role": recommended_role,
                        "action": (
                            "demote"
                            if recommended_role != current_role
                            else "no_change"
                        ),
                        "reason": f"Scored under {SANCTION_FAME_THRESHOLD} fame in the last race.",
                    }
                )
                continue

            recommended_role = self._role_for_rank_band(current_role, rank)
            if recommended_role == current_role:
                action = "no_change"
            elif self._role_rank(recommended_role) > self._role_rank(current_role):
                action = "promote"
            else:
                action = "demote"

            recommendations.append(
                {
                    "tag": member.tag,
                    "join_date": member.clan_joined_at,
                    "name": member.name,
                    "current_role": current_role,
                    "rank": rank,
                    "fame": fame,
                    "recommended_role": recommended_role,
                    "action": action,
                    "reason": f"Ranked #{rank} in the last race.",
                }
            )

        return recommendations
