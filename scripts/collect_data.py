"""
================================================================================
Filename: collect_data.py
Description: Script to collect and sync data from the Clash Royale API.
Author: Raphael Smilet
Date Created: 2026-07-03
Last Modified: 2026-09-11
Version: 0.9.1
Python Version: 3.12
Dependencies: app.scheduler.jobs
================================================================================
"""

from app.core.logger import logger
from app.database.session import SessionLocal
from app.scheduler.jobs import (
    backup_database,
    calculate_scores,
    create_daily_snapshots,
    increment_membership_days,
    update_clan_members,
    update_war_data,
)


def main() -> None:
    """Run the complete data collection pipeline."""
    db = SessionLocal()

    try:
        jobs = [
            update_clan_members,
            update_war_data,
            create_daily_snapshots,
            increment_membership_days,
            calculate_scores,
            backup_database,
        ]

        for job in jobs:
            if not job(db):
                logger.warning(
                    "Data collection stopped because '%s' failed.", job.__name__
                )
                break

        else:
            logger.info("Data collection completed successfully.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
