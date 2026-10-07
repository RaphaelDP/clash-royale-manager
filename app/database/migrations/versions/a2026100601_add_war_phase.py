"""
Filename: a2026100601_add_war_phase.py
Description: Store current API war phase without creating training participation.
Author: Raphael Smilet
Date Created: 2026-10-06
Last Modified: 2026-10-06
Version: 0.1.0
"""

from alembic import op
import sqlalchemy as sa

revision = "a2026100601"
down_revision = "a2026093001"
branch_labels = None
depends_on = None


def upgrade():
    """Add phase storage, tolerating a recognized unversioned current schema.

    Args:
        None.

    Returns:
        None.
    """
    if "war_phase" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "war_phase",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("period_type", sa.String(), nullable=False),
            sa.Column("period_index", sa.Integer(), nullable=True),
            sa.Column("section_index", sa.Integer(), nullable=False),
            sa.Column("season_id", sa.String(), nullable=True),
            sa.Column("observed_at", sa.DateTime(), nullable=False),
        )


def downgrade():
    """Remove phase metadata while preserving all race history.

    Args:
        None.

    Returns:
        None.
    """
    op.drop_table("war_phase")
