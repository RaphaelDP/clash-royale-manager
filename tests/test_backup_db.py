"""
================================================================================
Filename: test_backup_db.py
Description: Unit tests for the SQLite backup script.
Author: Raphael Smilet
Date Created: 2026-08-06
Last Modified: 2026-08-06
Version: 0.1.0
Python Version: 3.12
Dependencies: pytest, pytest-mock, sqlite3, scripts.backup_db
================================================================================
"""

import sqlite3
from pathlib import Path

from scripts.backup_db import backup_database, _sqlite_path_from_url, _prune_old_backups


def test_sqlite_path_from_url_parses_sqlite_url():
    """Test that _sqlite_path_from_url correctly extracts the path from a SQLite URL."""
    assert _sqlite_path_from_url("sqlite:///data/clan_manager.db") == Path(
        "data/clan_manager.db"
    )


def test_sqlite_path_from_url_returns_none_for_non_sqlite():
    """Test that _sqlite_path_from_url returns None for non-SQLite URLs."""
    assert _sqlite_path_from_url("postgresql://user:pass@host/db") is None


def test_backup_database_creates_backup_file(tmp_path, mocker):
    """Test that backup_database creates a backup file in the expected location."""
    db_path = tmp_path / "data" / "test.db"
    db_path.parent.mkdir()
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE t (id INTEGER)")
    conn.commit()
    conn.close()

    backup_dir = tmp_path / "backups"

    mocker.patch("scripts.backup_db.settings.DATABASE_URL", f"sqlite:///{db_path}")
    mocker.patch("scripts.backup_db.BACKUP_DIR", backup_dir)

    result = backup_database()

    assert result is not None
    assert result.exists()
    assert result.parent == backup_dir


def test_backup_database_returns_none_for_missing_source(mocker, tmp_path):
    """Test that backup_database returns None when the source database does not exist."""
    missing_path = tmp_path / "data" / "does_not_exist.db"
    mocker.patch("scripts.backup_db.settings.DATABASE_URL", f"sqlite:///{missing_path}")

    assert backup_database() is None


def test_backup_database_returns_none_for_non_sqlite_url(mocker):
    """Test that backup_database returns None for non-SQLite database URLs."""
    mocker.patch(
        "scripts.backup_db.settings.DATABASE_URL", "postgresql://user:pass@host/db"
    )

    assert backup_database() is None


def test_prune_old_backups_keeps_only_retention_count(tmp_path, mocker):
    """Test that _prune_old_backups keeps only the specified number of backups."""
    mocker.patch("scripts.backup_db.BACKUP_RETENTION_COUNT", 2)

    for i in range(5):
        (tmp_path / f"test_2026010{i}_000000.db").write_text("x")

    _prune_old_backups(tmp_path, "test")

    remaining = list(tmp_path.glob("test_*.db"))
    assert len(remaining) == 2
