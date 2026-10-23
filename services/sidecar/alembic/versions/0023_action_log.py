"""action_log: in-app actions the trainer or the user proposed, and what became of them.

Revision ID: 0023
Revises: 0022
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "action_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("params", sa.Text(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("source", sa.String(10), nullable=False),
        sa.Column("origin_text", sa.String(400), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("undo", sa.Text(), nullable=True),
        sa.Column("error", sa.String(300), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("executed_at", sa.DateTime(), nullable=True),
        sa.Column("undone_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_action_log_status", "action_log", ["status"])


def downgrade() -> None:
    op.drop_index("ix_action_log_status", "action_log")
    op.drop_table("action_log")
