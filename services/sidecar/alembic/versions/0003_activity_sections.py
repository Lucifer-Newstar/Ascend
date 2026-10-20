"""shared logger: sections, time and distance sets

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-20

One logger serves all six training sections (decision D8). Exercises and
workouts get a `section`; sets get optional duration, distance and heart rate
so a run, a boxing round, a stretch hold or a meditation sit is a set too.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("exercises") as b:
        b.add_column(sa.Column("section", sa.String(16), nullable=False, server_default="gym"))
        b.add_column(sa.Column("met", sa.Float(), nullable=True))
        b.create_index("ix_exercises_section", ["section"])
    with op.batch_alter_table("workouts") as b:
        b.add_column(sa.Column("section", sa.String(16), nullable=False, server_default="gym"))
    with op.batch_alter_table("workout_sets") as b:
        b.add_column(sa.Column("duration_s", sa.Integer(), nullable=True))
        b.add_column(sa.Column("distance_m", sa.Float(), nullable=True))
        b.add_column(sa.Column("avg_hr", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("workout_sets") as b:
        b.drop_column("avg_hr")
        b.drop_column("distance_m")
        b.drop_column("duration_s")
    with op.batch_alter_table("workouts") as b:
        b.drop_column("section")
    with op.batch_alter_table("exercises") as b:
        b.drop_index("ix_exercises_section")
        b.drop_column("met")
        b.drop_column("section")
