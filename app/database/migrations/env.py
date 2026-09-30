"""
================================================================================
Filename: env.py
Description: Apply migrations to an explicit connection or the configured application database.
Author: Raphael Smilet
Date Created: 2026-09-30
Last Modified: 2026-09-30
Version: 0.1.0
Python Version: 3.12
================================================================================
"""

from logging.config import fileConfig
from alembic import context
from sqlalchemy import create_engine, pool
from app.core.config import settings
from app.database.base import Base
from app.database import models

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name, disable_existing_loggers=False)
target_metadata = Base.metadata


def run(connection):
    context.configure(
        connection=connection, target_metadata=target_metadata, render_as_batch=True
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("Schema-aware upgrades require an online database connection.")
else:
    supplied = config.attributes.get("connection")
    if supplied is not None:
        run(supplied)
    else:
        engine = create_engine(settings.DATABASE_URL, poolclass=pool.NullPool)
        with engine.connect() as connection:
            run(connection)
