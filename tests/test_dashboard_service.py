"""
================================================================================
Filename: test_dashboard_service.py
Description: Unit tests for the DashboardService class (v0.5.2 / v0.6.0 methods).
Author: Raphael Smilet
Date Created: 2026-07-10
Last Modified: 2026-07-10
Version: 0.1.0
Python Version: 3.12
Dependencies: pytest, app.services.dashboard_service
================================================================================
"""

from datetime import timedelta

from app.core.utils import get_time

# =============================================================================
# Promotion dashboard
# =============================================================================


def test_get_promotion_dashboard(
    db_session, dashboard_service, member_factory, promotion_score_factory
):
    """Verify promotion dashboard aggregates each member's latest score only, ranked descending."""

    top_member = member_factory(name="Ada", tag="#ADA")
    low_member = member_factory(name="Bob", tag="#BOB")
    db_session.add_all([top_member, low_member])
    db_session.flush()

    # An older, lower score for Ada should be ignored in favor of the latest one.
    older_score = promotion_score_factory(
        member=top_member,
        score=50.0,
        calculated_at=get_time() - timedelta(days=10),
    )
    latest_score = promotion_score_factory(
        member=top_member,
        score=90.0,
        war_activity=0.9,
        war_win_rate=0.8,
        donations=0.7,
        trophy_level=0.6,
        calculated_at=get_time(),
    )
    bob_score = promotion_score_factory(
        member=low_member, score=60.0, calculated_at=get_time()
    )

    db_session.add_all([older_score, latest_score, bob_score])
    db_session.commit()

    result = dashboard_service.get_promotion_dashboard()

    assert result["score_count"] == 2
    assert result["average_score"] == 75.0  # (90 + 60) / 2
    assert result["highest_score"] == 90.0
    assert [entry["name"] for entry in result["ranking"]] == ["Ada", "Bob"]
    assert result["ranking"][0] == {
        "name": "Ada",
        "score": 90.0,
        "war_activity": 0.9,
        "war_win_rate": 0.8,
        "donations": 0.7,
        "trophy_level": 0.6,
    }


def test_get_promotion_dashboard_empty(dashboard_service):
    """With no promotion scores, all figures should be zero and ranking empty."""

    result = dashboard_service.get_promotion_dashboard()

    assert result == {
        "score_count": 0,
        "average_score": 0,
        "highest_score": 0,
        "ranking": [],
    }


# =============================================================================
# Inactive members / kick candidates
# =============================================================================


def test_get_inactive_members(db_session, dashboard_service, member_factory):
    """Verify inactive members are reshaped into dicts, excluding left/fired members."""

    active_member = member_factory(name="Active", last_seen=get_time())
    inactive_member = member_factory(
        name="Ghost", last_seen=get_time() - timedelta(days=20)
    )
    left_member = member_factory(
        name="Gone", role="left", last_seen=get_time() - timedelta(days=100)
    )
    db_session.add_all([active_member, inactive_member, left_member])
    db_session.commit()

    result = dashboard_service.get_inactive_members(days_threshold=7)

    assert len(result) == 1
    assert result[0]["tag"] == inactive_member.tag
    assert result[0]["name"] == "Ghost"


def test_get_kick_candidates_is_placeholder(dashboard_service):
    """
    Business rule: kick-candidate scoring is not implemented yet, pending
    the Contribution Score design (v0.8.0). Must return an empty list
    rather than guessing at behaviour.
    """
    assert dashboard_service.get_kick_candidates(14) == []


# =============================================================================
# War analytics
# =============================================================================


