"""
================================================================================
Filename: snapshot.py
Description: SQLAlchemy model for tracking daily snapshots of member data.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-18
Version: 0.4.2
Python Version: 3.12
Dependencies: sqlalchemy
================================================================================
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models import Member


class Snapshot(Base):
    """
    SQLAlchemy model for member data snapshots.

    Attributes:
        id: Primary key.
        member_tag: Associated member tag (foreign key).
        trophies: Trophy count at snapshot time.
        donations: Donations count at snapshot time.
        collected_at: Timestamp of snapshot collection.
        member: Many-to-one relationship with Member.
    """

    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_tag: Mapped[str] = mapped_column(String, ForeignKey("members.tag"))
    trophies: Mapped[int] = mapped_column(Integer)
    donations: Mapped[int] = mapped_column(Integer)
    collected_at: Mapped[datetime] = mapped_column(DateTime)

    # Relationships
    member: Mapped["Member"] = relationship(back_populates="snapshots")
