"""selector_picks: what the trainer posted on its own and why (select-v1); the trainer's
messages keep their why too.

Revision ID: 0022
Revises: 0021
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "selector_picks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("source", sa.String(8), nullable=False),
        sa.Column("item_id", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("text", sa.String(400), nullable=False),
        sa.Column("why", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_selector_picks_day", "selector_picks", ["day"])
    op.create_index("ix_selector_picks_item_id", "selector_picks", ["item_id"])
    with op.batch_alter_table("trainer_messages") as batch:
        batch.add_column(sa.Column("why", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("trainer_messages") as batch:
        batch.drop_column("why")
    op.drop_index("ix_selector_picks_item_id", "selector_picks")
    op.drop_index("ix_selector_picks_day", "selector_picks")
    op.drop_table("selector_picks")
