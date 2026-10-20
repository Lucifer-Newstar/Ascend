"""body metrics, tape measurements and a target weight

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "body_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("measured_at", sa.DateTime(), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=False),
        sa.Column("waist_cm", sa.Float(), nullable=True),
        sa.Column("resting_hr", sa.Integer(), nullable=True),
    )
    op.create_index("ix_body_metrics_measured_at", "body_metrics", ["measured_at"])
    op.create_table(
        "measurements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("measured_at", sa.DateTime(), nullable=False),
        sa.Column("site", sa.String(16), nullable=False),
        sa.Column("cm", sa.Float(), nullable=False),
    )
    op.create_index("ix_measurements_measured_at", "measurements", ["measured_at"])
    op.create_index("ix_measurements_site", "measurements", ["site"])
    with op.batch_alter_table("profile") as b:
        b.add_column(sa.Column("target_weight_kg", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("profile") as b:
        b.drop_column("target_weight_kg")
    op.drop_index("ix_measurements_site", "measurements")
    op.drop_index("ix_measurements_measured_at", "measurements")
    op.drop_table("measurements")
    op.drop_index("ix_body_metrics_measured_at", "body_metrics")
    op.drop_table("body_metrics")
