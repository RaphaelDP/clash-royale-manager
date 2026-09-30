"""
================================================================================
Filename: init_db.py
Description: Initialize and upgrade databases through the Alembic migration chain.
Author: Raphael Smilet
Date Created: 2026-06-06
Last Modified: 2026-09-30
Version: 0.1.1
Python Version: 3.12
================================================================================
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, UniqueConstraint

from app.database.base import Base
from app.database import models  # Register metadata before schema inspection.
from app.database.session import engine
from app.core.logger import logger

MIGRATIONS = Path(models.__file__).resolve().parents[1] / "migrations"


def migration_config(connection) -> Config:
    """Build Alembic settings using the supplied database connection."""
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    config.attributes["connection"] = connection
    return config


def recognize_unversioned_schema(connection) -> str:
    """Adopt only a recognized legacy schema, never stamp unknown tables blindly."""
    inspector = inspect(connection)
    tables = set(inspector.get_table_names()) - {"alembic_version"}
    expected = set(Base.metadata.tables)
    if tables - expected or (expected - {"job_run_state", "scheduler_config"}) - tables:
        raise RuntimeError(
            "Unrecognized unversioned schema; explicit migration review is required."
        )
    for name in tables:
        actual = {c["name"]: c for c in inspector.get_columns(name)}
        model = Base.metadata.tables[name]
        optional = {"days_in_clan"} if name == "members" else set()
        if name == "job_run_state":
            optional = {"last_attempt_at", "last_success_at", "last_error"}
        if set(actual) - set(model.columns.keys()) or set(
            model.columns.keys()
        ) - optional - set(actual):
            raise RuntimeError(
                f"Unrecognized columns in {name}; no migration stamp applied."
            )
        for column in model.columns:
            if (
                column.name in actual
                and column.type._type_affinity
                != actual[column.name]["type"]._type_affinity
            ):
                raise RuntimeError(f"Incompatible type in {name}.{column.name}.")
        expected_pk = [column.name for column in model.primary_key.columns]
        if inspector.get_pk_constraint(name)["constrained_columns"] != expected_pk:
            raise RuntimeError(f"Incompatible primary key in {name}.")
        actual_unique = {
            tuple(item["column_names"])
            for item in inspector.get_unique_constraints(name)
        }
        actual_unique |= {
            tuple(item["column_names"])
            for item in inspector.get_indexes(name)
            if item.get("unique")
        }

        expected_unique = {
            tuple(column.name for column in constraint.columns)
            for constraint in model.constraints
            if isinstance(constraint, UniqueConstraint)
        }
        if not expected_unique <= actual_unique:
            raise RuntimeError(f"Missing uniqueness constraint in {name}.")
        actual_foreign = {
            (
                tuple(item["constrained_columns"]),
                item["referred_table"],
                tuple(item["referred_columns"]),
            )
            for item in inspector.get_foreign_keys(name)
        }
        for constraint in model.foreign_key_constraints:
            expected_foreign = (
                tuple(element.parent.name for element in constraint.elements),
                constraint.referred_table.name,
                tuple(element.column.name for element in constraint.elements),
            )
            if expected_foreign not in actual_foreign:
                raise RuntimeError(f"Missing foreign key in {name}.")
    if "job_run_state" not in tables:
        return "67a87d4beb2d"
    job_columns = {c["name"] for c in inspector.get_columns("job_run_state")}
    tracking = {"last_attempt_at", "last_success_at", "last_error"}
    if tracking & job_columns and not tracking <= job_columns:
        raise RuntimeError(
            "Partially migrated job state; manual migration review required."
        )
    return "f117b96b7d59" if tracking <= job_columns else "6099e0c591ac"


def init_db(target_engine=None) -> None:
    """Create or upgrade the configured database, preserving recognized legacy data."""
    target = target_engine or engine
    if target.url.drivername.startswith("sqlite") and target.url.database not in (
        None,
        ":memory:",
    ):
        Path(target.url.database).parent.mkdir(parents=True, exist_ok=True)
    with target.begin() as connection:
        config = migration_config(connection)
        tables = set(inspect(connection).get_table_names())
        if tables - {"alembic_version"} and "alembic_version" not in tables:
            command.stamp(config, recognize_unversioned_schema(connection))
        command.upgrade(config, "head")
    logger.info("Database schema is up to date.")


if __name__ == "__main__":
    init_db()
