"""
================================================================================
Filename: session.py
Description: Database session configuration and dependency for FastAPI.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-06
Version: 0.1.0
Python Version: 3.11
Dependencies: sqlalchemy
================================================================================
"""

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Create engine
engine = create_engine(settings.DATABASE_URL, echo=False)

# Create session factory
SessionLocal = sessionmaker(  # pylint: disable=invalid-name
    autocommit=False, autoflush=False, bind=engine
)


# Dependency to get DB session
@contextmanager
def get_session():
    """
    Dependency to get a database session for FastAPI routes.

    Yields:
        SessionLocal: A SQLAlchemy database session.

    Note:
        Automatically closes the session after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
