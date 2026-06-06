"""
================================================================================
Filename: war_season.py
Description: SQLAlchemy model for tracking war seasons.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-06
Version: 0.1.0
Python Version: 3.11
Dependencies: sqlalchemy
================================================================================
"""

from __future__ import annotations  # to avoid Pylance: reportUndefinedVariable
from typing import List, Optional
from datetime import datetime
from sqlalchemy import String, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class WarSeason(Base):
    """
    SQLAlchemy model for war seasons.

    Attributes:
        id: Primary key.
        season_id: Unique identifier for the war season.
        start_date: Start date of the season.
        end_date: End date of the season.
        war_participations: One-to-many relationship with WarParticipation.
    """

    __tablename__ = "war_seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[str] = mapped_column(String, unique=True)
    start_date: Mapped[datetime] = mapped_column(DateTime)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    war_participations: Mapped[List["WarParticipation"]] = relationship(
        "WarParticipation", back_populates="war_season", cascade="all, delete-orphan"
    )
