"""
================================================================================
Filename: collect_data.py
Description: Script to collect and sync data from the Clash Royale API.
Author: Raphael Smilet
Date Created: 2026-07-03
Last Modified: 2026-07-03
Version: 0.5.0
Python Version: 3.12
Dependencies: app.services.clan_service, app.services.war_service, app.database.session
================================================================================
"""


from app.database.session import SessionLocal
from app.services.clan_service import ClanService
from app.services.war_service import WarService
from app.core.config import settings
from app.core.logger import logger

def main():
    """Sync clan members and war data."""
    db = SessionLocal()

    try:
        # Sync clan members
        clan_service = ClanService(db)
        clan_service.sync_clan_members(settings.CLAN_TAG)
        logger.info("Synced clan members.")

        # Sync river race log
        war_service = WarService(db)
        war_service.sync_river_race_log(settings.CLAN_TAG)
        logger.info("Synced river race log.")

        # Sync current river race
        war_service.sync_current_river_race(settings.CLAN_TAG)
        logger.info("Synced current river race.")
    except Exception as e:
        logger.error("Failed to sync data: %s", e)
    finally:
        db.close()

if __name__ == "__main__":
    main()