"""
================================================================================
Filename: test_db.py
Description: Unit tests for database models and relationships.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-18
Version: 0.4.0
Python Version: 3.12
Dependencies: pytest, app.database.models
================================================================================
"""

from app.database.models import Member


def test_create_member(db_session, test_members):
    """
    Verify a Member can be persisted and retrieved.
    """

    member = test_members[0]

    db_session.add(member)
    db_session.commit()
    db_session.refresh(member)

    assert member.id is not None
    assert member.tag == "#TEST_PLAYER1"
    assert member.name == "Player 1"
    assert member.role == "Leader"
    assert member.trophies == 5000
    assert member.donations == 100

    saved_member = db_session.query(Member).filter_by(tag="#TEST_PLAYER1").one()

    assert saved_member.id == member.id
    assert saved_member.name == member.name


def test_member_relationships(populated_member_graph):
    """
    Verify Member relationships:
    - snapshots
    - war participations
    - promotion scores
    """

    member = populated_member_graph["member"]
    war_season = populated_member_graph["war_season"]

    # Snapshot relationship

    assert len(member.snapshots) == 1

    snapshot = member.snapshots[0]

    assert snapshot.member_tag == member.tag
    assert snapshot.trophies == member.trophies
    assert snapshot.donations == member.donations
    assert snapshot.member is member

    # WarParticipation relationship

    assert len(member.war_participations) == 1

    participation = member.war_participations[0]

    assert participation.member_tag == member.tag
    assert participation.fame == 50
    assert participation.repair_points == 5
    assert participation.boat_attacks == 2
    assert participation.member is member
    assert participation.river_race is not None

    # PromotionScore relationship

    assert len(member.promotion_scores) == 1

    score = member.promotion_scores[0]

    assert score.member_tag == member.tag
    assert score.score == 95.5
    assert score.member is member

    # WarSeason relationship

    assert len(war_season.river_races) == 1

    race = war_season.river_races[0]

    assert race.season_id == war_season.season_id
    assert race.section_index == 1
    assert race.created_date is not None
    assert race.war_season is war_season
    assert len(race.war_participations) == 1
