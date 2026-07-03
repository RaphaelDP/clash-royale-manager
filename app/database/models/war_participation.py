"""
================================================================================
Filename: war_participation.py
Description: SQLAlchemy model for tracking member participation in river races.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-18
Version: 0.4.0
Python Version: 3.12
Dependencies: sqlalchemy
================================================================================
"""

from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models.member import Member
    from app.database.models.river_race import RiverRace


class WarParticipation(Base):
    """
    SQLAlchemy model for Clash Royale war participation.

    Attributes:
        id: Primary key.
        member_tag: Foreign key to Member.
        river_race_id: Foreign key to RiverRace.
        fame: Fame points earned.
        repair_points: Repair points earned.
        boat_attacks: Number of boat attacks.
        decks_used: Total decks used.
        decks_used_today: Decks used today.
        member: Relationship to Member.
        river_race: Relationship to RiverRace.
    """

    __tablename__ = "war_participation"
    __table_args__ = (
        UniqueConstraint("river_race_id", "member_tag", name="uq_race_member"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_tag: Mapped[str] = mapped_column(
        String, ForeignKey("members.tag"), nullable=False
    )
    river_race_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("river_races.id"), nullable=False
    )
    fame: Mapped[int] = mapped_column(Integer, default=0)
    repair_points: Mapped[int] = mapped_column(Integer, default=0)
    boat_attacks: Mapped[int] = mapped_column(Integer, default=0)
    decks_used: Mapped[int] = mapped_column(Integer, default=0)
    decks_used_today: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    member: Mapped["Member"] = relationship(back_populates="war_participations")
    river_race: Mapped["RiverRace"] = relationship(back_populates="war_participations")
