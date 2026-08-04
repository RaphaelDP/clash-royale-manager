"""add days_in_clan and job_run_state

Revision ID: 6099e0c591ac
Revises: 67a87d4beb2d
Create Date: 2026-08-04 17:09:20.623769

"""

from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '6099e0c591ac'
down_revision: Union[str, Sequence[str], None] = '67a87d4beb2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # op.add_column(
    #     'members',
    #     sa.Column('days_in_clan', sa.Integer(), nullable=False, server_default='0'),
    # )

    op.create_table(
        'job_run_state',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('job_name', sa.String(), nullable=False, unique=True),
        sa.Column('last_run_date', sa.Date(), nullable=False),
    )

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
            sa.text(
                "UPDATE members "
                "SET days_in_clan = :days "
                "WHERE tag = :tag"
            ),
            {
                "days": max(days, 0),
                "tag": tag,
            },
        )

def downgrade() -> None:
    op.drop_table('job_run_state')
    op.drop_column('members', 'days_in_clan')