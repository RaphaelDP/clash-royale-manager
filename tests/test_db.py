"""
================================================================================
Filename: test_db.py
Description: Unit tests for database models and relationships.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-06
Version: 1.0.0
Python Version: 3.12
Dependencies: pytest, app.database.models, app.database.session
================================================================================
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, UTC

from app.database.base import Base
from app.database.models.member import Member
from app.database.models.snapshot import Snapshot
from app.database.models.war_season import WarSeason
from app.database.models.war_participation import WarParticipation
from app.database.models.promotion_score import PromotionScore

@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

def test_create_member(db_session):
    """Test creating a new member in the database."""
    member = Member(
        tag="#ABC123",
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
    assert member.tag == "#ABC123"
    assert member.name == "Raphael"
    assert member.role == "Member"
    assert member.trophies == 9000

def test_member_relationships(db_session):
    """Test one-to-many relationships for Member (Snapshots, WarParticipations, PromotionScores)."""
    # Create a member
    member = Member(
        tag="#TEST123",
        name="Raphael",
        role="Member",
        trophies=8000,
        donations=100,
        last_seen=datetime.now(UTC),
    )

    # Create a war season
    war_season = WarSeason(
        season_id="2026-01",
        start_date=datetime.now(UTC),
        end_date=None,
    )

    # Create related objects
    war_participation = WarParticipation(
        member_tag=member.tag,
        season_id=war_season.season_id,
        attacks_used=10,
        attacks_possible=10,
        wins=5,
        losses=5,
        medals=100,
    )

    snapshot = Snapshot(
        member_tag=member.tag,
        trophies=8000,
        donations=100,
        collected_at=datetime.now(UTC),
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

    # Add all objects to the session
    db_session.add_all([member, war_season, war_participation, snapshot, promotion_score])
    db_session.commit()
    db_session.refresh(member)

    # Reload from DB to test relationships
    saved_member = db_session.get(Member, member.id)
    saved_war_season = db_session.get(WarSeason, war_season.id)

    # Assert relationships
    assert saved_member is not None
    assert len(saved_member.snapshots) == 1
    assert saved_member.snapshots[0].member_tag == member.tag
    assert saved_member.snapshots[0].trophies == 8000

    assert len(saved_member.war_participations) == 1
    assert saved_member.war_participations[0].member_tag == member.tag
    assert saved_member.war_participations[0].wins == 5

    assert len(saved_member.promotion_scores) == 1
    assert saved_member.promotion_scores[0].member_tag == member.tag
    assert saved_member.promotion_scores[0].score == 95.5

    # Assert WarSeason relationship
    assert saved_war_season is not None
    assert len(saved_war_season.war_participations) == 1
    assert saved_war_season.war_participations[0].season_id == war_season.season_id