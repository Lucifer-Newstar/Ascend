"""where a workout came from (app or an import) and a key that stops double imports

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("workouts") as batch:
        batch.add_column(sa.Column("source", sa.String(16), nullable=False, server_default="app"))
        # e.g. "strong:2026-09-01T18:02:11:Push Day"; NULL for workouts logged in ASCEND.
        batch.add_column(sa.Column("import_key", sa.String(160), nullable=True))
        batch.create_index("ix_workouts_import_key", ["import_key"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("workouts") as batch:
        batch.drop_index("ix_workouts_import_key")
        batch.drop_column("import_key")
        batch.drop_column("source")
