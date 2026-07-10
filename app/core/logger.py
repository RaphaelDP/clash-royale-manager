"""
================================================================================
Filename: logger.py
Description: Logging configuration for the application, including file and console handlers.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-07-10
Version: 0.5.0
Python Version: 3.12
Dependencies: None
================================================================================
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from app.core.config import settings


def _is_running_in_docker() -> bool:
    """
    Detect whether the application is running inside a Docker container.

    Docker automatically creates the file '/.dockerenv' inside containers,
    making it a simple and reliable way to detect the runtime environment.
    """
    return os.path.exists("/.dockerenv")


# =============================================================================
# Logger configuration
# =============================================================================

# Create (or retrieve) the application's logger.
# Using a named logger allows every module to share the same configuration.
logger = logging.getLogger("clan_manager")
logger.setLevel(getattr(logging, settings.LOG_LEVEL))

# Prevent duplicate log messages.
#
# Streamlit reloads modules whenever code changes. Without clearing existing
# handlers, every reload would add another handler, causing each log message
# to be printed multiple times.
logger.handlers.clear()

# Prevent messages from also being handled by Python's root logger.
logger.propagate = False

# Common format used regardless of where logs are written.
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# =============================================================================
# Logging destination
# =============================================================================

if _is_running_in_docker():
    # Docker best practice:
    #
    # Containers should write logs to stdout/stderr instead of files.
    # Docker automatically captures these logs, making them available through:
    #
    #     docker logs <container>
    #
    # This also avoids file permission issues when using bind mounts.
    handler = logging.StreamHandler(sys.stdout)

else:
    # Local execution:
    #
    # When running directly on the host (outside Docker), keep rotating log
    # files so logs persist between executions.
    os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)

    handler = RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=1024 * 1024,  # Rotate after 1 MB
        backupCount=5,  # Keep the last 5 log files
        encoding="utf-8",
    )

# Apply the same formatter regardless of the handler type.
handler.setFormatter(formatter)

# Register the handler with the application logger.
logger.addHandler(handler)
