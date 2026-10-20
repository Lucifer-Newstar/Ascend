"""transactional outbox and processed-event log

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "events_outbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.String(500), nullable=True),
    )
    op.create_index("ix_events_outbox_type", "events_outbox", ["type"])
    op.create_index("ix_events_outbox_created_at", "events_outbox", ["created_at"])
    op.create_table(
        "processed_events",
        sa.Column("handler", sa.String(128), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("handler", "event_id"),
    )


def downgrade() -> None:
    op.drop_table("processed_events")
    op.drop_index("ix_events_outbox_created_at", table_name="events_outbox")
    op.drop_index("ix_events_outbox_type", table_name="events_outbox")
    op.drop_table("events_outbox")
