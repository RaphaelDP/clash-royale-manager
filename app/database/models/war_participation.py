"""
================================================================================
Filename: war_participation.py
Description: SQLAlchemy model for tracking member participation in war seasons.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-06
Version: 0.1.2
Python Version: 3.11
Dependencies: sqlalchemy
================================================================================
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models import Member, WarSeason

class WarParticipation(Base):
    """
    SQLAlchemy model for war participation data.

    Attributes:
        id: Primary key.
        member_tag: Associated member tag (foreign key).
        season_id: Associated war season ID (foreign key).
        attacks_used: Number of attacks used in the war.
        attacks_possible: Total possible attacks.
        wins: Number of wins.
        losses: Number of losses.
        medals: Total medals earned.
        member: Many-to-one relationship with Member.
        war_season: Many-to-one relationship with WarSeason.
    """

    __tablename__ = "war_participations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_tag: Mapped[str] = mapped_column(String, ForeignKey("members.tag"))
    season_id: Mapped[str] = mapped_column(String, ForeignKey("war_seasons.season_id"))
    attacks_used: Mapped[int] = mapped_column(Integer)
    attacks_possible: Mapped[int] = mapped_column(Integer)
    wins: Mapped[int] = mapped_column(Integer)
    losses: Mapped[int] = mapped_column(Integer)
    medals: Mapped[int] = mapped_column(Integer)

    # Relationships
    member: Mapped[Member] = relationship(
         back_populates="war_participations"
    )
    war_season: Mapped[WarSeason] = relationship(
         back_populates="war_participations"
    )
