"""
================================================================================
Filename: bot.py
Description: Sends clan notifications to Discord via an incoming webhook.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-07-12
Version: 0.2.0
Python Version: 3.12
Dependencies: requests
================================================================================
"""

import requests

from app.core.config import settings
from app.core.logger import logger

DISCORD_MESSAGE_LIMIT = 2000


class DiscordBot:
    """
    Lightweight Discord notifier using a Discord incoming webhook.

    This is intentionally NOT a full discord.py bot: it doesn't hold a
    persistent gateway connection and can't receive commands, only send
    one-way messages. That fits this project's actual need (scheduled
    digests, fire-and-forget alerts) without an extra dependency or a
    process that has to stay logged in.
    """

    def __init__(self, webhook_url: str | None = None):
        """
        Initialize the DiscordBot with a webhook URL.

        Args:
            webhook_url: Discord incoming webhook URL. Defaults to
                settings.DISCORD_WEBHOOK_URL if not provided.
        """
        self.webhook_url = webhook_url or settings.DISCORD_WEBHOOK_URL

    def send_notification(self, message: str) -> bool:
        """
        Send a notification message to the configured Discord channel.

        Args:
            message: The notification message to send. Discord caps
                message content at 2000 characters; longer messages are
                truncated with a note appended.

        Returns:
            bool: True if the notification was sent successfully (HTTP 2xx),
                False otherwise (no webhook configured, network error, or a
                non-2xx response).
        """
        if not self.webhook_url:
            logger.warning("No Discord webhook URL configured; notification not sent.")
            return False

        if len(message) > DISCORD_MESSAGE_LIMIT:
            message = message[: DISCORD_MESSAGE_LIMIT - 100] + "\n... (truncated)"

        try:
            response = requests.post(
                self.webhook_url,
                json={"content": message},
                timeout=10,
            )
            response.raise_for_status()
            logger.info("Discord notification sent successfully.")
            return True
        except requests.exceptions.RequestException as e:
            logger.error("Failed to send Discord notification: %s", e)
            return False
