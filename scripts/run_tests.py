"""
================================================================================
Filename: run_tests.py
Description: Run the test suite without reading credentials or touching runtime data.
Author: Raphael Smilet
Date Created: 2026-09-30
Last Modified: 2026-09-30
Version: 0.1.0
Python Version: 3.12
================================================================================
"""

import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    """Run pytest in a temporary directory with isolated runtime settings."""
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="clan-manager-tests-") as directory:
        env = dict(os.environ)
        env.update(
            PYTHON_DOTENV_DISABLED="1",
            PYTHONDONTWRITEBYTECODE="1",
            PYTHONPATH=str(root),
            DATABASE_URL="sqlite:///:memory:",
            CR_API_TOKEN="test",
            CLAN_TAG="#TEST",
            DISCORD_WEBHOOK_URL="",
            LOG_FILE=str(Path(directory) / "test.log"),
            SCHEDULER_CONFIG_FILE=str(Path(directory) / "scheduler.json"),
            JOB_LOCK_DIR=str(Path(directory) / "locks"),
        )
        command = [
            sys.executable,
            "-m",
            "pytest",
            str(root / "tests"),
            "-o",
            f"cache_dir={directory}/pytest-cache",
            *sys.argv[1:],
        ]
        raise SystemExit(subprocess.call(command, cwd=directory, env=env))


if __name__ == "__main__":
    main()
