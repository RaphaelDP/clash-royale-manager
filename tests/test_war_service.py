"""
================================================================================
Filename: test_war_service.py
Description: Unit tests for the WarService class.
Author: Raphael Smilet
Date Created: 2026-06-17
Last Modified: 2026-06-18
Version: 0.4.0
Python Version: 3.12
Dependencies: pytest, app.services.war_service
================================================================================
"""

from datetime import datetime

import pytest

from app.core.utils import convert_timestamp_to_datetime
from app.database.models import (
    WarSeason,
    RiverRace,
    WarParticipation,
)


def test_create_or_update_season(db_session, war_service):
    """Verify a season is created only once."""

    season = war_service._create_or_update_season(
        "132",
        datetime(2026, 6, 1),
    )

    assert season.season_id == "132"

    same_season = war_service._create_or_update_season(
        "132",
        datetime(2026, 6, 1),
    )

    assert same_season.id == season.id

    seasons = db_session.query(WarSeason).all()

    assert len(seasons) == 1

    assert season.start_date == datetime(2026, 6, 1)
    assert same_season.start_date == datetime(2026, 6, 1)


def test_create_or_update_river_race(db_session, war_service):
    """Verify a river race is created only once."""

    season = war_service._create_or_update_season(
        "132",
        datetime(2026, 6, 1),
    )

    race = war_service._create_or_update_river_race(
        season_id=season.season_id,
        section_index=0,
        created_date=datetime(2026, 6, 8, 9, 34, 43),
    )

    assert race.season_id == "132"
    assert race.section_index == 0

    same_race = war_service._create_or_update_river_race(
        season_id=season.season_id,
        section_index=0,
        created_date=datetime(2026, 6, 8, 9, 34, 43),
    )

    assert same_race.id == race.id

    races = db_session.query(RiverRace).all()

    assert len(races) == 1
    assert race.created_date == datetime(2026, 6, 8, 9, 34, 43)
    assert same_race.created_date == datetime(2026, 6, 8, 9, 34, 43)


def test_create_or_update_participation(
    db_session,
    war_service,
    member_factory,
):
    """Verify participation is created then updated."""

    member = member_factory(
        tag="#PLAYER1",
        name="Player 1",
    )
    db_session.add(member)
    db_session.flush()

    season = war_service._create_or_update_season(
        "132",
        datetime(2026, 6, 1),
    )

    race = war_service._create_or_update_river_race(
        season_id=season.season_id,
        section_index=0,
        created_date=datetime(2026, 6, 8, 9, 34, 43),
    )

    participation = war_service._create_or_update_participation(
        river_race_id=race.id,
        member_tag=member.tag,
        fame=100,
        repair_points=10,
        boat_attacks=5,
        decks_used=3,
        decks_used_today=2,
    )

    assert participation.member_tag == member.tag
    assert participation.fame == 100
    assert participation.river_race_id == race.id
    assert participation.member_tag == member.tag

    updated = war_service._create_or_update_participation(
        river_race_id=race.id,
        member_tag=member.tag,
        fame=150,
        repair_points=15,
        boat_attacks=6,
        decks_used=4,
        decks_used_today=3,
    )

    assert updated.id == participation.id
    assert updated.fame == 150
    assert updated.repair_points == 15
    assert updated.boat_attacks == 6
    assert updated.decks_used == 4
    assert updated.decks_used_today == 3

    participations = db_session.query(WarParticipation).all()

    assert len(participations) == 1

    saved = db_session.query(WarParticipation).filter_by(member_tag=member.tag).one()

    assert saved.fame == 150
    assert saved.repair_points == 15
    assert saved.boat_attacks == 6
    assert saved.decks_used == 4
    assert saved.decks_used_today == 3


def test_sync_river_race_log(
    db_session,
    war_service,
    mocker,
    mock_river_race_log_with_standings,
    test_members,
):
    """Verify river race history is synchronized."""

    mocker.patch.object(
        war_service.api_client,
        "get_river_race_log",
        return_value=mock_river_race_log_with_standings,
    )

    war_service.sync_river_race_log("#TEST123")

    seasons = db_session.query(WarSeason).all()
    season = seasons[0]

    assert season.season_id == "132"
    assert season.start_date == convert_timestamp_to_datetime("20260608T093443.000Z")
    assert len(seasons) == 1

    races = db_session.query(RiverRace).all()
    race = races[0]

    assert race.season_id == "132"
    assert race.section_index == 0
    assert race.created_date == convert_timestamp_to_datetime("20260608T093443.000Z")
    assert len(races) == 1

    participations = db_session.query(WarParticipation).all()

    assert len(participations) == 2

    assert {p.member_tag for p in participations} == {
        "#TEST_PLAYER1",
        "#TEST_PLAYER2",
    }

    player1 = (
        db_session.query(WarParticipation).filter_by(member_tag="#TEST_PLAYER1").one()
    )

    assert player1.fame == 100
    assert player1.repair_points == 10
    assert player1.boat_attacks == 5
    assert player1.decks_used == 3
    assert player1.decks_used_today == 2

    player2 = (
        db_session.query(WarParticipation).filter_by(member_tag="#TEST_PLAYER2").one()
    )

    assert player2.fame == 200
    assert player2.repair_points == 20
    assert player2.boat_attacks == 8
    assert player2.decks_used == 5
    assert player2.decks_used_today == 3


