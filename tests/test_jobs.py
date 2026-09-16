"""

Filename: test_jobs.py
Description: Unit tests for scheduled jobs and job execution state.
Author: Raphael Smilet
Date Created: 2026-09-11
Last Modified: 2026-09-11
Version: 0.9.1
Python Version: 3.12
Dependencies: pytest, app.scheduler.jobs, app.database.models
=============================================================

"""

from datetime import datetime

from app.database.models import JobRunState
from app.scheduler import jobs

# =============================================================================

# Job execution state

# =============================================================================


def test_get_job_state_creates_state(db_session):
    """Test that _get_job_state creates a state for a new job."""

    state = jobs._get_job_state(db_session, "test_job")

    assert state.job_name == "test_job"
    assert state.last_attempt_at is not None
    assert state.last_success_at is None
    assert state.last_error is None

    saved_state = db_session.query(JobRunState).filter_by(job_name="test_job").first()

    assert saved_state is state


def test_get_job_state_returns_existing_state(db_session):
    """Test that _get_job_state returns an existing state."""

    existing_state = JobRunState(
        job_name="test_job",
        last_attempt_at=datetime(2026, 9, 11, 10, 0, 0),
    )
    db_session.add(existing_state)
    db_session.commit()

    state = jobs._get_job_state(db_session, "test_job")

    assert state.id == existing_state.id
    assert state.job_name == "test_job"


def test_run_job_success(db_session):
    """Test that a successful job records its execution state."""

    def job(_db):
        return None

    result = jobs._run_job(
        "test_job",
        job,
        db_session,
    )

    assert result is True

    state = db_session.query(JobRunState).filter_by(job_name="test_job").first()

    assert state is not None
    assert state.last_attempt_at is not None
    assert state.last_success_at is not None
    assert state.last_error is None


def test_run_job_failure(db_session):
    """Test that a failed job records its error."""

    def job(_db):
        raise RuntimeError("Test job failure")

    result = jobs._run_job(
        "test_job",
        job,
        db_session,
    )

    assert result is False

    state = db_session.query(JobRunState).filter_by(job_name="test_job").first()

    assert state is not None
    assert state.last_attempt_at is not None
    assert state.last_success_at is None
    assert state.last_error == "Test job failure"


def test_run_job_clears_previous_error(db_session):
    """Test that a successful execution clears a previous error."""

    state = JobRunState(
        job_name="test_job",
        last_attempt_at=datetime(2026, 9, 11, 9, 0, 0),
        last_error="Previous failure",
    )
    db_session.add(state)
    db_session.commit()

    def job(_db):
        return None

    result = jobs._run_job(
        "test_job",
        job,
        db_session,
    )

    assert result is True

    state = db_session.query(JobRunState).filter_by(job_name="test_job").first()

    assert state.last_success_at is not None
    assert state.last_error is None


# =============================================================================

# Clan members

# =============================================================================


def test_update_clan_members(db_session, mocker):
    """Test the clan member synchronization job."""

    clan_service = mocker.patch("app.scheduler.jobs.ClanService")

    result = jobs.update_clan_members(db_session)

    assert result is True

    clan_service.return_value.sync_clan_members.assert_called_once_with(
        jobs.settings.CLAN_TAG
    )

    state = (
        db_session.query(JobRunState).filter_by(job_name="update_clan_members").first()
    )

    assert state.last_success_at is not None
    assert state.last_error is None


def test_update_clan_members_failure(db_session, mocker):
    """Test that clan synchronization failures are recorded."""

    clan_service = mocker.patch("app.scheduler.jobs.ClanService")
    clan_service.return_value.sync_clan_members.side_effect = RuntimeError("API Error")

    result = jobs.update_clan_members(db_session)

    assert result is False

    state = (
        db_session.query(JobRunState).filter_by(job_name="update_clan_members").first()
    )

    assert state.last_success_at is None
    assert state.last_error == "API Error"


# =============================================================================

# Wars

# =============================================================================


def test_update_war_data(db_session, mocker):
    """Test the war synchronization job."""

    war_service = mocker.patch("app.scheduler.jobs.WarService")

    result = jobs.update_war_data(db_session)

    assert result is True

    service = war_service.return_value

    service.sync_river_race_log.assert_called_once_with(jobs.settings.CLAN_TAG)
    service.sync_current_river_race.assert_called_once_with(jobs.settings.CLAN_TAG)

    state = db_session.query(JobRunState).filter_by(job_name="update_war_data").first()

    assert state.last_success_at is not None
    assert state.last_error is None


