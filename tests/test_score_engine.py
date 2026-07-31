"""
================================================================================
Filename: test_score_engine.py
Description: Unit tests for the ScoreService class (Contribution Score
    calculation and promotion recommendations).
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-07-16
Version: 0.3.0
Python Version: 3.12
Dependencies: pytest, app.services.score_service
================================================================================
"""

from datetime import timedelta
from pytest import approx
from app.core.utils import get_time
from app.database.models import ContributionScore

# =============================================================================
# calculate_contribution_score
# =============================================================================


def test_calculate_contribution_score_unknown_member(score_service):
    assert score_service.calculate_contribution_score("#UNKNOWN") is None


def test_calculate_contribution_score_no_data(
    db_session, score_service, member_factory
):
    """A brand new member with no war/donation/snapshot history scores 0 on
    every component except whatever floor values apply."""
    member = member_factory(tag="#NEW", trophies=1000, donations=0)
    db_session.add(member)
    db_session.commit()

    score = score_service.calculate_contribution_score("#NEW")

    assert score.war_activity == 0
    assert score.war_performance == 0
    assert score.seniority == 0  # no clan_joined_at set on this fixture member
    assert score.consistency == 0


def test_calculate_contribution_score_war_activity(
    db_session,
    score_service,
    member_factory,
    war_season_factory,
    river_race_factory,
    war_participation_factory,
):
    """War Activity = participated / all-time completed races x 100."""
    member = member_factory(tag="#ACTIVE")
    other = member_factory(tag="#OTHER")
    db_session.add_all([member, other])
    db_session.flush()

    season = war_season_factory(season_id="2027-03")
    race1 = river_race_factory(war_season=season, section_index=0, is_completed=True)
    race2 = river_race_factory(war_season=season, section_index=1, is_completed=True)

    participation1 = war_participation_factory(member=member, river_race=race1)
    # race2 only has the other member - "member" didn't participate
    participation2 = war_participation_factory(member=other, river_race=race2)

    db_session.add_all([participation1, participation2])
    db_session.commit()

    score = score_service.calculate_contribution_score("#ACTIVE")

    assert score.war_activity == 50.0  # 1 participated / 2 available


def test_calculate_contribution_score_excludes_incomplete_races(
    db_session,
    score_service,
    member_factory,
    war_season_factory,
    river_race_factory,
    war_participation_factory,
):
    """War Activity/Performance ignore in-progress races."""
    member = member_factory(tag="#LIVE")
    db_session.add(member)
    db_session.flush()

    season = war_season_factory(season_id="2027-04")
    completed_race = river_race_factory(
        war_season=season, section_index=0, is_completed=True
    )
    live_race = river_race_factory(
        war_season=season, section_index=1, is_completed=False
    )

    completed_participation = war_participation_factory(
        member=member,
        river_race=completed_race,
        fame=3600,
        decks_used=4,
        repair_points=10,
        boat_attacks=2,
    )
    live_participation = war_participation_factory(
        member=member, river_race=live_race, fame=0
    )

    db_session.add_all([completed_participation, live_participation])
    db_session.commit()

    score = score_service.calculate_contribution_score("#LIVE")

    assert score.war_activity == 100.0  # 1 completed participation / 1 completed race


def test_calculate_contribution_score_donations_uses_snapshot_average(
    db_session, score_service, member_factory, snapshot_factory
):
    """Donations = 30-day snapshot average, not the raw current value."""
    member = member_factory(
        tag="#DONOR", donations=999
    )  # current value should be ignored
    db_session.add(member)
    db_session.flush()

    now = get_time()
    snap1 = snapshot_factory(
        member=member, donations=100, collected_at=now - timedelta(days=20)
    )
    snap2 = snapshot_factory(
        member=member, donations=200, collected_at=now - timedelta(days=5)
    )

    db_session.add_all([snap1, snap2])
    db_session.commit()

    score = score_service.calculate_contribution_score("#DONOR")

    # avg(100, 200) = 150 -> 150 / DONATION_TARGET(150) x 100 = 100
    assert score.donations == 100.0


def test_calculate_contribution_score_donations_falls_back_without_snapshots(
    db_session, score_service, member_factory
):
    """With no snapshots in the window, fall back to the member's current donations."""
    member = member_factory(tag="#NOSNAP", donations=75)
    db_session.add(member)
    db_session.commit()

    score = score_service.calculate_contribution_score("#NOSNAP")

    assert score.donations == 50.0  # 75 / DONATION_TARGET(150) x 100


def test_calculate_contribution_score_trophy_percentile(
    db_session, score_service, member_factory
):
    """Trophy Level normalizes against the clan's 95th percentile, not the raw max."""
    members = [member_factory(tag=f"#T{i}", trophies=1000 * (i + 1)) for i in range(10)]
    db_session.add_all(members)
    db_session.commit()

    # highest member (10000 trophies) should score at or near 100
    top_score = score_service.calculate_contribution_score("#T9")
    assert top_score.trophy_level == 100.0  # capped

    # a mid-pack member should score below 100
    mid_score = score_service.calculate_contribution_score("#T4")
    assert 0 < mid_score.trophy_level < 100


