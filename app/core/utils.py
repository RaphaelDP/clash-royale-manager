"""
================================================================================
Filename: utils.py
Description: Utility functions for the Clan Manager Dashboard.
Author: Raphael Smilet
Date Created: 2026-06-09
Last Modified: 2026-10-01
Version: 1.0.2
Python Version: 3.12
Dependencies: datetime
================================================================================
"""

from datetime import datetime, date
from zoneinfo import ZoneInfo
from app.core.config import settings
from app.core.constants import ACTIVITY_HALF_LIFE, ACTIVITY_STEEPNESS


def activity_score_from_days(days: float | None) -> int:
    """
    Map elapsed inactive days to a rounded 0–100 activity score.

    Unknown activity scores zero; negative elapsed days are clamped to zero. The
    configured half-life and steepness control the decay curve.

    Args:
        days: Number of days since last seen, or None if unknown.

    Returns:
        int: Activity score between 0 and 100.
    """
    if days is None:
        return 0

    score = 100 / (1 + pow(max(0, days) / ACTIVITY_HALF_LIFE, ACTIVITY_STEEPNESS))
    return round(score)


def convert_timestamp_to_datetime(timestamp_str: str | None) -> datetime:
    """
    Parse a Clash Royale UTC timestamp into naive scheduler-local time.

    Args:
        timestamp_str: UTC API timestamp in YYYYMMDDTHHMMSS.ffffffZ form, or an
            empty value.

    Returns:
        datetime | None: Naive scheduler-local datetime, or None for empty input.

    Raises:
        ValueError: The supplied nonempty timestamp does not match the API format.
    """
    if not timestamp_str:
        return None

    # 1. Parse the specific ISO format string into a UTC-aware datetime object
    # %Y%m%dT%H%M%S.%fZ handles '20260609T112122.000Z'
    utc_dt = datetime.strptime(timestamp_str, "%Y%m%dT%H%M%S.%fZ").replace(
        tzinfo=ZoneInfo("UTC")
    )

    # 2. Fetch the target timezone from config
    target_tz = ZoneInfo(settings.SCHEDULER_TIMEZONE)

    # 3. Convert the UTC datetime to the target timezone
    local_dt = utc_dt.astimezone(target_tz)

    return local_dt.replace(tzinfo=None)  # Return naive datetime in local time


def format_datetime(value: datetime | date | str | None) -> str:
    """
    Convert datetime/date values into a human-readable string for display.

    Args:
        value: Datetime, date, string, or None; None is displayed as "No data".

    Returns:
        str: Formatted string representation of the date/time.
    """
    if value is None:
        return "No data"

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")

    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")

    return str(value)


def get_time() -> datetime:
    """
    Return the current scheduler-local wall time without timezone information.

    Args:
        None.

    Returns:
        datetime: Naive wall time in settings.SCHEDULER_TIMEZONE.
    """
    target_tz = ZoneInfo(settings.SCHEDULER_TIMEZONE)
    return datetime.now(target_tz).replace(tzinfo=None)


def count(args) -> int:
    """
    Build a SQL COUNT expression without executing a database query.

    Args:
        args: SQLAlchemy column or expression whose non-null values should be
            counted.

    Returns:
        sqlalchemy.sql.functions.count: Unevaluated SQL COUNT expression.
    """
    from sqlalchemy import func  # pylint: disable=import-outside-toplevel

    # Import here to avoid circular imports

    return func.count(args)  # pylint: disable=not-callable
