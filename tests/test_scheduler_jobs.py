"""
================================================================================
Filename: test_scheduler_jobs.py
Description: Unit tests for scheduled jobs.
Author: Raphael Smilet
Date Created: 2026-07-12
Last Modified: 2026-07-12
Version: 0.1.0
Python Version: 3.12
Dependencies: pytest, pytest-mock, app.scheduler.jobs
================================================================================
"""

from app.scheduler import jobs


def test_update_clan_members_calls_clan_service(db_session, mocker):
    """ """
    mocker.patch("app.scheduler.jobs.SessionLocal", return_value=db_session)
    mock_clan_service = mocker.patch("app.scheduler.jobs.ClanService")

    jobs.update_clan_members()

    mock_clan_service.assert_called_once_with(db_session)
    mock_clan_service.return_value.sync_clan_members.assert_called_once()


def test_update_clan_members_handles_failure(db_session, mocker):
    mocker.patch("app.scheduler.jobs.SessionLocal", return_value=db_session)
    mock_clan_service = mocker.patch("app.scheduler.jobs.ClanService")
    mock_clan_service.return_value.sync_clan_members.side_effect = Exception("API down")

    jobs.update_clan_members()  # must not raise


def test_update_war_data_calls_war_service(db_session, mocker):
    mocker.patch("app.scheduler.jobs.SessionLocal", return_value=db_session)
    mock_war_service = mocker.patch("app.scheduler.jobs.WarService")

    jobs.update_war_data()

    mock_war_service.assert_called_once_with(db_session)
    mock_war_service.return_value.sync_river_race_log.assert_called_once()
    mock_war_service.return_value.sync_current_river_race.assert_called_once()


def test_create_daily_snapshots_calls_snapshot_service(db_session, mocker):
    mocker.patch("app.scheduler.jobs.SessionLocal", return_value=db_session)
    mock_snapshot_service = mocker.patch("app.scheduler.jobs.SnapshotService")

    jobs.create_daily_snapshots()

    mock_snapshot_service.assert_called_once_with(db_session)
    mock_snapshot_service.return_value.create_daily_snapshots.assert_called_once_with(
        None
    )


def test_calculate_scores_calls_score_service(db_session, mocker):
    mocker.patch("app.scheduler.jobs.SessionLocal", return_value=db_session)
    mock_score_service = mocker.patch("app.scheduler.jobs.ScoreService")

    jobs.calculate_scores()

    mock_score_service.assert_called_once_with(db_session)
    mock_score_service.return_value.calculate_all_scores.assert_called_once()


def test_send_daily_report_sends_when_generated(db_session, mocker):
    mocker.patch("app.scheduler.jobs.SessionLocal", return_value=db_session)
    mock_reporter_cls = mocker.patch("app.scheduler.jobs.DiscordReporter")
    mock_reporter_cls.return_value.generate_activity_report.return_value = "report text"

    mock_bot_cls = mocker.patch("app.scheduler.jobs.DiscordBot")
    mock_bot_cls.return_value.send_notification.return_value = True

    jobs.send_daily_report()

    mock_reporter_cls.return_value.generate_activity_report.assert_called_once()
    mock_bot_cls.return_value.send_notification.assert_called_once_with("report text")


def test_send_daily_report_handles_send_failure(db_session, mocker):
    mocker.patch("app.scheduler.jobs.SessionLocal", return_value=db_session)
    mock_reporter_cls = mocker.patch("app.scheduler.jobs.DiscordReporter")
    mock_reporter_cls.return_value.generate_activity_report.return_value = "report text"

    mock_bot_cls = mocker.patch("app.scheduler.jobs.DiscordBot")
    mock_bot_cls.return_value.send_notification.return_value = False

    jobs.send_daily_report()  # must not raise even when the send fails
