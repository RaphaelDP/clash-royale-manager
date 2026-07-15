"""
================================================================================
Filename: test_score_engine.py
Description: Unit tests for the ScoreService class.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-07-10
Version: 0.2.0
Python Version: 3.12
Dependencies: pytest, app.services.score_service
================================================================================
"""

from app.database.models import Member, PromotionScore


def test_calculate_promotion_score_all_components(
    db_session,
    score_service,
    member_factory,
    war_season_factory,
    river_race_factory,
    war_participation_factory,
):
    """
    Business rule: promotion score blends war activity (40%), war
    performance (30%), donations (20%), and trophy level (10%). Built so
    every component lands at exactly 50 to make the weighted sum easy to
    verify (50 * 1.0 = 50).
    """
    member_a = member_factory(tag="#A", trophies=4000, donations=75)
    member_b = member_factory(tag="#B", trophies=8000, donations=10)
    db_session.add_all([member_a, member_b])
    db_session.flush()

    season = war_season_factory(season_id="2026-12")
    race1 = river_race_factory(war_season=season, section_index=0)
    race2 = river_race_factory(war_season=season, section_index=1)

    # member_a participates only in race1, at half the max fame per race
    participation_a = war_participation_factory(
        member=member_a, river_race=race1, fame=1800
    )
    # member_b's participation just makes race2 exist as an "available race"
    participation_b = war_participation_factory(
        member=member_b, river_race=race2, fame=3600
    )

    db_session.add_all([participation_a, participation_b])
    db_session.commit()

    score = score_service.calculate_promotion_score("#A")

    assert score is not None
    assert score.war_activity == 50.0  # 1 participated / 2 available races
    assert score.war_win_rate == 50.0  # avg fame 1800 / MAX_FAME_PER_RACE 3600
    assert score.donations == 50.0  # 75 / DONATION_TARGET 150
    assert score.trophy_level == 50.0  # 4000 / clan max 8000
    assert score.score == 50.0

    updated_member = db_session.query(Member).filter_by(tag="#A").one()
    assert updated_member.promotion_score == 50.0
    assert updated_member.promotion_score_updated_at is not None


def test_calculate_promotion_score_unknown_member(score_service):
    """Business rule: calculating a score for a non-existent member returns None."""

    assert score_service.calculate_promotion_score("#UNKNOWN") is None


def test_calculate_promotion_score_no_war_data(
    db_session, score_service, member_factory
):
    """Business rule: a member with no races logged at all scores 0 on both war components."""

    member = member_factory(tag="#NEWBIE", trophies=1000, donations=0)
    db_session.add(member)
    db_session.commit()

    score = score_service.calculate_promotion_score("#NEWBIE")

    assert score.war_activity == 0
    assert score.war_win_rate == 0


def test_calculate_promotion_score_caps_at_100(
    db_session, score_service, member_factory
):
    """Business rule: components never exceed 100, even if raw values overshoot targets."""

    member = member_factory(tag="#OVER", donations=999, trophies=5000)
    db_session.add(member)
    db_session.commit()

    score = score_service.calculate_promotion_score("#OVER")

    assert score.donations == 100.0  # 999 donations >> DONATION_TARGET (150), capped
    assert (
        score.trophy_level == 100.0
    )  # sole member -> its own trophies are the clan max


def test_calculate_promotion_score_preserves_history(
    db_session, score_service, member_factory
):
    """Business rule: recalculating a score creates a new history row, never overwrites."""

    member = member_factory(tag="#HIST", donations=0, trophies=1000)
    db_session.add(member)
    db_session.commit()

    score_service.calculate_promotion_score("#HIST")
    score_service.calculate_promotion_score("#HIST")

    history = db_session.query(PromotionScore).filter_by(member_tag="#HIST").all()

    assert len(history) == 2


def test_calculate_all_scores_skips_left_members(
    db_session, score_service, member_factory
):
    """Business rule: calculate_all_scores only scores active members."""

    active = member_factory(tag="#ACTIVE", role="member")
    left = member_factory(tag="#LEFT", role="left")
    db_session.add_all([active, left])
    db_session.commit()

    scores = score_service.calculate_all_scores()

    scored_tags = {s.member_tag for s in scores}
    assert scored_tags == {"#ACTIVE"}


def test_calculate_promotion_score_excludes_incomplete_race(
    db_session,
    score_service,
    member_factory,
    war_season_factory,
    river_race_factory,
    war_participation_factory,
):
    """
    Business rule: an in-progress (incomplete) race must not count toward
    war activity or war performance, so scores stay stable until a war ends.
    """
    member = member_factory(tag="#LIVE", trophies=1000, donations=0)
    db_session.add(member)
    db_session.flush()

    season = war_season_factory(season_id="2027-01")
    completed_race = river_race_factory(
        war_season=season, section_index=0, is_completed=True
    )
    live_race = river_race_factory(
        war_season=season, section_index=1, is_completed=False
    )

    completed_participation = war_participation_factory(
        member=member, river_race=completed_race, fame=3600
    )
    live_participation = war_participation_factory(
        member=member, river_race=live_race, fame=0
    )

    db_session.add_all([completed_participation, live_participation])
    db_session.commit()

    score = score_service.calculate_promotion_score("#LIVE")

    # Only the completed race counts: 1 participated / 1 available = 100%
    assert score.war_activity == 100.0
    # Only the completed race's fame (3600) counts, not the live race's 0
    assert score.war_win_rate == 100.0
