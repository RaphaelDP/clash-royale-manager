"""
================================================================================
Filename: job_run_state.py
Description: SQLAlchemy model for tracking the last run date of guarded,
    once-per-day scheduled jobs (prevents double-counting if a job runs
    more than once on the same day).
Author: Raphael Smilet
Date Created: 2026-08-01
Last Modified: 2026-08-01
Version: 0.1.0
Python Version: 3.12
Dependencies: sqlalchemy
================================================================================
"""

from datetime import date
from sqlalchemy import Integer, String, Date
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class JobRunState(Base):
    """
    Tracks the last calendar date a named job successfully ran, so
    idempotency-sensitive jobs (e.g. incrementing a daily counter) can
    guard against running more than once per day, regardless of how many
    times or from where they're triggered.
    """

    __tablename__ = "job_run_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    last_run_date: Mapped[date] = mapped_column(Date, nullable=False)
