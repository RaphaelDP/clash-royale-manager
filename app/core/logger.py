"""
================================================================================
Filename: logger.py
Description: Logging configuration for the application, including file and console handlers.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-06
Version: 0.1.0
Python Version: 3.11
Dependencies: None
================================================================================
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from app.core.config import settings

# Create logs directory if it doesn't exist
os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)

# Configure logger
logger = logging.getLogger("clan_manager")
logger.setLevel(getattr(logging, settings.LOG_LEVEL))

# File handler
file_handler = RotatingFileHandler(
    settings.LOG_FILE, maxBytes=1024 * 1024, backupCount=5, encoding="utf-8"  # 1MB
)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)

# Add handlers
logger.addHandler(file_handler)
logger.addHandler(console_handler)
