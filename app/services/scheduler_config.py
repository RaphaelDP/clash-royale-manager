"""
================================================================================
Filename: scheduler_config.py
Description: Validate and atomically persist scheduler settings for cross-process reload.
Author: Raphael Smilet
Date Created: 2026-09-30
Last Modified: 2026-09-30
Version: 0.1.0
Python Version: 3.12
================================================================================
"""

import copy
import json
import os
import re
from pathlib import Path
import tempfile

DEFAULT_SCHEDULE = {
    "enabled": True,
    "intervals": {"update_clan_members": 60, "update_war_data": 60},
    "daily": {
        "create_daily_snapshots": "00:00",
        "increment_membership_days": "00:05",
        "calculate_scores": "00:30",
        "send_daily_report": "01:00",
        "backup_database": "02:00",
    },
}


def config_path():
    """Return the configured schedule file location."""
    return Path(os.getenv("SCHEDULER_CONFIG_FILE", "data/scheduler.json"))


def validate_schedule(value):
    """Validate job names, enabled state, intervals, and clock times."""
    if not isinstance(value, dict) or set(value) != set(DEFAULT_SCHEDULE):
        raise ValueError(
            "Schedule must contain enabled, intervals, and daily settings."
        )
    if not isinstance(value["enabled"], bool):
        raise ValueError("Enabled must be a boolean.")
    for group in ("intervals", "daily"):
        if not isinstance(value[group], dict) or set(value[group]) != set(
            DEFAULT_SCHEDULE[group]
        ):
            raise ValueError(f"Unexpected jobs in {group}.")
    for minutes in value["intervals"].values():
        if (
            not isinstance(minutes, int)
            or isinstance(minutes, bool)
            or not 1 <= minutes <= 1440
        ):
            raise ValueError(
                "Sync intervals must be integers between 1 and 1440 minutes."
            )
    for time in value["daily"].values():
        if not isinstance(time, str) or not re.fullmatch(
            r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", time
        ):
            raise ValueError("Daily times must use HH:MM (00:00–23:59).")
    return copy.deepcopy(value)


def load_schedule():
    """Load validated settings, defaulting only when no file exists."""
    try:
        return validate_schedule(json.loads(config_path().read_text(encoding="utf-8")))
    except FileNotFoundError:
        return copy.deepcopy(DEFAULT_SCHEDULE)


def save_schedule(value):
    """Validate and atomically replace the persisted schedule."""
    value = validate_schedule(value)
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".scheduler-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            json.dump(value, file, indent=2)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return value