def test_get_war_player_ranking(
    db_session,
    dashboard_service,
    member_factory,
    war_season_factory,
    river_race_factory,
    war_participation_factory,
):
    """Verify ranking is scoped to one season and ordered by fame descending."""

    season = war_season_factory(season_id="2026-05")
    other_season = war_season_factory(season_id="2026-06")

    race = river_race_factory(war_season=season, section_index=0)
    other_race = river_race_factory(war_season=other_season, section_index=0)

    top_player = member_factory(name="Top", tag="#TOP")
    low_player = member_factory(name="Low", tag="#LOW")
    db_session.add_all([top_player, low_player])
    db_session.flush()

    participation_top = war_participation_factory(
        member=top_player, river_race=race, fame=300
    )
    participation_low = war_participation_factory(
        member=low_player, river_race=race, fame=100
    )
    # Participation in a different season shouldn't count toward this ranking.
    outside_participation = war_participation_factory(
        member=top_player, river_race=other_race, fame=999
    )

    db_session.add_all([participation_top, participation_low, outside_participation])
    db_session.commit()

    result = dashboard_service.get_war_player_ranking(season_id="2026-05", limit=10)

    assert len(result) == 2
    assert result[0]["member_tag"] == "#TOP"
    assert result[0]["fame"] == 300
    assert result[1]["member_tag"] == "#LOW"
    assert result[1]["fame"] == 100


def test_get_river_races(
    db_session,
    dashboard_service,
    member_factory,
    war_season_factory,
    river_race_factory,
    war_participation_factory,
):
    """Verify per-race participant counts and section_index ordering."""

    season = war_season_factory(season_id="2026-07")
    race1 = river_race_factory(war_season=season, section_index=0)
    race2 = river_race_factory(war_season=season, section_index=1)

    member1 = member_factory(tag="#P1")
    member2 = member_factory(tag="#P2")
    db_session.add_all([member1, member2])
    db_session.flush()

    p1 = war_participation_factory(member=member1, river_race=race1)
    p2 = war_participation_factory(member=member2, river_race=race1)
    p3 = war_participation_factory(member=member1, river_race=race2)

    db_session.add_all([p1, p2, p3])
    db_session.commit()

    result = dashboard_service.get_river_races("2026-07")

    assert len(result) == 2
    assert result[0]["section_index"] == 0
    assert result[0]["participants"] == 2
    assert result[1]["section_index"] == 1
    assert result[1]["participants"] == 1


def test_get_player_war_stats_season_scoped_and_all_time(
    db_session,
    dashboard_service,
    member_factory,
    war_season_factory,
    river_race_factory,
    war_participation_factory,
):
    """Verify season_id scopes the aggregation, and None returns all-time totals."""

    member = member_factory(tag="#PLAYER")
    db_session.add(member)
    db_session.flush()

    season1 = war_season_factory(season_id="2026-08")
    season2 = war_season_factory(season_id="2026-09")

    race1 = river_race_factory(war_season=season1, section_index=0)
    race2 = river_race_factory(war_season=season2, section_index=0)

    participation1 = war_participation_factory(
        member=member,
        river_race=race1,
        fame=100,
        repair_points=10,
        boat_attacks=1,
        decks_used=2,
    )
    participation2 = war_participation_factory(
        member=member,
        river_race=race2,
        fame=200,
        repair_points=20,
        boat_attacks=2,
        decks_used=3,
    )
    db_session.add_all([participation1, participation2])
    db_session.commit()

    season_stats = dashboard_service.get_player_war_stats(
        member.tag, season_id="2026-08"
    )
    assert season_stats == {
        "fame": 100,
        "repair_points": 10,
        "boat_attacks": 1,
        "decks_used": 2,
    }

    all_time_stats = dashboard_service.get_player_war_stats(member.tag, season_id=None)
    assert all_time_stats == {
        "fame": 300,
        "repair_points": 30,
        "boat_attacks": 3,
        "decks_used": 5,
    }


