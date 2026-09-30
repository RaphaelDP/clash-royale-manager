"""
================================================================================
Filename: scheduler.py
Description: Configure scheduled jobs with persisted settings and controlled daily catch-up.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-09-30
Version: 0.2.1
Python Version: 3.12
================================================================================
"""

from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from app.core.config import settings
from app.core.logger import logger
from app.core.utils import get_time
from app.database.models import JobRunState
from app.database.session import SessionLocal
from app.scheduler import jobs
from app.services.scheduler_config import load_schedule

JOB_NAMES = (
    "update_clan_members",
    "update_war_data",
    "create_daily_snapshots",
    "increment_membership_days",
    "calculate_scores",
    "send_daily_report",
    "backup_database",
)


def apply_schedule(scheduler, config, *, catch_up=False):
    """Install validated settings; recover today's missed daily work only."""
    for name in JOB_NAMES:
        if scheduler.get_job(name):
            scheduler.remove_job(name)
    if not config["enabled"]:
        return
    for name, minutes in config["intervals"].items():
        scheduler.add_job(
            getattr(jobs, name),
            "interval",
            minutes=minutes,
            id=name,
            max_instances=1,
            coalesce=True,
        )
    now = get_time()
    with SessionLocal() as db:
        states = {row.job_name: row for row in db.query(JobRunState).all()}
        for order, (name, time) in enumerate(
            sorted(config["daily"].items(), key=lambda item: item[1])
        ):
            hour, minute = map(int, time.split(":"))
            state = states.get(name)
            success_today = (
                state
                and state.last_success_at
                and state.last_success_at.date() == now.date()
            )
            options = {}
            if (
                catch_up
                and (now.hour, now.minute) >= (hour, minute)
                and not success_today
            ):
                options["next_run_time"] = now + timedelta(milliseconds=order)
            scheduler.add_job(
                getattr(jobs, name),
                "cron",
                hour=hour,
                minute=minute,
                id=name,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=3600,
                **options,
            )


def start_scheduler():
    """Start a single-worker scheduler with same-day recovery."""
    scheduler = BackgroundScheduler(
        timezone=settings.SCHEDULER_TIMEZONE,
        executors={"default": {"type": "threadpool", "max_workers": 1}},
    )
    config = load_schedule()
    apply_schedule(scheduler, config, catch_up=True)
    scheduler.start()
    scheduler.runtime_config = config
    logger.info("Scheduler started.")
    return scheduler


def reload_scheduler(scheduler):
    """Apply changed settings while retaining the last valid schedule on errors."""
    try:
        config = load_schedule()
        if config != scheduler.runtime_config:
            apply_schedule(scheduler, config, catch_up=False)
            scheduler.runtime_config = config
            logger.info("Scheduler configuration reloaded.")
    except (ValueError, OSError):
        logger.exception(
            "Invalid scheduler settings; retaining the last valid configuration."
        )
