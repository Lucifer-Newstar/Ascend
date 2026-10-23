"""trainer_messages: what the trainer noticed (watch-v1), each event posted once.

Revision ID: 0021
Revises: 0020
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trainer_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(120), nullable=False, unique=True),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("mood", sa.String(10), nullable=False),
        sa.Column("text", sa.String(400), nullable=False),
        sa.Column("action_kind", sa.String(16), nullable=True),
        sa.Column("action_target", sa.String(40), nullable=True),
        sa.Column("share", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_trainer_messages_created_at", "trainer_messages", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_trainer_messages_created_at", "trainer_messages")
    op.drop_table("trainer_messages")