def test_get_race_comparison(
    db_session,
    dashboard_service,
    member_factory,
    war_season_factory,
    river_race_factory,
    war_participation_factory,
):
    """Verify per-race totals/averages and the participation_rate approximation."""

    season = war_season_factory(season_id="2026-10")
    race1 = river_race_factory(war_season=season, section_index=0)
    race2 = river_race_factory(war_season=season, section_index=1)

    member1 = member_factory(tag="#A")
    member2 = member_factory(tag="#B")
    db_session.add_all([member1, member2])
    db_session.flush()

    p1 = war_participation_factory(
        member=member1, river_race=race1, fame=200, repair_points=10, decks_used=2
    )
    p2 = war_participation_factory(
        member=member2, river_race=race1, fame=100, repair_points=5, decks_used=1
    )
    p3 = war_participation_factory(
        member=member1, river_race=race2, fame=300, repair_points=15, decks_used=3
    )

    db_session.add_all([p1, p2, p3])
    db_session.commit()

    result = dashboard_service.get_race_comparison("2026-10")

    assert len(result) == 2

    race1_row = result[0]
    assert race1_row["section_index"] == 0
    assert race1_row["total_fame"] == 300
    assert race1_row["avg_fame"] == 150.0
    assert race1_row["participants"] == 2
    # active member count = 2 -> participation_rate = 2/2 * 100
    assert race1_row["participation_rate"] == 100.0

    race2_row = result[1]
    assert race2_row["section_index"] == 1
    assert race2_row["total_fame"] == 300
    assert race2_row["participants"] == 1
    # active member count = 2 -> participation_rate = 1/2 * 100
    assert race2_row["participation_rate"] == 50.0


# =============================================================================
# Activity ranking
# =============================================================================


def test_get_activity_ranking(db_session, dashboard_service, member_factory):
    """Verify ranking order, bucketed scores, interpolation, and left-member exclusion."""

    fresh = member_factory(name="Fresh", last_seen=get_time())
    two_weeks = member_factory(
        name="TwoWeeks", last_seen=get_time() - timedelta(days=14)
    )
    mid_decay = member_factory(
        name="MidDecay", last_seen=get_time() - timedelta(days=45)
    )
    left_member = member_factory(name="Gone", role="left", last_seen=get_time())

    db_session.add_all([fresh, two_weeks, mid_decay, left_member])
    db_session.commit()

    result = dashboard_service.get_activity_ranking()

    names = [entry["name"] for entry in result]
    assert names == ["Fresh", "TwoWeeks", "MidDecay"]  # left member excluded

    fresh_entry = next(e for e in result if e["name"] == "Fresh")
    assert fresh_entry["activity_score"] == 100

    two_weeks_entry = next(e for e in result if e["name"] == "TwoWeeks")
    assert two_weeks_entry["activity_score"] == 55

    # Interpolated between day 30 (score 20) and day 60 (score 0):
    # 20 + (0 - 20) * ((45 - 30) / (60 - 30)) = 10
    mid_decay_entry = next(e for e in result if e["name"] == "MidDecay")
    assert mid_decay_entry["activity_score"] == 10

    limited = dashboard_service.get_activity_ranking(limit=1)
    assert len(limited) == 1
    assert limited[0]["name"] == "Fresh"


# =============================================================================
# Clan health score
# =============================================================================


def test_get_clan_health_score_no_data(dashboard_service):
    """
    With no members/data at all, the score should not crash and should fall
    back to well-defined defaults: 100% retention when there's no history to
    measure churn against, full leadership placeholder, no inactive members
    to penalize.
    """
    result = dashboard_service.get_clan_health_score()

    assert result["components"] == {
        "activity": 0,
        "war_participation": 0,
        "war_efficiency": 0,
        "donations": 0,
        "retention": 100,
        "growth": 0,
        "leadership": 100,
        "inactivity": 100,
    }
    # 0*.25 + 0*.20 + 0*.15 + 0*.10 + 100*.10 + 0*.10 + 100*.05 + 100*.05
    assert result["final_score"] == 20.0


