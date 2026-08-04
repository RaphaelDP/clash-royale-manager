"""
================================================================================
Filename: member.py
Description: SQLAlchemy model for clan members, including tags, roles, trophies, and activity data.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-07-16
Version: 0.5.0
Python Version: 3.12
Dependencies: sqlalchemy
================================================================================
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, DateTime, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models import Snapshot, WarParticipation, ContributionScore


class Member(Base):
    """
    SQLAlchemy model for clan members.

    Attributes:
        id: Primary key.
        tag: Unique Clash Royale player tag.
        name: Player name.
        role: Role in the clan (Leader, Co-Leader, Elder, Member).
        trophies: Current trophy count.
        donations: Total donations made.
        last_seen: Timestamp of last activity.
        clan_joined_at: Timestamp this app first recorded the member (not
            necessarily their true in-game join date). Used for the
            Seniority contribution score component; NULL for members
            that existed before this field was introduced.
        contribution_score: Calculated contribution score.
        contribution_score_updated_at: Timestamp of last score update.
        snapshots: One-to-many relationship with Snapshot.
        war_participations: One-to-many relationship with WarParticipation.
        contribution_scores: One-to-many relationship with ContributionScore.
    """

    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    tag: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String)
    trophies: Mapped[int] = mapped_column(Integer, default=0)
    donations: Mapped[int] = mapped_column(Integer, default=0)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    clan_joined_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    contribution_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    contribution_score_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    days_in_clan: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    snapshots: Mapped[List["Snapshot"]] = relationship(
        "Snapshot", back_populates="member", cascade="all, delete-orphan"
    )
    war_participations: Mapped[List["WarParticipation"]] = relationship(
        "WarParticipation", back_populates="member", cascade="all, delete-orphan"
    )
    contribution_scores: Mapped[List["ContributionScore"]] = relationship(
        "ContributionScore", back_populates="member", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Member(tag={self.tag} "
            f"name={self.name} "
            f"role={self.role} "
            f"trophies={self.trophies} "
            f"donations={self.donations} "
            f"last_seen={self.last_seen} "
            f"clan_joined_at={self.clan_joined_at} "
            f"contribution_score={self.contribution_score} "
            f"at {self.contribution_score_updated_at} )>"
        )
