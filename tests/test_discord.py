"""
================================================================================
Filename: test_discord.py
Description: Unit tests for Discord integration (bot + reports).
Author: Raphael Smilet
Date Created: 2026-07-12
Last Modified: 2026-07-12
Version: 0.1.0
Python Version: 3.12
Dependencies: pytest, pytest-mock, app.integrations.discord
================================================================================
"""

from datetime import timedelta

import requests

from app.core.utils import get_time
from app.integrations.discord.bot import DiscordBot
from app.integrations.discord.reports import DiscordReporter

# =============================================================================
# DiscordBot
# =============================================================================


def test_send_notification_success(mocker):
    mock_response = mocker.MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_post = mocker.patch("requests.post", return_value=mock_response)

    bot = DiscordBot(webhook_url="https://discord.com/api/webhooks/fake")
    result = bot.send_notification("hello clan")

    assert result is True
    mock_post.assert_called_once()
    assert mock_post.call_args.kwargs["json"] == {"content": "hello clan"}


def test_send_notification_no_webhook_configured():
    bot = DiscordBot(webhook_url=None)

    assert bot.send_notification("hello") is False


def test_send_notification_network_failure(mocker):
    mocker.patch(
        "requests.post", side_effect=requests.exceptions.ConnectionError("down")
    )

    bot = DiscordBot(webhook_url="https://discord.com/api/webhooks/fake")

    assert bot.send_notification("hello") is False


def test_send_notification_truncates_long_messages(mocker):
    mock_response = mocker.MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_post = mocker.patch("requests.post", return_value=mock_response)

    bot = DiscordBot(webhook_url="https://discord.com/api/webhooks/fake")
    bot.send_notification("x" * 3000)

    sent_content = mock_post.call_args.kwargs["json"]["content"]
    assert len(sent_content) <= 2000
    assert sent_content.endswith("(truncated)")


# =============================================================================
# DiscordReporter
# =============================================================================


def test_generate_activity_report_includes_counts(db_session, member_factory):
    active = member_factory(name="Active", last_seen=get_time())
    inactive = member_factory(name="Ghost", last_seen=get_time() - timedelta(days=10))
    long_inactive = member_factory(
        name="Vanished", last_seen=get_time() - timedelta(days=25)
    )
    db_session.add_all([active, inactive, long_inactive])
    db_session.commit()

    reporter = DiscordReporter(db_session)
    report = reporter.generate_activity_report()

    assert "Ghost" in report
    assert "Vanished" in report
    assert "Members:" in report
