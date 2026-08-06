"""
================================================================================
Filename: backup_db.py
Description: Creates a timestamped hot backup of the SQLite database and
    prunes old backups beyond the configured retention count.
Author: Raphael Smilet
Date Created: 2026-08-06
Last Modified: 2026-08-06
Version: 0.1.0
Python Version: 3.12
Dependencies: sqlite3, app.core.config, app.core.constants
================================================================================
"""

import sqlite3
from pathlib import Path

from app.core.config import settings
from app.core.constants import BACKUP_RETENTION_COUNT
from app.core.logger import logger
from app.core.utils import get_time

BACKUP_DIR = Path("backups")


def _sqlite_path_from_url(database_url: str) -> Path | None:
    """
    Extracts the filesystem path from a SQLite SQLAlchemy URL
    (e.g. 'sqlite:///data/clan_manager.db' -> Path('data/clan_manager.db')).
    Returns None for non-SQLite URLs (e.g. Postgres) - this script only
    supports SQLite today.
    """
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return None
    return Path(database_url[len(prefix) :])


def _prune_old_backups(backup_dir: Path, stem: str) -> None:
    """
    Deletes backups beyond BACKUP_RETENTION_COUNT, oldest first. Sorted by
    filename rather than mtime - the timestamp format (YYYYMMDD_HHMMSS) is
    zero-padded, so lexicographic order already matches chronological
    order, and it avoids filesystem mtime-resolution flakiness.
    """
    backups = sorted(backup_dir.glob(f"{stem}_*.db"))

    excess = len(backups) - BACKUP_RETENTION_COUNT
    if excess <= 0:
        return

    for old_backup in backups[:excess]:
        old_backup.unlink()
        logger.info("Pruned old backup %s.", old_backup)


def backup_database() -> Path | None:
    """
    Creates a timestamped hot backup of the SQLite database using
    sqlite3's own backup API - safe even while the app is writing to the
    DB, unlike a raw file copy which can capture a torn/inconsistent
    snapshot.

    Returns:
        Path to the created backup file, or None if skipped (non-SQLite
        database, or the source file doesn't exist yet).
    """
    db_path = _sqlite_path_from_url(settings.DATABASE_URL)
    if db_path is None:
        logger.warning(
            "backup_database: DATABASE_URL is not SQLite, skipping (got %s).",
            settings.DATABASE_URL,
        )
        return None

    if not db_path.exists():
        logger.warning(
            "backup_database: source database %s does not exist yet.", db_path
        )
        return None

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = get_time().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"{db_path.stem}_{timestamp}.db"

    source_conn = sqlite3.connect(db_path)
    dest_conn = sqlite3.connect(backup_path)
    try:
        with dest_conn:
            source_conn.backup(dest_conn)
        logger.info("Database backed up to %s.", backup_path)
    finally:
        source_conn.close()
        dest_conn.close()

    _prune_old_backups(BACKUP_DIR, db_path.stem)

    return backup_path


if __name__ == "__main__":
    backup_database()