def test_sync_river_race_log_twice_no_duplicates(
    db_session, war_service, mocker, mock_river_race_log_with_standings, test_members
):
    """Verify running sync twice does not create duplicates."""

    mocker.patch.object(
        war_service.api_client,
        "get_river_race_log",
        return_value=mock_river_race_log_with_standings,
    )

    war_service.sync_river_race_log("#TEST123")
    war_service.sync_river_race_log("#TEST123")

    seasons = db_session.query(WarSeason).all()
    races = db_session.query(RiverRace).all()
    participations = db_session.query(WarParticipation).all()

    assert len(seasons) == 1
    assert len(races) == 1
    assert len(participations) == 2
    assert (
        db_session.query(WarParticipation).filter_by(member_tag="#TEST_PLAYER1").count()
        == 1
    )

    assert (
        db_session.query(WarParticipation).filter_by(member_tag="#TEST_PLAYER2").count()
        == 1
    )


def test_sync_river_race_log_clan_not_found(
    db_session,
    war_service,
    mocker,
):
    """Verify no data is stored if the clan is absent from standings."""

    mock_data = {
        "items": [
            {
                "seasonId": "132",
                "sectionIndex": 0,
                "createdDate": "20260608T093443.000Z",
                "standings": [
                    {
                        "rank": 1,
                        "clan": {
                            "tag": "#OTHER_CLAN",
                            "participants": [],
                        },
                    }
                ],
            }
        ]
    }

    mocker.patch.object(
        war_service.api_client,
        "get_river_race_log",
        return_value=mock_data["items"],
    )

    war_service.sync_river_race_log("#TEST123")

    assert db_session.query(WarSeason).count() == 1
    assert db_session.query(RiverRace).count() == 1
    assert db_session.query(WarParticipation).count() == 0

    season = db_session.query(WarSeason).one()
    assert season.season_id == "132"

    race = db_session.query(RiverRace).one()
    assert race.section_index == 0


def test_sync_river_race_log_rollback(
    db_session,
    war_service,
    mocker,
):
    """Verify database rollback occurs on API failure."""

    mocker.patch.object(
        war_service.api_client,
        "get_river_race_log",
        side_effect=Exception("API Error"),
    )

    with pytest.raises(Exception, match="API Error"):
        war_service.sync_river_race_log("#TEST123")

    assert db_session.query(WarSeason).count() == 0
    assert db_session.query(RiverRace).count() == 0
    assert db_session.query(WarParticipation).count() == 0


def test_sync_current_river_race(
    db_session, war_service, mocker, mock_current_river_race, test_members
):
    """Verify current river race data is synchronized."""

    war_service._create_or_update_season(
        "132",
        datetime(2026, 6, 1),
    )

    mock_get_current_river_race = mocker.patch.object(
        war_service.api_client,
        "get_current_river_race",
        return_value=mock_current_river_race,
    )

    war_service.sync_current_river_race("#TEST123")

    races = db_session.query(RiverRace).all()

    assert len(races) == 1
    assert races[0].section_index == 2

    participations = db_session.query(WarParticipation).all()

    assert len(participations) == 2

    player1 = (
        db_session.query(WarParticipation).filter_by(member_tag="#TEST_PLAYER1").one()
    )

    assert player1.fame == 50
    assert player1.repair_points == 5
    assert player1.boat_attacks == 1
    assert player1.decks_used == 1
    assert player1.decks_used_today == 1
    assert player1.river_race_id == races[0].id

    player2 = (
        db_session.query(WarParticipation).filter_by(member_tag="#TEST_PLAYER2").one()
    )

    assert player2.fame == 75
    assert player2.repair_points == 7
    assert player2.boat_attacks == 2
    assert player2.decks_used == 2
    assert player2.decks_used_today == 2
    assert player2.river_race_id == races[0].id

    mock_get_current_river_race.assert_called_once_with("#TEST123")

    season = db_session.query(WarSeason).one()
    assert len(season.river_races) == 1

    race = season.river_races[0]
    assert len(race.war_participations) == 2


def test_sync_current_river_race_no_season(
    db_session,
    war_service,
    mocker,
    mock_current_river_race,
):
    """Verify current race sync is skipped if no season exists."""

    mocker.patch.object(
        war_service.api_client,
        "get_current_river_race",
        return_value=mock_current_river_race,
    )

    war_service.sync_current_river_race("#TEST123")

    assert db_session.query(RiverRace).count() == 0
    assert db_session.query(WarParticipation).count() == 0
