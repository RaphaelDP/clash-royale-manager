"""
================================================================================
Filename: collect_data.py
Description: Script to collect and sync data from the Clash Royale API.
Author: Raphael Smilet
Date Created: 2026-07-03
Last Modified: 2026-07-11
Version: 0.6.0
Python Version: 3.12
Dependencies: app.services.clan_service, app.services.war_service, app.services.snapshot_service, app.services.score_service, app.database.session
================================================================================
"""

from app.database.session import SessionLocal
from app.services.clan_service import ClanService
from app.services.war_service import WarService
from app.services.snapshot_service import SnapshotService
from app.services.score_service import ScoreService
from app.core.config import settings
from app.core.logger import logger


def main():
    """Sync clan members, war data, snapshots, and promotion scores."""
    db = SessionLocal()

    try:
        clan_service = ClanService(db)
        clan_service.sync_clan_members(settings.CLAN_TAG)
        logger.info("Synced clan members.")

        war_service = WarService(db)
        war_service.sync_river_race_log(settings.CLAN_TAG)
        logger.info("Synced river race log.")

        war_service.sync_current_river_race(settings.CLAN_TAG)
        logger.info("Synced current river race.")

        snapshot_service = SnapshotService(db)
        snapshot_service.create_daily_snapshots(None)
        logger.info("Created daily snapshots.")

        score_service = ScoreService(db)
        score_service.calculate_all_scores()
        logger.info("Calculated promotion scores.")
    except Exception as e:
        logger.error("Failed to sync data: %s", e)
    finally:
        db.close()


if __name__ == "__main__":
    main()