def test_update_war_data_failure(db_session, mocker):
    """Test that war synchronization failures are recorded."""

    war_service = mocker.patch("app.scheduler.jobs.WarService")
    war_service.return_value.sync_river_race_log.side_effect = RuntimeError(
        "War API Error"
    )

    result = jobs.update_war_data(db_session)

    assert result is False

    state = db_session.query(JobRunState).filter_by(job_name="update_war_data").first()

    assert state.last_success_at is None
    assert state.last_error == "War API Error"


# =============================================================================

# Snapshots

# =============================================================================


def test_create_daily_snapshots(db_session, mocker):
    """Test the daily snapshot job."""

    snapshot_service = mocker.patch("app.scheduler.jobs.SnapshotService")

    result = jobs.create_daily_snapshots(db_session)

    assert result is True

    snapshot_service.return_value.create_daily_snapshots.assert_called_once_with(None)

    state = (
        db_session.query(JobRunState)
        .filter_by(job_name="create_daily_snapshots")
        .first()
    )

    assert state.last_success_at is not None
    assert state.last_error is None


# =============================================================================

# Contribution scores

# =============================================================================


def test_calculate_scores(db_session, mocker):
    """Test the contribution score calculation job."""

    score_service = mocker.patch("app.scheduler.jobs.ScoreService")

    result = jobs.calculate_scores(db_session)

    assert result is True

    score_service.return_value.calculate_all_scores.assert_called_once_with()

    state = db_session.query(JobRunState).filter_by(job_name="calculate_scores").first()

    assert state.last_success_at is not None
    assert state.last_error is None


# =============================================================================

# Membership days

# =============================================================================


def test_increment_membership_days(db_session, mocker):
    """Test the membership days increment job."""

    member_service = mocker.patch("app.scheduler.jobs.MemberService")

    result = jobs.increment_membership_days(db_session)

    assert result is True

    member_service.return_value.increment_days_in_clan.assert_called_once_with()

    state = (
        db_session.query(JobRunState)
        .filter_by(job_name="increment_membership_days")
        .first()
    )

    assert state.last_success_at is not None
    assert state.last_error is None


# =============================================================================

# Discord report

# =============================================================================


def test_send_daily_report(db_session, mocker):
    """Test the daily Discord report job."""

    reporter = mocker.patch("app.scheduler.jobs.DiscordReporter")
    bot = mocker.patch("app.scheduler.jobs.DiscordBot")

    reporter.return_value.generate_activity_report.return_value = "Test report"
    bot.return_value.send_notification.return_value = True

    result = jobs.send_daily_report(db_session)

    assert result is True

    reporter.return_value.generate_activity_report.assert_called_once_with()
    bot.return_value.send_notification.assert_called_once_with("Test report")

    state = (
        db_session.query(JobRunState).filter_by(job_name="send_daily_report").first()
    )

    assert state.last_success_at is not None
    assert state.last_error is None


def test_send_daily_report_failure(db_session, mocker):
    """Test that a failed Discord report is recorded."""

    reporter = mocker.patch("app.scheduler.jobs.DiscordReporter")
    bot = mocker.patch("app.scheduler.jobs.DiscordBot")

    reporter.return_value.generate_activity_report.return_value = "Test report"
    bot.return_value.send_notification.return_value = False

    result = jobs.send_daily_report(db_session)

    assert result is False

    state = (
        db_session.query(JobRunState).filter_by(job_name="send_daily_report").first()
    )

    assert state.last_success_at is None
    assert state.last_error == "Discord report was not sent."


# =============================================================================

# Database backup

# =============================================================================


def test_backup_database(mocker):
    """Test the database backup job."""

    backup = mocker.patch("app.scheduler.jobs.run_database_backup")

    result = jobs.backup_database()

    assert result is True
    backup.assert_called_once_with()


def test_backup_database_failure(mocker):
    """Test that database backup failures are handled."""

    mocker.patch(
        "app.scheduler.jobs.run_database_backup",
        side_effect=RuntimeError("Backup Error"),
    )

    result = jobs.backup_database()

    assert result is False
