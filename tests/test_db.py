"""
================================================================================
Filename: test_db.py
Description: Unit tests for database models and relationships.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-08
Version: 0.3.2
Python Version: 3.12
Dependencies: pytest, app.database.models
================================================================================
"""

from datetime import UTC, datetime

from app.database.models.member import Member
from app.database.models.snapshot import Snapshot
from app.database.models.war_season import WarSeason
from app.database.models.war_participation import WarParticipation
from app.database.models.promotion_score import PromotionScore


def test_create_member(db_session):
    """
    Verify a Member can be persisted and retrieved.
    """

    member = Member(
        tag="#TEST000",
        name="Raphael",
        role="Member",
        trophies=9000,
        donations=0,
        last_seen=datetime.now(UTC),
    )

    db_session.add(member)
    db_session.commit()
    db_session.refresh(member)

    assert member.id is not None
    assert member.tag == "#TEST000"
    assert member.name == "Raphael"
    assert member.role == "Member"
    assert member.trophies == 9000
    assert member.donations == 0


def test_member_relationships(db_session):
    """
    Verify Member relationships:
    - snapshots
    - war participations
    - promotion scores
    """

    member = Member(
        tag="#TEST123",
        name="Emma",
        role="Member",
        trophies=8000,
        donations=100,
        last_seen=datetime.now(UTC),
    )

    war_season = WarSeason(
        season_id="2026-01",
        start_date=datetime.now(UTC),
        end_date=None,
    )

    db_session.add_all([member, war_season])
    db_session.commit()

    snapshot = Snapshot(
        member_tag=member.tag,
        trophies=8000,
        donations=100,
        collected_at=datetime.now(UTC),
    )

    war_participation = WarParticipation(
        member_tag=member.tag,
        season_id=war_season.season_id,
        attacks_used=10,
        attacks_possible=10,
        wins=5,
        losses=5,
        medals=100,
    )

    promotion_score = PromotionScore(
        member_tag=member.tag,
        score=95.5,
        war_activity=0.4,
        war_win_rate=0.3,
        donations=0.2,
        trophy_level=0.1,
        calculated_at=datetime.now(UTC),
    )

    db_session.add_all(
        [
            snapshot,
            war_participation,
            promotion_score,
        ]
    )
    db_session.commit()

    saved_member = (
        db_session.query(Member)
        .filter(Member.tag == "#TEST123")
        .one()
    )

    saved_war_season = (
        db_session.query(WarSeason)
        .filter(WarSeason.season_id == "2026-01")
        .one()
    )

    # Snapshot relationship

    assert len(saved_member.snapshots) == 1

    saved_snapshot = saved_member.snapshots[0]

    assert saved_snapshot.member_tag == "#TEST123"
    assert saved_snapshot.trophies == 8000
    assert saved_snapshot.donations == 100

    # WarParticipation relationship

    assert len(saved_member.war_participations) == 1

    saved_participation = saved_member.war_participations[0]

    assert saved_participation.member_tag == "#TEST123"
    assert saved_participation.wins == 5
    assert saved_participation.losses == 5
    assert saved_participation.medals == 100

    # PromotionScore relationship

    assert len(saved_member.promotion_scores) == 1

    saved_score = saved_member.promotion_scores[0]

    assert saved_score.member_tag == "#TEST123"
    assert saved_score.score == 95.5

    # WarSeason relationship

    assert len(saved_war_season.war_participations) == 1

    season_participation = saved_war_season.war_participations[0]

    assert season_participation.season_id == "2026-01"
    assert season_participation.member_tag == "#TEST123"