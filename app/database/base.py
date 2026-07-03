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
from sqlalchemy.inspection import inspect


class Base(DeclarativeBase):
    """
    Declarative base for all ORM models.

    Provides the shared SQLAlchemy metadata used to define and
    manage database tables throughout the application.
    """

    def to_dict(self, include_relationships: bool = False) -> dict:
        data = {
            column.key: getattr(self, column.key)
            for column in inspect(self).mapper.column_attrs
        }

        if include_relationships:
            for rel in inspect(self).mapper.relationships:
                value = getattr(self, rel.key)

                if rel.uselist:
                    data[rel.key] = [
                        item.to_dict() if hasattr(item, "to_dict") else str(item)
                        for item in value
                    ]
                else:
                    data[rel.key] = (
                        value.to_dict() if value and hasattr(value, "to_dict") else None
                    )

        return data
