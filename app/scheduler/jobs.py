"""
================================================================================
Filename: jobs.py
Description: Scheduled jobs for data collection, updates, and analytics.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-07-12
Version: 0.2.0
Python Version: 3.12
Dependencies: app.services, app.integrations.discord, app.database.session
================================================================================
"""

from app.core.config import settings
from app.core.logger import logger
from app.database.session import SessionLocal
from app.services.clan_service import ClanService
from app.services.war_service import WarService
from app.services.snapshot_service import SnapshotService
from app.services.score_service import ScoreService
from app.integrations.discord.bot import DiscordBot
from app.integrations.discord.reports import DiscordReporter


def update_clan_members() -> None:
    """
    Scheduled job to fetch and update clan members from the Clash Royale API.
    Runs hourly to ensure member data (trophies, donations, roles) is up-to-date.
    """
    db = SessionLocal()
    try:
        clan_service = ClanService(db)
        clan_service.sync_clan_members(settings.CLAN_TAG)
        logger.info("[scheduler] Synced clan members.")
    except Exception as e:
        logger.error("[scheduler] Failed to sync clan members: %s", e)
    finally:
        db.close()


def update_war_data() -> None:
    """
    Scheduled job to sync the river race log and current river race.
    Runs hourly, since scoring, clan health, and the live race status view
    all depend on up-to-date war data.
    """
    db = SessionLocal()
    try:
        war_service = WarService(db)
        war_service.sync_river_race_log(settings.CLAN_TAG)
        war_service.sync_current_river_race(settings.CLAN_TAG)
        logger.info("[scheduler] Synced war data.")
    except Exception as e:
        logger.error("[scheduler] Failed to sync war data: %s", e)
    finally:
        db.close()


def create_daily_snapshots() -> None:
    """
    Scheduled job to create daily snapshots of all member data.
    Runs once per day to track historical trends in trophies, donations, and activity.
    """
    db = SessionLocal()
    try:
        snapshot_service = SnapshotService(db)
        snapshot_service.create_daily_snapshots(None)
        logger.info("[scheduler] Created daily snapshots.")
    except Exception as e:
        logger.error("[scheduler] Failed to create daily snapshots: %s", e)
    finally:
        db.close()


def calculate_scores() -> None:
    """
    Scheduled job to calculate promotion scores for all members.
    Runs once per day, after snapshots, to update scores based on the
    latest data.
    """
    db = SessionLocal()
    try:
        score_service = ScoreService(db)
        score_service.calculate_all_scores()
        logger.info("[scheduler] Calculated promotion scores.")
    except Exception as e:
        logger.error("[scheduler] Failed to calculate scores: %s", e)
    finally:
        db.close()


def send_daily_report() -> None:
    """
    Scheduled job to generate and send the daily clan activity report to
    Discord. Runs once per day, after snapshots and scores, so the report
    reflects fresh data.
    """
    db = SessionLocal()
    try:
        reporter = DiscordReporter(db)
        report = reporter.generate_activity_report()

        bot = DiscordBot()
        sent = bot.send_notification(report)

        if sent:
            logger.info("[scheduler] Daily Discord report sent.")
        else:
            logger.warning("[scheduler] Daily Discord report was not sent.")
    except Exception as e:
        logger.error("[scheduler] Failed to send daily report: %s", e)
    finally:
        db.close()
