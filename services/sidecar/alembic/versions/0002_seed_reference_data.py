"""seed exercise library and Indian food table

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-20

Reference data ships as a data migration so every install (and every test
database) starts with the same library. User data is never touched here.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.modules.nutrition.seed import FOODS, SOURCE
from app.modules.workouts.seed import EXERCISES

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

exercises = sa.table(
    "exercises", sa.column("id", sa.Integer), sa.column("name", sa.String),
    sa.column("equipment", sa.String),
)
exercise_muscles = sa.table(
    "exercise_muscles", sa.column("exercise_id", sa.Integer), sa.column("muscle", sa.String),
    sa.column("weight", sa.Float),
)
foods = sa.table(
    "foods", sa.column("name", sa.String), sa.column("portion_label", sa.String),
    sa.column("portion_g", sa.Float), sa.column("kcal", sa.Float),
    sa.column("protein_g", sa.Float), sa.column("carbs_g", sa.Float),
    sa.column("fat_g", sa.Float), sa.column("source", sa.String),
)


def upgrade() -> None:
    op.bulk_insert(
        exercises,
        [{"id": i, "name": n, "equipment": eq} for i, (n, eq, _) in enumerate(EXERCISES, start=1)],
    )
    op.bulk_insert(
        exercise_muscles,
        [
            {"exercise_id": i, "muscle": m, "weight": wt}
            for i, (_, _, muscles) in enumerate(EXERCISES, start=1)
            for m, wt in muscles.items()
        ],
    )
    op.bulk_insert(
        foods,
        [
            {"name": n, "portion_label": pl, "portion_g": pg, "kcal": k, "protein_g": p,
             "carbs_g": c, "fat_g": f, "source": SOURCE}
            for (n, pl, pg, k, p, c, f) in FOODS
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM exercise_muscles")
    op.execute("DELETE FROM exercises")
    op.execute("DELETE FROM foods")
