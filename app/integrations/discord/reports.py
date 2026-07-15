"""
================================================================================
Filename: reports.py
Description: Generate Discord reports for clan activity and wars.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-07-12
Version: 0.2.0
Python Version: 3.12
Dependencies: app.services.dashboard_service, app.core.constants
================================================================================
"""

from datetime import datetime

from app.core.constants import INACTIVE_DAYS, KICK_CANDIDATE_DAYS
from app.core.logger import logger
from app.services.dashboard_service import DashboardService

MAX_LISTED_MEMBERS = 10


class DiscordReporter:
    """
    Generator for Discord reports on clan activity, wars, and promotions.
    """

    def __init__(self, db_session):
        """
        Initialize the DiscordReporter with a database session.

        Args:
            db_session: SQLAlchemy database session for fetching report data.
        """
        self.db = db_session
        self.dashboard_service = DashboardService(db_session)

    def _format_member_list(self, members: list[dict]) -> str:
        names = ", ".join(m["name"] for m in members[:MAX_LISTED_MEMBERS])
        if len(members) > MAX_LISTED_MEMBERS:
            names += " ..."
        return f"    {names}"

    def generate_activity_report(self) -> str:
        """
        Generate a formatted daily activity report for Discord.

        Returns:
            str: Formatted report string, including:
                - Active members count and Clan Health Score.
                - Members inactive INACTIVE_DAYS+ (7+) days.
                - Members inactive KICK_CANDIDATE_DAYS+ (21+) days - a
                  simple activity-based list, NOT the future score-based
                  kick candidate system planned for v0.8.0, which isn't
                  implemented yet.
        """
        overview = self.dashboard_service.get_overview_stats()
        health = self.dashboard_service.get_clan_health_score()

        inactive_members = self.dashboard_service.get_inactive_members(INACTIVE_DAYS)
        long_inactive_members = self.dashboard_service.get_inactive_members(
            KICK_CANDIDATE_DAYS
        )

        lines = [
            f"**📊 Daily Clan Report — {datetime.now().strftime('%Y-%m-%d')}**",
            "",
            f"👥 Members: {overview['member_count']} ({overview['active_members']} active)",
            f"🩺 Clan Health: {health['final_score']:.1f} / 100",
            "",
            f"🚨 Inactive {INACTIVE_DAYS}+ days: {len(inactive_members)}",
        ]

        if inactive_members:
            lines.append(self._format_member_list(inactive_members))

        lines.append(
            f"⛔ Inactive {KICK_CANDIDATE_DAYS}+ days: {len(long_inactive_members)}"
        )

        if long_inactive_members:
            lines.append(self._format_member_list(long_inactive_members))

        report = "\n".join(lines)
        logger.info("Generated daily activity report.")
        return report
