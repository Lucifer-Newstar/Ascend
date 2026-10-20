"""exercise library v2: metadata columns + free-exercise-db + calisthenics progressions

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-20

New exercise columns: slug, measure (reps | hold | time), difficulty, movement pattern,
mechanic, instructions and aliases (JSON lists), thumbnail path, source and source_ref
(where the row came from), field_sources (JSON: which source proposed each field),
default rep/hold range, is_custom/archived for user-added exercises, attribution (JSON
list of online sources) and created_at. The data step lives in
app/modules/workouts/library_seed.py.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.modules.workouts import library_seed

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Plain ALTER TABLE statements, not batch mode: a batch "move and copy" of `exercises`
# would drop the old table, and with foreign keys on, SQLite's implicit DELETE would
# cascade to exercise_muscles. SQLite has supported DROP COLUMN since 3.35.
COLUMNS: list[sa.Column[object]] = [
    sa.Column("slug", sa.String(80), nullable=True),
    sa.Column("measure", sa.String(8), nullable=False, server_default="reps"),
    sa.Column("difficulty", sa.String(12), nullable=True),
    sa.Column("pattern", sa.String(16), nullable=False, server_default="other"),
    sa.Column("mechanic", sa.String(12), nullable=True),
    sa.Column("instructions", sa.Text(), nullable=False, server_default="[]"),
    sa.Column("aliases", sa.Text(), nullable=False, server_default="[]"),
    sa.Column("image", sa.String(120), nullable=True),
    sa.Column("source", sa.String(24), nullable=False, server_default="ascend"),
    sa.Column("source_ref", sa.String(80), nullable=True),
    sa.Column("field_sources", sa.Text(), nullable=False, server_default="{}"),
    sa.Column("rep_low", sa.Integer(), nullable=True),
    sa.Column("rep_high", sa.Integer(), nullable=True),
    sa.Column("is_custom", sa.Boolean(), nullable=False, server_default="0"),
    sa.Column("archived", sa.Boolean(), nullable=False, server_default="0"),
    sa.Column("attribution", sa.Text(), nullable=False, server_default="[]"),
    sa.Column("created_at", sa.DateTime(), nullable=True),
]


def upgrade() -> None:
    for col in COLUMNS:
        op.add_column("exercises", col)
    library_seed.upgrade(op.get_bind())
    op.create_index("ix_exercises_slug", "exercises", ["slug"], unique=True)


def downgrade() -> None:
    library_seed.downgrade(op.get_bind())
    op.drop_index("ix_exercises_slug", table_name="exercises")
    for col in reversed(COLUMNS):
        op.execute(f"ALTER TABLE exercises DROP COLUMN {col.name}")