def test_calculate_contribution_score_seniority(
    db_session, score_service, member_factory
):
    """Seniority = months in clan / SENIORITY_MONTHS_CAP x 100, 0 if clan_joined_at unset."""
    now = get_time()

    no_join_date = member_factory(tag="#NODATE")
    six_months = member_factory(tag="#SIXMO", clan_joined_at=now - timedelta(days=182))
    over_a_year = member_factory(
        tag="#OLDTIMER", clan_joined_at=now - timedelta(days=400)
    )

    db_session.add_all([no_join_date, six_months, over_a_year])
    db_session.commit()

    assert score_service.calculate_contribution_score("#NODATE").seniority == 0
    assert 45 < score_service.calculate_contribution_score("#SIXMO").seniority < 55
    assert (
        score_service.calculate_contribution_score("#OLDTIMER").seniority == 100.0
    )  # capped


def test_calculate_contribution_score_preserves_history(
    db_session, score_service, member_factory
):
    member = member_factory(tag="#HIST")
    db_session.add(member)
    db_session.commit()

    score_service.calculate_contribution_score("#HIST")
    score_service.calculate_contribution_score("#HIST")

    history = db_session.query(ContributionScore).filter_by(member_tag="#HIST").all()
    assert len(history) == 2


def test_calculate_all_scores_skips_left_members(
    db_session, score_service, member_factory
):
    active = member_factory(tag="#ACTIVE2", role="member")
    left = member_factory(tag="#LEFT2", role="left")
    db_session.add_all([active, left])
    db_session.commit()

    scores = score_service.calculate_all_scores()

    assert {s.member_tag for s in scores} == {"#ACTIVE2"}


# =============================================================================
# Promotion band mapping (direct unit tests on the pure rule-table logic)
# =============================================================================


def test_role_for_rank_band_top(score_service):
    assert score_service._role_for_rank_band("member", 1) == "elder"
    assert score_service._role_for_rank_band("elder", 15) == "coLeader"
    assert score_service._role_for_rank_band("coLeader", 10) == "coLeader"


def test_role_for_rank_band_elder_range(score_service):
    assert score_service._role_for_rank_band("member", 16) == "elder"
    assert score_service._role_for_rank_band("member", 25) == "elder"
    assert score_service._role_for_rank_band("elder", 20) == "elder"
    assert score_service._role_for_rank_band("coLeader", 20) == "coLeader"


def test_role_for_rank_band_demote_coleader(score_service):
    assert score_service._role_for_rank_band("coLeader", 26) == "elder"
    assert score_service._role_for_rank_band("coLeader", 35) == "elder"
    assert score_service._role_for_rank_band("elder", 30) == "elder"
    assert score_service._role_for_rank_band("member", 30) == "member"


def test_role_for_rank_band_demote_to_member(score_service):
    assert score_service._role_for_rank_band("coLeader", 36) == "member"
    assert score_service._role_for_rank_band("elder", 50) == "member"
    assert score_service._role_for_rank_band("member", 40) == "member"


# =============================================================================
# get_promotion_recommendations
# =============================================================================


def test_promotion_recommendations_no_completed_race(score_service):
    assert score_service.get_promotion_recommendations() == []


def test_promotion_recommendations_ranks_by_fame(
    db_session,
    score_service,
    member_factory,
    war_season_factory,
    river_race_factory,
    war_participation_factory,
):
    top = member_factory(tag="#TOP", role="member")
    bottom = member_factory(tag="#BOTTOM", role="member")
    db_session.add_all([top, bottom])
    db_session.flush()

    season = war_season_factory(season_id="2027-05")
    race = river_race_factory(war_season=season, section_index=0, is_completed=True)

    participation_top = war_participation_factory(
        member=top, river_race=race, fame=3000
    )
    participation_bottom = war_participation_factory(
        member=bottom, river_race=race, fame=500
    )

    db_session.add_all([participation_top, participation_bottom])
    db_session.commit()

    recs = score_service.get_promotion_recommendations()
    ranks = {r["tag"]: r["rank"] for r in recs}

    assert ranks["#TOP"] == 1
    assert ranks["#BOTTOM"] == 2


def test_promotion_recommendations_leader_exempt(
    db_session,
    score_service,
    member_factory,
    war_season_factory,
    river_race_factory,
    war_participation_factory,
):
    leader = member_factory(tag="#LEADER", role="leader")
    db_session.add(leader)
    db_session.flush()

    season = war_season_factory(season_id="2027-06")
    race = river_race_factory(war_season=season, section_index=0, is_completed=True)
    participation = war_participation_factory(member=leader, river_race=race, fame=100)

    db_session.add(participation)
    db_session.commit()

    recs = score_service.get_promotion_recommendations()

    assert recs[0]["action"] == "no_change"
    assert recs[0]["current_role"] == "leader"


