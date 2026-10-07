"""
Filename: smoke_standalone.py
Description: Verify an extracted standalone runtime with isolated data and no API calls.
Author: Raphael Smilet
Date Created: 2026-10-07
Last Modified: 2026-10-07
Version: 0.1.0
"""

import argparse
import json
import os
from pathlib import Path
import socket
import sqlite3
import tempfile
import time

from launch.native_backend import NativeBackend
from app.services.scheduler_config import DEFAULT_SCHEDULE


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
    with tempfile.TemporaryDirectory(prefix="clan-native-smoke-") as directory:
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
            with sqlite3.connect(database) as connection:
                connection.execute("CREATE TABLE acceptance_marker (value TEXT)")
                connection.execute("INSERT INTO acceptance_marker VALUES ('preserved')")
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
            with sqlite3.connect(database) as connection:
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
            backend.stop()


if __name__ == "__main__":
    main()
