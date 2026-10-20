"""prog-v1: decisions on progression targets

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-21

New table progression_decisions: "use it" / "keep mine" on a target, so a declined target
is not proposed again for 7 days (backlog FT-1) and acceptance can be measured.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "progression_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "exercise_id",
            sa.Integer(),
            sa.ForeignKey("exercises.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("decided_at", sa.DateTime(), nullable=False),
        sa.Column("choice", sa.String(10), nullable=False),
        sa.Column("reason", sa.String(24), nullable=False),
        sa.Column("target_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("algo_version", sa.String(16), nullable=False),
    )
    op.create_index(
        "ix_progression_decisions_exercise_id", "progression_decisions", ["exercise_id"]
    )
    op.create_index("ix_progression_decisions_decided_at", "progression_decisions", ["decided_at"])


def downgrade() -> None:
    op.drop_index("ix_progression_decisions_decided_at", "progression_decisions")
    op.drop_index("ix_progression_decisions_exercise_id", "progression_decisions")
    op.drop_table("progression_decisions")
