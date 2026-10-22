"""programs-v1: the workout program the user follows

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-21

New table plan_enrollments: which built-in program (workouts/programs.py) the user chose
and when. The active choice has no ended_at (ADR-0020).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plan_enrollments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("program_key", sa.String(40), nullable=False),
        sa.Column("started_on", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_plan_enrollments_ended_at", "plan_enrollments", ["ended_at"])


def downgrade() -> None:
    op.drop_index("ix_plan_enrollments_ended_at", "plan_enrollments")
    op.drop_table("plan_enrollments")
