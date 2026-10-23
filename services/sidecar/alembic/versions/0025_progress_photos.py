"""progress_photos: dated progress photos kept as files in the data folder.

Revision ID: 0025
Revises: 0024
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "progress_photos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("taken_on", sa.Date(), nullable=False),
        sa.Column("pose", sa.String(8), nullable=False, server_default="front"),
        sa.Column("filename", sa.String(64), nullable=False, unique=True),
        sa.Column("mime", sa.String(16), nullable=False),
        sa.Column("bytes", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(200), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_progress_photos_taken_on", "progress_photos", ["taken_on"])


def downgrade() -> None:
    op.drop_index("ix_progress_photos_taken_on", "progress_photos")
    op.drop_table("progress_photos")
