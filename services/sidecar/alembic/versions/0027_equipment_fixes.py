"""equipment_fixes: correct the gear on library moves that need a bar, dip bars or a bench,
and retire partner-only martial-arts entries (v1.2 loadout + solo-safe rule).

Revision ID: 0027
Revises: 0026

v1.1 listed some moves as "bodyweight" that cannot be done without gear (a pull-up needs a
bar), so a no-equipment user was offered them. Partner-only entries (BJJ rolling, pad work
held by a partner) are archived, not deleted: anything already logged with them stays in
the history. The downgrade restores the old values.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# name -> (old equipment, new equipment)
EQUIPMENT_FIXES: dict[str, tuple[str, str]] = {
    "Pull-up": ("bodyweight", "bar"),
    "Chin-up": ("bodyweight", "bar"),
    "Hanging Leg Raise": ("bodyweight", "bar"),
    "Hanging Pike": ("bodyweight", "bar"),
    "Gorilla Chin/Crunch": ("bodyweight", "bar"),
    "Chest Dip": ("bodyweight", "parallel_bars"),
    "Dips - Triceps Version": ("bodyweight", "parallel_bars"),
    "Close-Grip Push-Up off of a Dumbbell": ("bodyweight", "dumbbell"),
    "Flat Bench Leg Pull-In": ("bodyweight", "bench"),
    "Seated Flat Bench Leg Pull-In": ("bodyweight", "bench"),
    "Decline Crunch": ("bodyweight", "bench"),
    "Decline Oblique Crunch": ("bodyweight", "bench"),
    "Decline Reverse Crunch": ("bodyweight", "bench"),
}

# Martial-arts entries that need a training partner (v1.2 keeps only solo-safe drills).
PARTNER_ONLY = ("BJJ Rolling", "Muay Thai Pad Work")

exercises = sa.table(
    "exercises",
    sa.column("name", sa.String),
    sa.column("equipment", sa.String),
    sa.column("archived", sa.Boolean),
    sa.column("is_custom", sa.Boolean),
)


def _set(name: str, equipment: str, only_if: str) -> None:
    op.execute(
        exercises.update()
        .where(
            exercises.c.name == name,
            exercises.c.equipment == only_if,
            exercises.c.is_custom.is_(False),
        )
        .values(equipment=equipment)
    )


def upgrade() -> None:
    for name, (old, new) in EQUIPMENT_FIXES.items():
        _set(name, new, old)
    op.execute(
        exercises.update()
        .where(exercises.c.name.in_(PARTNER_ONLY), exercises.c.is_custom.is_(False))
        .values(archived=True)
    )


def downgrade() -> None:
    for name, (old, new) in EQUIPMENT_FIXES.items():
        _set(name, old, new)
    op.execute(
        exercises.update()
        .where(exercises.c.name.in_(PARTNER_ONLY), exercises.c.is_custom.is_(False))
        .values(archived=False)
    )