def test_promotion_recommendations_first_sanction_demotes(
    db_session,
    score_service,
    member_factory,
    war_season_factory,
    river_race_factory,
    war_participation_factory,
):
    """First time under the fame threshold -> demoted one step, not kicked."""
    member = member_factory(tag="#ONCE", role="elder")
    db_session.add(member)
    db_session.flush()

    season = war_season_factory(season_id="2027-07")
    race = river_race_factory(war_season=season, section_index=0, is_completed=True)
    participation = war_participation_factory(member=member, river_race=race, fame=1000)

    db_session.add(participation)
    db_session.commit()

    recs = score_service.get_promotion_recommendations()
    rec = next(r for r in recs if r["tag"] == "#ONCE")

    assert rec["action"] == "demote"
    assert rec["recommended_role"] == "member"


def test_promotion_recommendations_second_consecutive_sanction_kicks(
    db_session,
    score_service,
    member_factory,
    war_season_factory,
    river_race_factory,
    war_participation_factory,
):
    """Two consecutive races under threshold -> kick, not demote."""
    member = member_factory(tag="#TWICE", role="elder")
    db_session.add(member)
    db_session.flush()

    season = war_season_factory(season_id="2027-08")
    race1 = river_race_factory(war_season=season, section_index=0, is_completed=True)
    race2 = river_race_factory(war_season=season, section_index=1, is_completed=True)

    participation1 = war_participation_factory(
        member=member, river_race=race1, fame=1000
    )
    participation2 = war_participation_factory(
        member=member, river_race=race2, fame=1200
    )

    db_session.add_all([participation1, participation2])
    db_session.commit()

    recs = score_service.get_promotion_recommendations()
    rec = next(r for r in recs if r["tag"] == "#TWICE")

    assert rec["action"] == "kick"


def test_promotion_recommendations_no_kick_on_first_ever_race(
    db_session,
    score_service,
    member_factory,
    war_season_factory,
    river_race_factory,
    war_participation_factory,
):
    """A member's very first race being under threshold must not kick them
    (there's no second_last_race to compare against)."""
    member = member_factory(tag="#FIRSTRACE", role="member")
    db_session.add(member)
    db_session.flush()

    season = war_season_factory(season_id="2027-09")
    race = river_race_factory(war_season=season, section_index=0, is_completed=True)
    participation = war_participation_factory(member=member, river_race=race, fame=100)

    db_session.add(participation)
    db_session.commit()

    recs = score_service.get_promotion_recommendations()
    rec = next(r for r in recs if r["tag"] == "#FIRSTRACE")

    assert rec["action"] != "kick"


def test_consistency_below_threshold_uses_clan_average(
    db_session,
    score_service,
    member_factory,
    war_season_factory,
    river_race_factory,
    war_participation_factory,
):
    """Members below MIN_RACES_FOR_CONSISTENCY get the clan average (of
    qualifying members), not their own trivial (insufficient-data) score."""

    qualifying_a = member_factory(tag="#QUALA", role="member")
    qualifying_b = member_factory(tag="#QUALB", role="member")
    new_member = member_factory(tag="#NEWBIE", role="member")
    db_session.add_all([qualifying_a, qualifying_b, new_member])
    db_session.flush()

    season = war_season_factory(season_id="2027-11")
    races = [
        river_race_factory(war_season=season, section_index=i, is_completed=True)
        for i in range(3)
    ]

    participations = [
        war_participation_factory(member=qualifying_a, river_race=race, fame=1000)
        for race in races
    ]
    for race, fame in zip(races, [800, 1200, 1000]):
        participations.append(
            war_participation_factory(member=qualifying_b, river_race=race, fame=fame)
        )
    # new_member only has one race - shouldn't qualify
    participations.append(
        war_participation_factory(member=new_member, river_race=races[-1], fame=3000)
    )

    db_session.add_all(participations)
    db_session.commit()

    recent_race_ids = score_service._get_recent_race_ids()

    raw_a = score_service._raw_consistency_score(qualifying_a, recent_race_ids)
    raw_b = score_service._raw_consistency_score(qualifying_b, recent_race_ids)
    expected_average = (raw_a + raw_b) / 2

    result = score_service._consistency_score(new_member, recent_race_ids)

    assert raw_a is not None
    assert raw_b is not None
    assert result == approx(expected_average)
    assert result != 100  # not the new member's own trivial (single-datapoint) score


def test_effective_join_date_uses_earliest_participation_when_earlier(
    db_session,
    score_service,
    member_factory,
    war_season_factory,
    river_race_factory,
    war_participation_factory,
):
    """
    Business rule: clan_joined_at can be stamped later than reality (e.g.
    a historical backfill created the Member row late) - the effective
    join date falls back to the earliest known participation instead.
    """
    now = get_time()

    member = member_factory(
        tag="#BACKFILLED", role="member", clan_joined_at=now - timedelta(days=10)
    )
    db_session.add(member)
    db_session.flush()

    season = war_season_factory(season_id="2027-13")
    old_race = river_race_factory(
        war_season=season,
        section_index=0,
        is_completed=True,
        created_date=now - timedelta(days=100),
    )
    participation = war_participation_factory(
        member=member, river_race=old_race, fame=1000
    )

    db_session.add(participation)
    db_session.commit()

    effective_date = score_service._effective_join_date(member)

    assert effective_date == old_race.created_date
