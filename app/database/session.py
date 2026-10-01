"""
================================================================================
Filename: session.py
Description: Database session configuration and dependency for FastAPI.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-10-01
Version: 0.1.1
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
    Open a database session and close it when the context exits.

    This helper does not automatically commit changes.

    Args:
        None.

    Returns:
        AbstractContextManager[Session]: Context manager owning one database session.

    Yields:
        Session: Open session, always closed when the context exits.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
