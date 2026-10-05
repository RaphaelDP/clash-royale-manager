"""
================================================================================
Filename: test_player_metrics.py
Description: Verify service-owned player metrics independently of dashboard rendering.
Author: Raphael Smilet
Date Created: 2026-10-02
Last Modified: 2026-10-02
Version: 0.1.0
Python Version: 3.12
================================================================================
"""

import pytest

from app.database.models import WarParticipation
from app.services.member_service import MemberService
from app.services.war_service import WarService


@pytest.mark.parametrize(
    "profile, expected",
    [
        ({}, 0.0),
        ({"wins": 0, "losses": 0, "battleCount": 10}, 0.0),
        ({"wins": 3, "losses": 1, "battleCount": 10}, 75.0),
        ({"wins": 1, "losses": 2}, 33.3),
    ],
)
def test_winrate_uses_decided_battles(profile, expected):
    """Keep draws out of win-rate calculations and handle absent results.

    Args:
        profile: Synthetic API profile, including optional draw-inclusive battle count.
        expected: Expected percentage rounded to one decimal place.

    Returns:
        None. Assertions verify the service's battle-count semantics.
    """
    assert MemberService.calculate_winrate(profile) == expected


@pytest.mark.parametrize("populated", [False, True])
def test_war_summary_retains_zero_deck_records(populated):
    """Distinguish the number of recorded races from attacks and decks used.

    Args:
        populated: Whether to supply an active record and a zero-deck record.

    Returns:
        None. Assertions verify totals and the empty-history fallback.
    """
    records = (
        [
            WarParticipation(fame=1200, boat_attacks=2, decks_used=4),
            WarParticipation(fame=0, boat_attacks=0, decks_used=0),
        ]
        if populated
        else []
    )
    assert WarService.summarize_participations(records) == {
        "count": 2 if populated else 0,
        "total_fame": 1200 if populated else 0,
        "total_boats": 2 if populated else 0,
        "total_decks": 4 if populated else 0,
    }
