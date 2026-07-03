"""
================================================================================
Filename: member.py
Description: SQLAlchemy model for clan members, including tags, roles, trophies, and activity data.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-18
Version: 0.4.2
Python Version: 3.12
Dependencies: sqlalchemy
================================================================================
"""

from __future__ import annotations  # to avoid Pylance: reportUndefinedVariable
from typing import List, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, DateTime, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models import Snapshot, WarParticipation, PromotionScore


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
        promotion_score: Calculated promotion score.
        promotion_score_updated_at: Timestamp of last score update.
        snapshots: One-to-many relationship with Snapshot.
        war_participations: One-to-many relationship with WarParticipation.
        promotion_scores: One-to-many relationship with PromotionScore.
    """

    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    tag: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String)
    trophies: Mapped[int] = mapped_column(Integer, default=0)
    donations: Mapped[int] = mapped_column(Integer, default=0)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    promotion_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    promotion_score_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    # Relationships
    snapshots: Mapped[List["Snapshot"]] = relationship(
        "Snapshot", back_populates="member", cascade="all, delete-orphan"
    )
    war_participations: Mapped[List["WarParticipation"]] = relationship(
        "WarParticipation", back_populates="member", cascade="all, delete-orphan"
    )
    promotion_scores: Mapped[List["PromotionScore"]] = relationship(
        "PromotionScore", back_populates="member", cascade="all, delete-orphan"
    )
