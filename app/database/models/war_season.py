"""
================================================================================
Filename: war_season.py
Description: SQLAlchemy model for tracking war seasons.
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
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models import RiverRace


class WarSeason(Base):
    """
    SQLAlchemy model for war seasons.

    Attributes:
        id: Primary key.
        season_id: Unique identifier for the war season.

        river_races: One-to-many relationship with RiverRace.
    """

    __tablename__ = "war_seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[str] = mapped_column(String, unique=True)
    start_date: Mapped[datetime] = mapped_column(DateTime, unique=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    river_races: Mapped[List["RiverRace"]] = relationship(
        "RiverRace", back_populates="war_season", cascade="all, delete-orphan"
    )
