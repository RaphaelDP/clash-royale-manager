"""
================================================================================
Filename: utils.py
Description: Utility functions for the Clan Manager Dashboard.
Author: Raphael Smilet
Date Created: 2026-06-09
Last Modified: 2026-06-09
Version: 1.0.0
Python Version: 3.12
Dependencies: datetime
================================================================================
"""

from datetime import datetime
from zoneinfo import ZoneInfo
from app.core.config import settings


def convert_timestamp_to_datetime(timestamp_str: str | None) -> datetime:
    """
    Converts a UTC timestamp string (e.g., '20260609T112122.000Z')
    into a datetime object localized to the SCHEDULER_TIMEZONE.
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
