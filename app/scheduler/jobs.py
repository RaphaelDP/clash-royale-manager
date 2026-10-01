"""
================================================================================
Filename: jobs.py
Description: Scheduled jobs for data collection, updates, and analytics.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-10-01
Version: 0.9.3
Python Version: 3.12
Dependencies: app.services, app.integrations.discord, app.database.session
================================================================================
"""

from collections.abc import Callable
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.job_lock import job_lock
from app.core.logger import logger
from app.core.utils import get_time
from app.database.models import JobRunState
from app.database.session import SessionLocal
from app.services.clan_service import ClanService
from app.services.member_service import MemberService
from app.services.war_service import WarService
from app.services.snapshot_service import SnapshotService
from app.services.score_service import ScoreService
from app.integrations.discord.bot import DiscordBot
from app.integrations.discord.reports import DiscordReporter
from scripts.backup_db import backup_database as run_database_backup


def _get_job_state(db: Session, job_name: str) -> JobRunState:
    """
    Get or create the state record for a job.

    Args:
        db: SQLAlchemy database session.
        job_name: Name of the job.

    Returns:
        JobRunState: Existing or newly flushed state record; not committed here.
    """
    state = db.query(JobRunState).filter_by(job_name=job_name).first()

    if state is None:
        state = JobRunState(
            job_name=job_name,
            last_attempt_at=get_time(),
        )
        db.add(state)
        db.flush()

    return state


def _execute_job(
    job_name: str,
    job_function: Callable[[Session], None],
    db_session: Session | None = None,
    *,
    daily: bool = False,
) -> bool:
    """
    Execute a job and persist its execution state.

    A session is created automatically when the job is called directly by the scheduler.
    When a session is supplied, it is reused by collect_data.py.

    Args:
        job_name: Name of the job.
        job_function: Function to execute, which accepts a SQLAlchemy session.
        db_session: Optional SQLAlchemy session. If None, a new session is created.
        daily: Skip execution after a recorded success on the current local date.

    Returns:
        bool: True on success or an applicable daily skip; False on a caught failure.
    """
    own_session = db_session is None
    db = db_session or SessionLocal()

    state = None

    try:
        state = _get_job_state(db, job_name)
        if daily and state.last_run_date == get_time().date():
            return True
        state.last_attempt_at = get_time()
        state.last_error = None
        db.commit()

        job_function(db)

        state = _get_job_state(db, job_name)
        state.last_success_at = get_time()
        if daily:
            state.last_run_date = get_time().date()
        state.last_error = None
        db.commit()

        logger.info("Job '%s' completed successfully.", job_name)
        return True

    except Exception as e:
        db.rollback()

        try:
            state = _get_job_state(db, job_name)
            state.last_attempt_at = get_time()
            state.last_error = str(e)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Unable to persist job failure state.")

        logger.error("Job '%s' failed: %s", job_name, e)
        return False

    finally:
        if own_session:
            db.close()


def _run_job(job_name, job_function, db_session=None, *, daily=False):
    """
    Run a job with a non-blocking lock to prevent concurrent execution.

    Args:
        job_name: Name of the job.
        job_function: Function to execute, which accepts a SQLAlchemy session.
        db_session: Optional SQLAlchemy session. If None, a new session is created.
        daily: Skip execution after a recorded success on the current local date.

    Returns:
        bool: True on success or an applicable daily skip; False on a caught failure or
        lock contention.
    """
    with job_lock(job_name) as acquired:
        if not acquired:
            logger.warning("Job %s is already running.", job_name)
            return False
        return _execute_job(job_name, job_function, db_session, daily=daily)


## Different Jobs Definitions


def update_clan_members(db_session: Session | None = None) -> bool:
    """
    Update clan members from the Clash Royale API. A session is created automatically
    when the job is called directly by the scheduler. When a session is supplied, it is
    reused by collect_data.py.

    Args:
        db_session: Optional SQLAlchemy session. If None, a new session is created.

    Returns:
        bool: True on success or an applicable daily skip; False on a caught failure or
        lock contention.
    """

    def job(db: Session) -> None:
        """
        Sync clan members from the Clash Royale API and update the database.

        Args:
            db: SQLAlchemy database session.

        Returns:
            None.
        """
        clan_service = ClanService(db)
        clan_service.sync_clan_members(settings.CLAN_TAG)
        logger.info("Synced clan members.")

    return _run_job("update_clan_members", job, db_session)


