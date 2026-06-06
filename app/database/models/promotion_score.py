"""
================================================================================
Filename: promotion_score.py
Description: SQLAlchemy model for tracking promotion scores and their components.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-06
Version: 0.1.1
Python Version: 3.11
Dependencies: sqlalchemy
================================================================================
"""

from __future__ import annotations  # to avoid Pylance: reportUndefinedVariable

from datetime import datetime
from sqlalchemy import Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class PromotionScore(Base):
    """
    SQLAlchemy model for promotion scores.

    Attributes:
        id: Primary key.
        member_tag: Associated member tag (foreign key).
        score: Calculated promotion score.
        war_activity: War activity component of the score.
        war_win_rate: War win rate component of the score.
        donations: Donations component of the score.
        trophy_level: Trophy level component of the score.
        calculated_at: Timestamp of score calculation.
        member: Many-to-one relationship with Member.
    """

    __tablename__ = "promotion_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_tag: Mapped[str] = mapped_column(String, ForeignKey("members.tag"))
    score: Mapped[float] = mapped_column(Float)
    war_activity: Mapped[float] = mapped_column(Float)
    war_win_rate: Mapped[float] = mapped_column(Float)
    donations: Mapped[float] = mapped_column(Float)
    trophy_level: Mapped[float] = mapped_column(Float)
    calculated_at: Mapped[datetime] = mapped_column(DateTime)

    # Relationships
    member: Mapped["Member"] = relationship("Member", back_populates="promotion_scores")
