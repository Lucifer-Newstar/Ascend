"""unlock_events: the unlocks you have seen, for the Unlocks page and its replays (v1.4).

Revision ID: 0033
Revises: 0032
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0033"
down_revision: str | None = "0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "unlock_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(80), nullable=False, unique=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("title", sa.String(80), nullable=False),
        sa.Column("detail", sa.String(160), nullable=False, server_default=""),
        sa.Column("at", sa.DateTime(), nullable=False),
        sa.Column("seeded", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_unlock_events_at", "unlock_events", ["at"])


def downgrade() -> None:
    op.drop_index("ix_unlock_events_at", "unlock_events")
    op.drop_table("unlock_events")
