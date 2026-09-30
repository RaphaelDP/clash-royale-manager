"""
================================================================================
Filename: a2026093001_repair_membership_days.py
Description: Repair membership days on databases already past the historical migration.
Author: Raphael Smilet
Date Created: 2026-09-30
Last Modified: 2026-09-30
Version: 0.1.0
Python Version: 3.12
================================================================================
"""

from alembic import op
import sqlalchemy as sa

revision = "a2026093001"
down_revision = "f117b96b7d59"
branch_labels = None
depends_on = None


def upgrade():
    # Older installations may already be stamped beyond the faulty revision.
    if "days_in_clan" not in {
        c["name"] for c in sa.inspect(op.get_bind()).get_columns("members")
    }:
        op.add_column(
            "members",
            sa.Column("days_in_clan", sa.Integer(), nullable=False, server_default="0"),
        )
        # Membership before this repair is unknown; do not invent tenure across absences.


def downgrade():
    # The repaired historical revision also owns this column. Preserve it here.
    pass