def update_war_data(db_session: Session | None = None) -> bool:
    """
    Update war data from the Clash Royale API. A session is created automatically when
    the job is called directly by the scheduler. When a session is supplied, it is
    reused by collect_data.py.

    Args:
        db_session: Optional SQLAlchemy session. If None, a new session is created.

    Returns:
        bool: True on success or an applicable daily skip; False on a caught failure or
        lock contention.
    """

    def job(db: Session) -> None:
        """
        Sync war data from the Clash Royale API and update the database.

        Args:
            db: SQLAlchemy database session.

        Returns:
            None.
        """
        war_service = WarService(db)
        war_service.sync_river_race_log(settings.CLAN_TAG)
        war_service.sync_current_river_race(settings.CLAN_TAG)
        logger.info("Synced war data.")

    return _run_job("update_war_data", job, db_session)


def create_daily_snapshots(db_session: Session | None = None) -> bool:
    """
    Create daily snapshots of member data. A session is created automatically when the
    job is called directly by the scheduler. When a session is supplied, it is reused by
    collect_data.py.

    Args:
        db_session: Optional SQLAlchemy session. If None, a new session is created.

    Returns:
        bool: True on success or an applicable daily skip; False on a caught failure or
        lock contention.
    """

    def job(db: Session) -> None:
        """
        Create daily snapshots of member data for historical tracking.

        Args:
            db: SQLAlchemy database session.

        Returns:
            None.
        """
        snapshot_service = SnapshotService(db)
        snapshot_service.create_daily_snapshots(None)
        logger.info("Created daily snapshots.")

    return _run_job("create_daily_snapshots", job, db_session, daily=True)


def calculate_scores(db_session: Session | None = None) -> bool:
    """
    Calculate contribution scores for all members.

    Args:
        db_session: Optional SQLAlchemy session. If None, a new session is created.

    Returns:
        bool: True on success or an applicable daily skip; False on a caught failure or
        lock contention.
    """

    def job(db: Session) -> None:
        """
        Run the calculate scores callback with the supplied session.

        Args:
            db: SQLAlchemy session used for database operations.

        Returns:
            None.
        """
        score_service = ScoreService(db)
        score_service.calculate_all_scores()
        logger.info("Calculated contribution scores.")

    return _run_job("calculate_scores", job, db_session)


def increment_membership_days(db_session: Session | None = None) -> bool:
    """
    Increment days in clan for active members.

    Args:
        db_session: Optional SQLAlchemy session. If None, a new session is created.

    Returns:
        bool: True on success or an applicable daily skip; False on a caught failure or
        lock contention.
    """

    def job(db: Session) -> None:
        """
        Increment the 'days_in_clan' field for all active members.

        Args:
            db: SQLAlchemy database session.

        Returns:
            None.
        """
        member_service = MemberService(db)
        member_service.increment_days_in_clan()
        logger.info("Incremented membership days.")

    return _run_job("increment_membership_days", job, db_session)


def send_daily_report(db_session: Session | None = None) -> bool:
    """
    Generate and send the daily clan activity report to Discord.

    Args:
        db_session: Optional SQLAlchemy session. If None, a new session is created.

    Returns:
        bool: True on success or an applicable daily skip; False on a caught failure or
        lock contention.
    """

    def job(db: Session) -> None:
        """
        Generate the daily clan activity report and send it to Discord.

        Args:
            db: SQLAlchemy database session.

        Returns:
            None.
        """
        reporter = DiscordReporter(db)
        report = reporter.generate_activity_report()

        bot = DiscordBot()
        if bot.webhook_url:
            if not bot.send_notification(report):
                raise RuntimeError("Discord report was not sent.")
            logger.info("Daily Discord report sent.")
        else:
            logger.info("Discord webhook not configured; skipping report.")

    return _run_job("send_daily_report", job, db_session, daily=True)


def backup_database(db_session: Session | None = None) -> bool:
    """
    Create a timestamped database backup.

    Args:
        db_session: Optional SQLAlchemy session. If None, a new session is created.

    Returns:
        bool: True on success or an applicable daily skip; False on a caught failure or
        lock contention.
    """

    def job(_db: Session) -> None:
        """
        Create a timestamped backup of the database.

        Args:
            _db: SQLAlchemy database session (not used in this job).

        Returns:
            None.
        """
        if run_database_backup() is None:
            raise RuntimeError("No database backup was created.")
        logger.info("Database backup completed.")

    return _run_job("backup_database", job, db_session, daily=True)
