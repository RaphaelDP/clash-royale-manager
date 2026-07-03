"""
================================================================================
Filename: river_race.py
Description: SQLAlchemy model for Clash Royale River Races.
Author: Raphael Smilet
Date Created: 2026-06-09
Last Modified: 2026-06-18
Version: 0.4.0
Python Version: 3.12
Dependencies: sqlalchemy, app.database.base
================================================================================
"""

from __future__ import annotations  # to avoid Pylance: reportUndefinedVariable
from typing import List, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models import WarParticipation, WarSeason


class RiverRace(Base):
    """
    SQLAlchemy model for Clash Royale River Races.

    Attributes:
        id: Primary key.
        season_id: Foreign key to WarSeason.
        section_index: Index of the river race section.
        created_date: Creation date of the river race.
        war_season: Relationship to WarSeason.
        war_participations: One-to-many relationship with WarParticipation.
    """

    __tablename__ = "river_races"
    __table_args__ = (
        UniqueConstraint("season_id", "section_index", name="uq_river_race"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    season_id: Mapped[str] = mapped_column(
        String, ForeignKey("war_seasons.season_id"), nullable=False
    )
    section_index: Mapped[int] = mapped_column(Integer, nullable=False)
    created_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationships
    war_season: Mapped[WarSeason] = relationship(back_populates="river_races")
    war_participations: Mapped[List["WarParticipation"]] = relationship(
        "WarParticipation", back_populates="river_race", cascade="all, delete-orphan"
    )
