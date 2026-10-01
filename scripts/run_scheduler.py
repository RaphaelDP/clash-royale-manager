"""
================================================================================
Filename: run_scheduler.py
Description: Run one scheduler process with signal handling and settings reload.
Author: Raphael Smilet
Date Created: 2026-07-12
Last Modified: 2026-10-01
Version: 0.1.2
Python Version: 3.12
================================================================================
"""

import signal
from threading import Event
from app.core.job_lock import job_lock
from app.scheduler.scheduler import start_scheduler, reload_scheduler


def main():
    """
    Hold the process lock and reload settings until shutdown is requested.

    Args:
        None.

    Returns:
        None.
    """
    stop = Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    with job_lock("scheduler_process") as acquired:
        if not acquired:
            raise RuntimeError("A scheduler process is already running.")
        scheduler = start_scheduler()
        try:
            while not stop.wait(5):
                reload_scheduler(scheduler)
        finally:
            scheduler.shutdown(wait=True)


if __name__ == "__main__":
    main()
