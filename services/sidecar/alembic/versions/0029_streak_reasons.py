"""streak_reasons: a missed day keeps the streak when you say why (v1.2).

Revision ID: 0029
Revises: 0028

v1.2 replaces the automatic streak freezes with a reason rule: a missed day is kept when
a reason is given by the end of the next day; two missed days in a row, or no reason,
reset the streak. Streaks are recomputed from history, so nothing else changes; the old
freezes were never stored.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "streak_reasons",
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("reason", sa.String(120), nullable=False),
        sa.Column("given_on", sa.Date(), nullable=False),
        sa.Column("given_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("streak_reasons")
