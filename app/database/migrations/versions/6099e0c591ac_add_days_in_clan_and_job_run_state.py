"""add days_in_clan and job_run_state

Revision ID: 6099e0c591ac
Revises: 67a87d4beb2d
Create Date: 2026-08-04 17:09:20.623769

Filename: 6099e0c591ac_add_days_in_clan_and_job_run_state.py
Description: Add days_in_clan and job_run_state.
Author: Raphael Smilet
Date Created: 2026-08-04
Last Modified: 2026-10-01
Version: 0.1.0
"""

from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "6099e0c591ac"
down_revision: Union[str, Sequence[str], None] = "67a87d4beb2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Apply the membership-day and job-guard schema changes in the active Alembic context.

    Args:
        None.

    Returns:
        None.
    """
    missing_days = "days_in_clan" not in {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("members")
    }
    if missing_days:
        op.add_column(
            "members",
            sa.Column("days_in_clan", sa.Integer(), nullable=False, server_default="0"),
        )

    op.create_table(
        "job_run_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_name", sa.String(), nullable=False, unique=True),
        sa.Column("last_run_date", sa.Date(), nullable=False),
    )

    if not missing_days:
        return

    # One-time best-effort backfill: seed days_in_clan from clan_joined_at
    # for existing members. No historical daily record exists before this
    # migration, so this is an approximation, not an exact reconstruction.
    conn = op.get_bind()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    rows = conn.execute(
        sa.text(
            "SELECT tag, clan_joined_at "
            "FROM members "
            "WHERE clan_joined_at IS NOT NULL"
        )
    ).fetchall()

    for tag, clan_joined_at in rows:
        if isinstance(clan_joined_at, str):
            clan_joined_at = datetime.fromisoformat(clan_joined_at)

        days = (now - clan_joined_at).days

        conn.execute(
            sa.text("UPDATE members " "SET days_in_clan = :days " "WHERE tag = :tag"),
            {
                "days": max(days, 0),
                "tag": tag,
            },
        )


def downgrade() -> None:
    """
    Reverse the membership-day and job-guard schema changes in the active Alembic
    context.

    Args:
        None.

    Returns:
        None.
    """
    op.drop_table("job_run_state")
    op.drop_column("members", "days_in_clan")
