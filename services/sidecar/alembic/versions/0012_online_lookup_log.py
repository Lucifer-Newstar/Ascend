"""online research: local lookup log

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "online_lookup_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("at", sa.DateTime(), nullable=False),
        sa.Column("query", sa.String(80), nullable=False),
        sa.Column("sources_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("consent", sa.String(8), nullable=False),
        sa.Column("detail", sa.String(200), nullable=False, server_default=""),
    )
    op.create_index("ix_online_lookup_log_at", "online_lookup_log", ["at"])


def downgrade() -> None:
    op.drop_index("ix_online_lookup_log_at", table_name="online_lookup_log")
    op.drop_table("online_lookup_log")
