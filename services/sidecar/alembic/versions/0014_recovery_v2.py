"""recovery-v2: personal recovery factors and recovery-v2 doses

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-21

New table recovery_params (one row per muscle group: the personal factor k with its
interval, the evidence count and the fitted fatigue sensitivity). The stored per-muscle
doses in muscle_load_events are recomputed with the recovery-v2 rule (RIR-weighted,
holds by seconds); the downgrade puts the load-v1 rows back. The data step lives in
app/modules/intelligence/doses.py.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.modules.intelligence import doses

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recovery_params",
        sa.Column("muscle_group", sa.String(16), primary_key=True),
        sa.Column("k", sa.Float(), nullable=False),
        sa.Column("k_low", sa.Float(), nullable=False),
        sa.Column("k_high", sa.Float(), nullable=False),
        sa.Column("k_hat", sa.Float(), nullable=True),
        sa.Column("alpha", sa.Float(), nullable=True),
        sa.Column("n", sa.Integer(), nullable=False),
        sa.Column("personal", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("algo_version", sa.String(16), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    doses.rebuild(op.get_bind())


def downgrade() -> None:
    doses.rebuild(op.get_bind(), version="load-v1")
    op.drop_table("recovery_params")
