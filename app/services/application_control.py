"""
================================================================================
Filename: application_control.py
Description: Exchange shutdown requests with the application's owning supervisor.
Author: Raphael Smilet
Date Created: 2026-10-05
Last Modified: 2026-10-06
Version: 0.1.1
Python Version: 3.12
================================================================================
"""

import json
import os
from pathlib import Path
import tempfile
import time

CONTROL_ENV = "CLAN_CONTROL_DIR"
MODES = {"dashboard", "all"}


def control_available() -> bool:
    """Check whether this dashboard has a recently active owning supervisor.

    Args:
        None.

    Returns:
        bool: True when an inherited control directory has a recent heartbeat.
    """
    directory = os.getenv(CONTROL_ENV)
    if not directory:
        return False
    try:
        age = time.time() - (Path(directory) / "heartbeat").stat().st_mtime
        return 0 <= age < 10
    except OSError:
        return False


def request_shutdown(mode: str) -> None:
    """Atomically submit a confirmed request to this instance's supervisor.

    Args:
        mode: dashboard to stop only the web server, or all to stop both children.

    Returns:
        None.

    Raises:
        ValueError: The requested mode is unsupported.
        RuntimeError: The owning supervisor is unavailable.
        OSError: The request could not be written.
    """
    if mode not in MODES:
        raise ValueError("Unsupported shutdown mode.")
    if not control_available():
        raise RuntimeError(
            "Supervisor unavailable. Start with python -m scripts.run_app."
        )
    directory = Path(os.environ[CONTROL_ENV])
    descriptor, temporary = tempfile.mkstemp(prefix=".request-", dir=directory)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump({"mode": mode, "not_before": time.time() + 3}, output)
        os.replace(temporary, directory / "request.json")
    finally:
        Path(temporary).unlink(missing_ok=True)


def pending_shutdown(directory: Path) -> str | None:
    """Read a due request, allowing the UI time to display its acknowledgement.

    Args:
        directory: Private control directory created by the supervisor.

    Returns:
        str | None: A validated due mode, or None for absent/not-yet-due requests.
    """
    path = directory / "request.json"
    try:
        request = json.loads(path.read_text(encoding="utf-8"))
        mode = request["mode"]
        due = float(request["not_before"])
        if mode not in MODES:
            raise ValueError("Invalid shutdown mode")
        if time.time() < due:
            return None
    except FileNotFoundError:
        return None
    except (ValueError, TypeError, KeyError):
        path.unlink(missing_ok=True)
        return None
    path.unlink(missing_ok=True)
    return mode


def request_dashboard_start():
    """Ask the live container supervisor to reopen its dashboard without stopping jobs.

    Args:
        None. The container has one supervisor with a private temporary directory.

    Returns:
        None. During initial collection there is no supervisor yet and no request is needed.
    """
    for directory in Path(tempfile.gettempdir()).glob("clan-control-*"):
        try:
            age = time.time() - (directory / "heartbeat").stat().st_mtime
            if 0 <= age < 10:
                (directory / "resume-dashboard").touch()
        except FileNotFoundError:
            continue
