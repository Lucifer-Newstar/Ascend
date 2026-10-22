"""boss_raids: the weekly boss raid (boss-v1, ADR-0022).

One row per week with the boss, its HP and where the HP came from, and when it was
beaten. Damage is counted from the logged sets, not stored.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "boss_raids",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("week_start", sa.Date(), nullable=False, unique=True),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("title", sa.String(40), nullable=False),
        sa.Column("hp", sa.Integer(), nullable=False),
        sa.Column("hp_source", sa.String(16), nullable=False),
        sa.Column("hp_note", sa.String(160), nullable=False),
        sa.Column("algo_version", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("defeated_at", sa.DateTime(), nullable=True),
        sa.Column("xp_awarded", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("boss_raids")