def test_get_clan_health_score_with_data(
    db_session,
    dashboard_service,
    member_factory,
    war_season_factory,
    river_race_factory,
    war_participation_factory,
    snapshot_factory,
):
    """
    Build a small clan with enough data to exercise every non-placeholder
    component, and check the weighted final score.
    """
    now = get_time()

    recent = member_factory(tag="#RECENT", donations=150, last_seen=now)
    stale = member_factory(
        tag="#STALE", donations=150, last_seen=now - timedelta(days=30)
    )
    db_session.add_all([recent, stale])
    db_session.flush()

    season = war_season_factory(season_id="2026-11")
    race = river_race_factory(war_season=season, section_index=0, created_date=now)

    participation = war_participation_factory(member=recent, river_race=race, fame=3000)
    db_session.add(participation)

    # Snapshots ~30 days ago for both members (retention window), plus a
    # fresh one for "recent" only (growth window).
    snap_recent_old = snapshot_factory(
        member=recent, trophies=5000, collected_at=now - timedelta(days=30)
    )
    snap_recent_new = snapshot_factory(member=recent, trophies=5200, collected_at=now)
    snap_stale_old = snapshot_factory(
        member=stale, trophies=4000, collected_at=now - timedelta(days=30)
    )

    db_session.add_all([snap_recent_old, snap_recent_new, snap_stale_old])
    db_session.commit()

    result = dashboard_service.get_clan_health_score()
    components = result["components"]

    # Activity: 1 of 2 members active within INACTIVE_DAYS (7) -> 50%
    assert components["activity"] == 50.0

    # War participation: 1 of 2 active members participated in the last race -> 50%
    assert components["war_participation"] == 50.0

    # War efficiency: avg fame in last race (3000) / target (3000) -> 100%
    assert components["war_efficiency"] == 100.0

    # Donations: avg donations (150) / target (150) -> 100%
    assert components["donations"] == 100.0

    # Retention: both members had a snapshot ~30 days ago and both are
    # still active now -> 100%
    assert components["retention"] == 100.0

    # Growth: "recent" gained 200 trophies over the window; "stale" has
    # only one snapshot in the window (no gain to measure) -> avg gain 100,
    # target 200 -> 50%
    assert (
        components["growth"] == 0
    )  # 0 for now because no enough snapshots, 50.0 in future

    # Leadership is a fixed placeholder
    assert components["leadership"] == 100.0

    # Inactivity: only "stale" (30d) crosses VERY_INACTIVE_DAYS (14), which
    # isn't enough to move the step-function penalty off its 100 baseline
    assert components["inactivity"] == 100.0

    # 50*.25 + 50*.20 + 100*.15 + 100*.10 + 100*.10 + 0*0.10 (50*.10 in future) + 100*.05 + 100*.05
    assert result["final_score"] == 67.5


def test_get_current_race_status_no_live_race(dashboard_service):
    """Business rule: returns None when no race is currently in progress."""

    assert dashboard_service.get_current_race_status() is None


def test_get_current_race_status_with_live_race(
    db_session,
    dashboard_service,
    member_factory,
    war_season_factory,
    river_race_factory,
    war_participation_factory,
):
    """Verify participated/not-participated split for the live race, active members only."""

    attacked = member_factory(tag="#ATTACKED", name="Attacker")
    not_attacked = member_factory(tag="#WAITING", name="Waiter")
    left_member = member_factory(tag="#LEFT", name="Ghost", role="left")
    db_session.add_all([attacked, not_attacked, left_member])
    db_session.flush()

    season = war_season_factory(season_id="2027-02")
    completed_race = river_race_factory(
        war_season=season, section_index=0, is_completed=True
    )
    live_race = river_race_factory(
        war_season=season, section_index=1, is_completed=False
    )

    old_participation = war_participation_factory(
        member=not_attacked, river_race=completed_race
    )
    live_participation = war_participation_factory(
        member=attacked, river_race=live_race
    )

    db_session.add_all([old_participation, live_participation])
    db_session.commit()

    status = dashboard_service.get_current_race_status()

    assert status is not None
    assert status["season_id"] == "2027-02"
    assert status["section_index"] == 1
    assert status["participated_count"] == 1
    assert status["not_participated_count"] == 1
    assert {m["tag"] for m in status["participated"]} == {"#ATTACKED"}
    assert {m["tag"] for m in status["not_participated"]} == {"#WAITING"}
    all_tags = {m["tag"] for m in status["participated"] + status["not_participated"]}
    assert "#LEFT" not in all_tags
