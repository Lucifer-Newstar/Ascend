"""keep_v11_theme: existing players keep the look they had (v1.2 themes).

Revision ID: 0028
Revises: 0027

v1.2 makes "Shadow" the default theme for new players. Someone upgrading from v1.1 who never
picked a theme had the old dark look by default; this pins it ("dark"), so the upgrade does
not change their app's look without asking. A fresh install (no profile yet) is untouched.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    has_profile = bind.execute(sa.text("SELECT COUNT(*) FROM profile")).scalar()
    has_theme = bind.execute(sa.text("SELECT COUNT(*) FROM settings WHERE key = 'theme'")).scalar()
    if has_profile and not has_theme:
        bind.execute(sa.text("INSERT INTO settings (key, value) VALUES ('theme', 'dark')"))


def downgrade() -> None:
    # v1.1 knows only dark / light / system: a v1.2 theme falls back to its default (dark).
    op.execute(
        "DELETE FROM settings WHERE key = 'theme' AND value NOT IN ('dark', 'light', 'system')"
    )
