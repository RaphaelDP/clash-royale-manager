"""
Filename: smoke_standalone.py
Description: Verify an extracted standalone runtime with isolated data and no API calls.
Author: Raphael Smilet
Date Created: 2026-10-07
Last Modified: 2026-10-15
Version: 0.1.1
"""

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import socket
import shutil
import sys
import sqlite3
import tempfile
import time

from launch.native_backend import NativeBackend
from app.services.scheduler_config import DEFAULT_SCHEDULE


def cleanup(backend, directory, failed):
    """Stop owned processes before removing data, preserving any original failure.

    Args:
        backend: Application backend owning the test supervisor.
        directory: Temporary test directory to remove after shutdown.
        failed: Whether an earlier test exception is already propagating.

    Returns:
        None. Reports retained files; raises cleanup errors only without an earlier error.
    """
    try:
        backend.stop()
    except Exception:
        print(f"Shutdown incomplete; isolated test data retained at {directory}.")
        if not failed:
            raise
    else:
        try:
            shutil.rmtree(directory)
        except OSError as error:
            print(f"Test cleanup incomplete: {error}")
            if not failed:
                raise


def main():
    """Check startup, dashboard resume, persistence and shutdown without user data.

    Args:
        None. Requires the standalone bundle path.

    Returns:
        None. Raises if any lifecycle assertion fails.
    """
    parser = argparse.ArgumentParser(description="Isolated standalone lifecycle check.")
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    os.environ.update(
        CLAN_SKIP_STARTUP_COLLECTION="1",
        PYTHON_DOTENV_DISABLED="1",
        CR_API_TOKEN="test",
        CLAN_TAG="#TEST",
        DISCORD_WEBHOOK_URL="",
        DATABASE_URL="sqlite:///data/clan_manager.db",
        LOG_FILE="logs/clan_manager.log",
    )
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    directory = tempfile.mkdtemp(prefix="clan-native-smoke-")
    try:
        backend = NativeBackend(args.bundle, Path(directory), port)
        schedule = dict(DEFAULT_SCHEDULE, enabled=False)
        (backend.root / "data/scheduler.json").write_text(
            json.dumps(schedule), encoding="utf-8"
        )
        (backend.root / ".env").write_text(
            "CR_API_TOKEN=test\nCLAN_TAG=#TEST\n", encoding="utf-8"
        )
        try:
            backend.start()
            database = backend.root / "data/clan_manager.db"
            with closing(sqlite3.connect(database)) as connection:
                connection.execute("CREATE TABLE acceptance_marker (value TEXT)")
                connection.execute("INSERT INTO acceptance_marker VALUES ('preserved')")
                connection.commit()
            (backend.control / "request.json").write_text(
                json.dumps({"mode": "dashboard", "not_before": time.time()}),
                encoding="utf-8",
            )
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                with socket.socket() as probe:
                    if probe.connect_ex(("127.0.0.1", port)) != 0:
                        break
                time.sleep(0.2)
            else:
                raise AssertionError("Dashboard-only close did not release the port.")
            assert backend.alive(), "Scheduler supervisor did not survive."
            backend.start()
            backend.stop()
            assert not backend.alive()
            backend.start()
            with closing(sqlite3.connect(database)) as connection:
                assert connection.execute(
                    "SELECT value FROM acceptance_marker"
                ).fetchone() == ("preserved",)
            backend.stop()
            with socket.socket() as probe:
                assert probe.connect_ex(("127.0.0.1", port)) != 0
            print(
                "Standalone lifecycle passed: startup, dashboard resume, persistent data, full shutdown."
            )
        except Exception:
            log = backend.root / "logs/desktop-startup.log"
            if log.exists():
                print(log.read_text(encoding="utf-8", errors="replace")[-12000:])
            raise
        finally:
            cleanup(backend, directory, failed=sys.exc_info()[0] is not None)
    finally:
        if Path(directory).exists():
            print(f"Test files remain at {directory}.")


if __name__ == "__main__":
    main()
