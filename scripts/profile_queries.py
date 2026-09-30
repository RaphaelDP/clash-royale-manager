"""
================================================================================
Filename: profile_queries.py
Description: Measure dashboard and scoring queries against synthetic in-memory clan data.
Author: Raphael Smilet
Date Created: 2026-09-30
Last Modified: 2026-09-30
Version: 0.1.0
Python Version: 3.12
================================================================================
"""

from datetime import timedelta
from time import perf_counter
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from app.core.utils import get_time
from app.database.base import Base
from app.database.models import Member, WarSeason, RiverRace, WarParticipation
from app.services.dashboard_service import DashboardService
from app.services.score_service import ScoreService


def main():
    """Profile dashboard operations against a synthetic fifty-member clan."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        now = get_time()
        members = [
            Member(
                tag=f"#TEST{i}",
                name=f"Player {i}",
                role="member",
                trophies=5000 + i * 10,
                donations=100,
                last_seen=now,
                days_in_clan=30,
            )
            for i in range(50)
        ]
        season = WarSeason(season_id="test", start_date=now - timedelta(days=60))
        for week in range(8):
            race = RiverRace(
                war_season=season,
                section_index=week,
                created_date=now - timedelta(days=7 * (8 - week)),
                is_completed=True,
            )
            db.add_all(
                [
                    WarParticipation(
                        member=member, river_race=race, fame=2000 + i, decks_used=16
                    )
                    for i, member in enumerate(members)
                ]
            )
        db.commit()
        queries = [0]

        def count_query(*_args):
            queries[0] += 1

        event.listen(engine, "before_cursor_execute", count_query)
        dashboard = DashboardService(db, api_clash=object())
        for name, action in [
            ("overview_stats", dashboard.get_overview_stats),
            ("clan_health", dashboard.get_clan_health_score),
            ("recommendations", dashboard.get_promotion_recommendations),
            ("all_scores", ScoreService(db).calculate_all_scores),
        ]:
            queries[0] = 0
            started = perf_counter()
            action()
            print(
                f"{name}: {queries[0]} SQL statements, {perf_counter()-started:.3f}s (50 members / 8 races, synthetic)"
            )
    engine.dispose()


if __name__ == "__main__":
    main()
