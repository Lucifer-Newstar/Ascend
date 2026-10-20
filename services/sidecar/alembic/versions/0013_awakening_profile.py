"""awakening onboarding: profile focus, equipment and baseline

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("profile") as batch:
        batch.add_column(sa.Column("focus", sa.String(12), nullable=True))
        batch.add_column(sa.Column("equipment", sa.Text(), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("baseline", sa.Text(), nullable=False, server_default="{}"))


def downgrade() -> None:
    with op.batch_alter_table("profile") as batch:
        batch.drop_column("baseline")
        batch.drop_column("equipment")
        batch.drop_column("focus")
