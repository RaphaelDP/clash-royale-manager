"""
================================================================================
Filename: restore_db.py
Description: Validate and restore SQLite backups without changing the source backup.
Author: Raphael Smilet
Date Created: 2026-09-30
Last Modified: 2026-10-01
Version: 0.1.1
Python Version: 3.12
================================================================================
"""

from contextlib import closing
import argparse
import os
from pathlib import Path
import sqlite3
import tempfile


def restore_database(source: Path, destination: Path, *, replace=False):
    """
    Validate and copy a backup; call only while application processes are stopped.

    Args:
        source: Path to the SQLite backup, opened read-only.
        destination: Output path for the generated archive or restored database.
        replace: Allow replacing an existing destination after all app processes
            stop.

    Returns:
        Path: Destination containing the validated restored SQLite database.

    Raises:
        FileNotFoundError: The source backup is missing.
        FileExistsError: The destination exists without replace=True.
        ValueError: Source and destination match or backup integrity fails.
        RuntimeError: Destination SQLite sidecar files are present.
        sqlite3.DatabaseError: The source is not a readable SQLite database.
    """
    source, destination = source.resolve(), destination.absolute()
    if source == destination:
        raise ValueError("Source and destination must differ.")
    if destination.exists() and not replace:
        raise FileExistsError(
            "Destination exists; explicitly pass --replace after stopping the app."
        )
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".restore-", dir=destination.parent)
    os.close(descriptor)
    try:
        with closing(
            sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)
        ) as original:
            if original.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Backup integrity check failed.")
            copied = sqlite3.connect(temporary)
            try:
                original.backup(copied)
            finally:
                copied.close()
        # Refuse sidecars rather than replacing a potentially open WAL database.
        if any(
            Path(str(destination) + suffix).exists()
            for suffix in ("-wal", "-shm", "-journal")
        ):
            raise RuntimeError(
                "Database sidecars exist; stop the app and resolve them before restoring."
            )
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return destination


def main():
    """
    Parse explicit source and destination paths and restore a stopped database.

    Args:
        None.

    Returns:
        None.
    """
    parser = argparse.ArgumentParser(
        description="Restore a stopped SQLite application from backup."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    print(restore_database(args.source, args.destination, replace=args.replace))


if __name__ == "__main__":
    main()
