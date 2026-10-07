"""
Filename: a2026100701_merge_race_phase.py
Description: Move phase metadata onto weekly river races.
Author: Raphael Smilet
Date Created: 2026-10-07
Last Modified: 2026-10-07
Version: 0.1.0
"""

from alembic import op
import sqlalchemy as sa

revision = "a2026100701"
down_revision = "a2026100601"
branch_labels = None
depends_on = None


def upgrade():
    """Merge identified phase observations into weekly races.

    Args:
        None.

    Returns:
        None.
    """
    bind = op.get_bind()
    columns = {c["name"] for c in sa.inspect(bind).get_columns("river_races")}
    for column in (
        sa.Column("type_of_day", sa.String(), nullable=False, server_default="unknown"),
        sa.Column("period_index", sa.Integer(), nullable=True),
        sa.Column("observed_at", sa.DateTime(), nullable=True),
    ):
        if column.name not in columns:
            op.add_column("river_races", column)
    bind.execute(sa.text("UPDATE river_races SET type_of_day='battle' WHERE is_completed=1"))
    if "war_phase" in sa.inspect(bind).get_table_names():
        phases = bind.execute(sa.text("SELECT * FROM war_phase")).mappings().all()
        for phase in phases:
            season = phase["season_id"]
            if season is None:
                # No weekly identity can safely be assigned; the next sync refreshes it.
                continue
            values = dict(phase)
            values["kind"] = (
                "training" if phase["period_type"] == "training"
                else "battle" if phase["period_type"] in ("warDay", "colosseum")
                else "unknown"
            )
            bind.execute(sa.text(
                "INSERT INTO war_seasons (season_id, start_date) "
                "SELECT :season_id, :observed_at WHERE NOT EXISTS "
                "(SELECT 1 FROM war_seasons WHERE season_id=:season_id)"
            ), values)
            bind.execute(sa.text(
                "INSERT INTO river_races (season_id, section_index, created_date, is_completed, type_of_day) "
                "SELECT :season_id, :section_index, :observed_at, 0, :kind WHERE NOT EXISTS "
                "(SELECT 1 FROM river_races WHERE season_id=:season_id AND section_index=:section_index)"
            ), values)
            bind.execute(sa.text(
                "UPDATE river_races SET type_of_day=:kind, period_index=:period_index, "
                "observed_at=:observed_at WHERE season_id=:season_id "
                "AND section_index=:section_index AND is_completed=0"
            ), values)
            if values["kind"] == "training":
                bind.execute(sa.text(
                    "DELETE FROM war_participation WHERE river_race_id IN "
                    "(SELECT id FROM river_races WHERE season_id=:season_id "
                    "AND section_index=:section_index AND is_completed=0)"
                ), values)
        op.drop_table("war_phase")


def downgrade():
    """Restore the previous phase table and remove race metadata columns.

    Args:
        None.

    Returns:
        None.
    """
    op.create_table(
        "war_phase",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("period_type", sa.String(), nullable=False),
        sa.Column("period_index", sa.Integer(), nullable=True),
        sa.Column("section_index", sa.Integer(), nullable=False),
        sa.Column("season_id", sa.String(), nullable=True),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
    )
    op.execute(sa.text(
        "INSERT INTO war_phase SELECT 1, "
        "CASE WHEN type_of_day='battle' THEN 'warDay' ELSE type_of_day END, "
        "period_index, section_index, season_id, observed_at FROM river_races "
        "WHERE observed_at IS NOT NULL ORDER BY observed_at DESC LIMIT 1"
    ))
    with op.batch_alter_table("river_races") as batch:
        batch.drop_column("observed_at")
        batch.drop_column("period_index")
        batch.drop_column("type_of_day")
