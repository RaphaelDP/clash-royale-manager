"""track job execution state

Revision ID: f117b96b7d59
Revises: 6099e0c591ac
Create Date: 2026-09-11 18:02:16.540225
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f117b96b7d59"
down_revision: Union[str, Sequence[str], None] = "6099e0c591ac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "job_run_state",
        sa.Column("last_attempt_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "job_run_state",
        sa.Column("last_success_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "job_run_state",
        sa.Column("last_error", sa.String(), nullable=True),
    )

    connection = op.get_bind()

    connection.execute(
        sa.text(
            """
            UPDATE job_run_state
            SET last_attempt_at = CURRENT_TIMESTAMP
            WHERE last_attempt_at IS NULL
            """
        )
    )

    with op.batch_alter_table("job_run_state") as batch_op:
        batch_op.alter_column(
            "last_attempt_at",
            existing_type=sa.DateTime(),
            nullable=False,
        )
        batch_op.alter_column(
            "last_run_date",
            existing_type=sa.Date(),
            nullable=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("job_run_state") as batch_op:
        batch_op.alter_column(
            "last_run_date",
            existing_type=sa.Date(),
            nullable=False,
        )
        batch_op.drop_column("last_error")
        batch_op.drop_column("last_success_at")
        batch_op.drop_column("last_attempt_at")