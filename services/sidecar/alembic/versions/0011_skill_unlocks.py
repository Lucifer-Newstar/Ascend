"""skill trees: unlocked steps

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "skill_unlocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("skill_key", sa.String(32), nullable=False),
        sa.Column("step_key", sa.String(40), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(), nullable=False),
        sa.Column("source", sa.String(12), nullable=False, server_default="log"),
        sa.Column("trigger_set_id", sa.Integer(), nullable=True),
        sa.Column("evidence", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("engine_version", sa.String(16), nullable=False),
        sa.UniqueConstraint("skill_key", "step_key", name="uq_skill_step"),
    )
    op.create_index("ix_skill_unlocks_skill_key", "skill_unlocks", ["skill_key"])


def downgrade() -> None:
    op.drop_index("ix_skill_unlocks_skill_key", table_name="skill_unlocks")
    op.drop_table("skill_unlocks")
