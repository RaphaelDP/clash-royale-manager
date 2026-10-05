"""
================================================================================
Filename: observe_war_identity.py
Description: Collect sanitized live-war qualification evidence in an isolated process.
Author: Raphael Smilet
Date Created: 2026-10-02
Last Modified: 2026-10-05
Version: 0.1.2
Python Version: 3.12
================================================================================
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from dotenv import dotenv_values

# Application imports must occur only after the child runtime is isolated.
# Isolation settings deliberately mirror the credential-free test runner.
# pylint: disable=import-outside-toplevel,duplicate-code


def run_worker(confirm_season=None, confirm_section=None):
    """Collect one fresh sample using credentials and temporary runtime settings.

    Args:
        confirm_season: Optional expected season to confirm using fresh API history.
        confirm_section: Expected section, supplied together with confirm_season.

    Returns:
        dict: Sanitized observation or failure type; no credentials or player data.
    """
    if (
        os.getenv("PYTHON_DOTENV_DISABLED") != "1"
        or os.getenv("DATABASE_URL") != "sqlite:///:memory:"
        or os.getenv("DISCORD_WEBHOOK_URL") != ""
    ):
        return {"ok": False, "error_type": "IsolationRequired"}

    from sqlalchemy.orm import Session
    from app.core.config import settings, validate_required_config
    from app.core.logger import logger
    from app.database.base import Base
    from app.database.session import engine
    from app.services.clash_api import ClashAPIClient
    from app.services.war_service import WarService

    logger.disabled = True
    client = None
    try:
        if validate_required_config():
            return {"ok": False, "error_type": "MissingConfiguration"}
        Base.metadata.create_all(engine)
        client = ClashAPIClient()
        with Session(engine) as db:
            return WarService(db, client).observe_identity(
                settings.CLAN_TAG, confirm_season, confirm_section
            )
    except Exception as error:  # Do not expose request URLs or response contents.
        return {"ok": False, "error_type": type(error).__name__}
    finally:
        if client is not None:
            client.session.close()
        engine.dispose()


def main():
    """Run one isolated sample and print a JSON line suitable for an evidence file.

    Args:
        None. The internal --worker flag is reserved for the isolated subprocess.

    Returns:
        int: Zero for success (and requested confirmation), one for collection failure,
        or three while confirmation is pending. Invalid CLI arguments exit with two.
    """
    parser = argparse.ArgumentParser(
        description="Print sanitized live-war identity evidence without changing runtime data."
    )
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--confirm-season", help="Season to confirm in completed API history."
    )
    parser.add_argument(
        "--confirm-section", type=int, help="Section to confirm with the season."
    )
    args = parser.parse_args()
    if args.confirm_season is not None or args.confirm_section is not None:
        if (
            not args.confirm_season
            or not args.confirm_season.strip()
            or args.confirm_section is None
            or args.confirm_section < 0
        ):
            parser.error(
                "Supply both a nonempty --confirm-season and nonnegative --confirm-section."
            )
    if args.worker:
        result = run_worker(args.confirm_season, args.confirm_section)
    else:
        root = Path(__file__).resolve().parents[1]
        configured = dotenv_values(root / ".env")
        env = dict(os.environ)
        for name in ("CR_API_TOKEN", "CLAN_TAG", "SCHEDULER_TIMEZONE"):
            if name not in env and configured.get(name) is not None:
                env[name] = configured[name]
        with tempfile.TemporaryDirectory(prefix="clan-war-observation-") as directory:
            env.update(
                PYTHON_DOTENV_DISABLED="1",
                PYTHONDONTWRITEBYTECODE="1",
                PYTHONPATH=str(root),
                DATABASE_URL="sqlite:///:memory:",
                DISCORD_WEBHOOK_URL="",
                LOG_FILE=str(Path(directory) / "observation.log"),
                SCHEDULER_CONFIG_FILE=str(Path(directory) / "scheduler.json"),
                JOB_LOCK_DIR=str(Path(directory) / "locks"),
            )
            command = [sys.executable, "-m", "scripts.observe_war_identity", "--worker"]
            if args.confirm_season is not None:
                command.extend(
                    [
                        "--confirm-season",
                        args.confirm_season,
                        "--confirm-section",
                        str(args.confirm_section),
                    ]
                )
            try:
                child = subprocess.run(
                    command,
                    cwd=directory,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=180,
                    check=False,
                )
                result = json.loads(child.stdout)
            except (subprocess.TimeoutExpired, ValueError):
                result = {"ok": False, "error_type": "ObservationProcessFailed"}
    print(json.dumps(result, sort_keys=True))
    if not result.get("ok"):
        return 1
    return 3 if result.get("confirmation", {}).get("status") == "pending" else 0


if __name__ == "__main__":
    raise SystemExit(main())
