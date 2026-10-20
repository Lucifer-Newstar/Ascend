"""remember what a check-in did to the quest

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # NULL = the band's default note (rows from before this column existed).
    with op.batch_alter_table("checkins") as batch:
        batch.add_column(sa.Column("quest_note", sa.String(160), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("checkins") as batch:
        batch.drop_column("quest_note")
