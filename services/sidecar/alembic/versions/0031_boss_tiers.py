"""boss_tiers: remember the tier each weekly boss raid was spawned at (boss-v2, v1.2).

Revision ID: 0031
Revises: 0030

Seasonal bosses follow the player's level, so the tier is stored with the raid. Older
raids keep NULL and take the tier from the boss's name.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("boss_raids") as batch:
        batch.add_column(sa.Column("tier", sa.String(length=1), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("boss_raids") as batch:
        batch.drop_column("tier")
