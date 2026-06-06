"""
================================================================================
Filename: base.py
Description: SQLAlchemy base model for database tables.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-06-06
Version: 0.1.0
Python Version: 3.11
Dependencies: sqlalchemy
================================================================================
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Declarative base for all ORM models.

    Provides the shared SQLAlchemy metadata used to define and
    manage database tables throughout the application.
    """
