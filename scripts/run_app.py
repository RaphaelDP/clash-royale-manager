"""
================================================================================
Filename: run_app.py
Description: Supervise dashboard and scheduler with safe startup and graceful shutdown.
Author: Raphael Smilet
Date Created: 2026-09-30
Last Modified: 2026-10-07
Version: 0.2.0
Python Version: 3.12
================================================================================
"""

from contextlib import nullcontext
import os
from pathlib import Path
import signal
import tempfile
import subprocess
import sys
from threading import Event

from scripts.init_db import init_db
from scripts.collect_data import main as collect_data
from app.core.logger import logger
from app.core.job_lock import job_lock
from app.services.application_control import CONTROL_ENV, pending_shutdown


def main():
    """
    Upgrade and collect data, then supervise the dashboard and scheduler.

    Args:
        None.

    Returns:
        None.
    """
    with job_lock("supervisor_process") as acquired:
        if not acquired:
            raise RuntimeError("An application supervisor is already running.")
        run_supervisor()


def run_supervisor():
    """Initialize data and own dashboard/scheduler children until shutdown.

    Args:
        None.

    Returns:
        None.
    """
    init_db()  # Never launch against an incompatible schema.
    try:
        if os.getenv("CLAN_SKIP_STARTUP_COLLECTION") != "1":
            collect_data()
    except Exception:
        # Keep the dashboard available to inspect persisted sync failures.
        logger.exception("Initial collection failed; serving existing data.")
    stop = Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    desktop = os.getenv("CLAN_DESKTOP_CONTROL")
    # The selected context is entered immediately below.
    # pylint: disable=consider-using-with
    context = (
        nullcontext(desktop)
        if desktop
        else tempfile.TemporaryDirectory(prefix="clan-control-")
    )
    # pylint: enable=consider-using-with
    with context as directory:
        control = Path(directory)
        control.mkdir(parents=True, exist_ok=True, mode=0o700)
        (control / "request.json").unlink(missing_ok=True)
        (control / "resume-dashboard").unlink(missing_ok=True)
        (control / "heartbeat").touch()
        env = dict(os.environ, **{CONTROL_ENV: directory})
        processes = {}
        # Children are always terminated and reaped, including partial startup.
        # pylint: disable=consider-using-with
        try:
            processes["scheduler"] = subprocess.Popen(
                [sys.executable, "-m", "scripts.run_scheduler"],
                env=env,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if os.name == "nt" and desktop else 0
                ),
            )
            processes["dashboard"] = start_dashboard(control)
            supervise_processes(processes, stop, control)
        finally:
            stop_processes(processes.values())
            (control / "heartbeat").unlink(missing_ok=True)


def start_dashboard(control):
    """Start only the web process with its supervisor's private control channel.

    Args:
        control: Live supervisor directory inherited by the dashboard.

    Returns:
        subprocess.Popen: Owned dashboard child requiring eventual cleanup.
    """
    return subprocess.Popen(  # pylint: disable=consider-using-with
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            os.getenv("CLAN_DASHBOARD_SCRIPT", "dashboard/navigation.py"),
            f"--server.port={os.getenv('CLAN_DASHBOARD_PORT', '8501')}",
            "--server.address="
            + ("127.0.0.1" if os.getenv("CLAN_DESKTOP_CONTROL") else "0.0.0.0"),
        ],
        env=dict(os.environ, **{CONTROL_ENV: str(control)}),
        creationflags=(
            subprocess.CREATE_NO_WINDOW
            if os.name == "nt" and os.getenv("CLAN_DESKTOP_CONTROL")
            else 0
        ),
    )


def stop_processes(processes):
    """Terminate owned children, then reap them with a bounded grace period.

    Args:
        processes: Iterable of subprocess.Popen objects owned by this supervisor.

    Returns:
        None.
    """
    processes = list(processes)
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def supervise_processes(processes, stop, control):
    """Monitor children and honor only this instance's confirmed shutdown requests.

    Args:
        processes: Mapping of child role to its owned subprocess.Popen object.
        stop: Event set by supervisor signal handlers for full shutdown.
        control: Private directory carrying the heartbeat and UI requests.

    Returns:
        None. Full intentional shutdown returns normally; caller cleans up children.

    Raises:
        RuntimeError: A child exits without an intentional shutdown request.
    """
    while not stop.wait(1):
        (control / "heartbeat").touch()
        mode = pending_shutdown(control)
        if mode == "all":
            return
        if mode == "dashboard" and "dashboard" in processes:
            stop_processes([processes["dashboard"]])
            del processes["dashboard"]
        resume = control / "resume-dashboard"
        if resume.exists():
            resume.unlink(missing_ok=True)
            if "dashboard" not in processes:
                processes["dashboard"] = start_dashboard(control)
        if any(process.poll() is not None for process in processes.values()):
            raise RuntimeError("An application process exited unexpectedly.")


if __name__ == "__main__":
    main()
