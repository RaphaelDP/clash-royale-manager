"""
================================================================================
Filename: scheduler.py
Description: Scheduler configuration for running jobs at specified intervals.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-07-12
Version: 0.2.0
Python Version: 3.12
Dependencies: apscheduler, app.scheduler.jobs
================================================================================
"""

from apscheduler.schedulers.background import BackgroundScheduler
from app.core.config import settings
from app.core.logger import logger
from app.scheduler.jobs import (
    update_clan_members,
    update_war_data,
    create_daily_snapshots,
    calculate_scores,
    send_daily_report,
)


def start_scheduler() -> BackgroundScheduler:
    """
    Start the scheduler with configured jobs.

    Returns:
        BackgroundScheduler: the running scheduler instance, so the caller
        can hold a reference (e.g. to shut it down gracefully).
    """
    scheduler = BackgroundScheduler(timezone=settings.SCHEDULER_TIMEZONE)

    # Hourly: keep member and war data fresh
    scheduler.add_job(update_clan_members, "interval", hours=1)
    scheduler.add_job(update_war_data, "interval", hours=1)

    # Daily: snapshots -> scores -> report, in that order
    scheduler.add_job(create_daily_snapshots, "cron", hour=0, minute=0)
    scheduler.add_job(calculate_scores, "cron", hour=0, minute=30)
    scheduler.add_job(send_daily_report, "cron", hour=1, minute=0)

    scheduler.start()
    logger.info("Scheduler started.")

    return scheduler
