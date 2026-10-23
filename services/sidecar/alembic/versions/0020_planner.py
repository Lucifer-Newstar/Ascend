"""planner: custom workout programs, saved diet plans and the profile's training experience.

Revision ID: 0020
Revises: 0019
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "custom_programs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("summary", sa.String(400), nullable=False, server_default=""),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("equipment", sa.String(16), nullable=False),
        sa.Column("days", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("algo_version", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.create_table(
        "diet_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("kcal_target", sa.Integer(), nullable=False),
        sa.Column("protein_target_g", sa.Integer(), nullable=False),
        sa.Column("diet", sa.String(8), nullable=False),
        sa.Column("plan", sa.Text(), nullable=False),
        sa.Column("algo_version", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
    )
    with op.batch_alter_table("profile") as batch:
        batch.add_column(sa.Column("experience", sa.String(12), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("profile") as batch:
        batch.drop_column("experience")
    op.drop_table("diet_plans")
    op.drop_table("custom_programs")
