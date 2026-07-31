"""
================================================================================
Filename: contribution_score.py
Description: SQLAlchemy model for tracking contribution scores and their components.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-07-16
Version: 0.2.0
Python Version: 3.12
Dependencies: sqlalchemy
================================================================================
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from datetime import datetime
from sqlalchemy import Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models import Member


class ContributionScore(Base):
    """
    SQLAlchemy model for contribution scores.

    Attributes:
        id: Primary key.
        member_tag: Associated member tag (foreign key).
        score: Final weighted contribution score (0-100).
        war_activity: War Activity component (30%).
        war_performance: War Performance component (20%).
        donations: Donations component (15%).
        trophy_level: Trophy Level component (10%).
        activity: Activity component (10%).
        consistency: Consistency component (10%).
        seniority: Seniority component (5%).
        calculated_at: Timestamp of score calculation.
        member: Many-to-one relationship with Member.
    """

    __tablename__ = "contribution_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_tag: Mapped[str] = mapped_column(String, ForeignKey("members.tag"))
    score: Mapped[float] = mapped_column(Float)
    war_activity: Mapped[float] = mapped_column(Float)
    war_performance: Mapped[float] = mapped_column(Float)
    donations: Mapped[float] = mapped_column(Float)
    trophy_level: Mapped[float] = mapped_column(Float)
    activity: Mapped[float] = mapped_column(Float, default=0)
    consistency: Mapped[float] = mapped_column(Float, default=0)
    seniority: Mapped[float] = mapped_column(Float, default=0)
    calculated_at: Mapped[datetime] = mapped_column(DateTime)

    # Relationships
    member: Mapped[Member] = relationship(back_populates="contribution_scores")
