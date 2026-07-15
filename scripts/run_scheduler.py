"""
================================================================================
Filename: run_scheduler.py
Description: Standalone entry point to run the background scheduler as its
    own process, separate from the Streamlit dashboard.
Author: Raphael Smilet
Date Created: 2026-07-12
Last Modified: 2026-07-12
Version: 0.1.0
Python Version: 3.12
Dependencies: app.scheduler.scheduler
================================================================================
"""

import time

from app.core.logger import logger
from app.scheduler.scheduler import start_scheduler


def main():
    """Start the scheduler and keep this process alive."""
    scheduler = start_scheduler()

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
