"""
================================================================================
Filename: collect_data.py
Description: Script to manually collect and store clan data.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-06
Version: 0.2.1
Python Version: 3.12
Dependencies: app.services.clash_api, app.services.clan_service, app.database.session
================================================================================
"""

from app.core.config import settings
from app.core.logger import logger
from app.database.models.member import Member
from app.database.session import SessionLocal
from app.services.clan_service import ClanService


def collect_data() -> None:
    """
    Collect and store clan data from the Clash Royale API.
    """

    db = SessionLocal()

    try:
        clan_service = ClanService(db)

        members = clan_service.sync_clan_members(settings.CLAN_TAG)

        logger.info("Successfully synchronized %s members", len(members))

        print("\n=== Clan Members ===")

        for member in db.query(Member).all():
            print(
                f"{member.name} "
                f"({member.tag}) - "
                f"{member.trophies} trophies - "
                f"{member.donations} donations"
            )

    finally:
        db.close()


if __name__ == "__main__":
    collect_data()
