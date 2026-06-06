"""
================================================================================
Filename: init_db.py
Description: Script to initialize the database and create tables.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-06
Version: 0.1.0
Python Version: 3.11
Dependencies: sqlalchemy, app.database.base, app.database.models
================================================================================
"""

from app.database.base import Base
from app.database.session import engine
from app.core.logger import logger


def init_db() -> None:
    """
    Initialize the database and create all tables defined in SQLAlchemy models.
    Run this script once to set up the database schema.
    """
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized and tables created.")


if __name__ == "__main__":
    init_db()
