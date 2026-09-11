"""
================================================================================
Filename: config.py
Description: Centralized configuration settings for the application, loaded from environment variables.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-06
Version: 0.1.0
Python Version: 3.11
Dependencies: python-dotenv
================================================================================
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """
    Centralized application configuration.

    Loads runtime settings from environment variables and provides
    default values when not explicitly defined.

    Configuration domains:
        - Clash Royale API credentials
        - Database connection settings
        - Logging configuration
        - Scheduler settings

    Environment variables:
        CR_API_TOKEN: Clash Royale API authentication token.
        CLAN_TAG: Target clan tag to monitor.
        DATABASE_URL: Database connection URL.
        LOG_LEVEL: Logging verbosity level.
        LOG_FILE: Path to the application log file.
        SCHEDULER_TIMEZONE: Timezone used by scheduled jobs.
    """

    # Version
    VERSION = "0.5.1"

    # Clash Royale API
    CR_API_TOKEN = os.getenv("CR_API_TOKEN")

    CLAN_TAG = os.getenv("CLAN_TAG")

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/clan_manager.db")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/clan_manager.log")

    # Scheduler
    SCHEDULER_TIMEZONE = os.getenv("SCHEDULER_TIMEZONE", "Europe/Paris")

    # Discord Webhook URL
    DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


settings = Settings()


def validate_required_config() -> list[str]:
    """
    Returns the names of required settings that are missing or blank.
    Used by the dashboard to show a clear error message instead of a
    confusing downstream failure (e.g. a 403 from the Clash Royale API)
    when someone hasn't filled in their .env yet.

    DISCORD_WEBHOOK_URL is deliberately excluded - it's optional by
    design (Discord notifications are disabled when blank, not an error).
    """
    required = {
        "CR_API_TOKEN": settings.CR_API_TOKEN,
        "CLAN_TAG": settings.CLAN_TAG,
    }
    return [name for name, value in required.items() if not value]
