"""
================================================================================
Filename: run_app.py
Description: Supervise dashboard and scheduler with safe startup and graceful shutdown.
Author: Raphael Smilet
Date Created: 2026-09-30
Last Modified: 2026-10-01
Version: 0.1.1
Python Version: 3.12
================================================================================
"""

import signal
import subprocess
import sys
from threading import Event

from scripts.init_db import init_db
from scripts.collect_data import main as collect_data
from app.core.logger import logger


def main():
    """
    Upgrade and collect data, then supervise the dashboard and scheduler.

    Args:
        None.

    Returns:
        None.
    """
    init_db()  # Never launch against an incompatible schema.
    try:
        collect_data()
    except Exception:
        # Keep the dashboard available to inspect persisted sync failures.
        logger.exception("Initial collection failed; serving existing data.")
    stop = Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    # Processes are terminated together and reaped in the finally block.
    # pylint: disable=consider-using-with
    processes = []
    try:
        processes.append(
            subprocess.Popen([sys.executable, "-m", "scripts.run_scheduler"])
        )
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    "dashboard/home.py",
                    "--server.port=8501",
                    "--server.address=0.0.0.0",
                ]
            )
        )
        while not stop.wait(1):
            if any(process.poll() is not None for process in processes):
                raise RuntimeError("An application process exited unexpectedly.")
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    main()
