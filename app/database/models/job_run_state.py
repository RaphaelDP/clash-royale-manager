"""
================================================================================
Filename: job_run_state.py
Description: SQLAlchemy model for tracking scheduled job execution state.
Author: Raphael Smilet
Date Created: 2026-08-01
Last Modified: 2026-09-11
Version: 0.9.1
Python Version: 3.12
Dependencies: sqlalchemy
================================================================================
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class JobRunState(Base):
    """
    Tracks the execution state of a named job.

    last_run_date is used by idempotency-sensitive daily jobs.
    last_attempt_at, last_success_at, and last_error provide persistent
    information about the health and freshness of each job.
    """

    __tablename__ = "job_run_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    last_run_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    last_attempt_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_success_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    last_error: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
