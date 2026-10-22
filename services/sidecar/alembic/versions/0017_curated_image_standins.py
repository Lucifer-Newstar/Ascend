"""Pictures for curated entries: a similar-movement photo where free-exercise-db has one

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-22

Sets exercises.image for ASCEND's own entries listed in workouts/library.py IMAGE_STANDINS
and records field_sources["image"] = "similar:<source exercise>" so the detail view can say
the picture shows a related movement. Only rows that still have no image are touched, so a
user's own edits are never overwritten. Downgrade clears exactly those pictures again.
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.modules.workouts.library import IMAGE_STANDINS, standin_image

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _rows(conn: sa.Connection, name: str) -> list[sa.Row[tuple[int, str | None, str | None]]]:
    return list(
        conn.execute(
            sa.text(
                "SELECT id, image, field_sources FROM exercises "
                "WHERE name = :n AND source = 'ascend' AND is_custom = 0"
            ),
            {"n": name},
        )
    )


def upgrade() -> None:
    conn = op.get_bind()
    for name in IMAGE_STANDINS:
        found = standin_image(name)
        assert found is not None
        path, ref = found
        for row_id, image, sources_raw in _rows(conn, name):
            if image:
                continue
            sources = json.loads(sources_raw or "{}")
            sources["image"] = f"similar:{ref}"
            conn.execute(
                sa.text("UPDATE exercises SET image = :p, field_sources = :s WHERE id = :i"),
                {"p": path, "s": json.dumps(sources, sort_keys=True), "i": row_id},
            )


def downgrade() -> None:
    conn = op.get_bind()
    for name in IMAGE_STANDINS:
        found = standin_image(name)
        assert found is not None
        path, _ref = found
        for row_id, image, sources_raw in _rows(conn, name):
            if image != path:
                continue
            sources = json.loads(sources_raw or "{}")
            sources.pop("image", None)
            conn.execute(
                sa.text("UPDATE exercises SET image = NULL, field_sources = :s WHERE id = :i"),
                {"s": json.dumps(sources, sort_keys=True), "i": row_id},
            )
