"""seed cardio, martial arts, flexibility and meditation activities

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-20

Also tags the bodyweight moves from 0002 as `calisthenics`.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.modules.workouts.activity_seed import ACTIVITIES

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

exercises = sa.table(
    "exercises",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("equipment", sa.String),
    sa.column("section", sa.String),
    sa.column("met", sa.Float),
)
exercise_muscles = sa.table(
    "exercise_muscles",
    sa.column("exercise_id", sa.Integer),
    sa.column("muscle", sa.String),
    sa.column("weight", sa.Float),
)


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        exercises.update()
        .where(exercises.c.equipment == "bodyweight")
        .values(section="calisthenics")
    )
    for name, section, equipment, met, muscles in ACTIVITIES:
        conn.execute(
            exercises.insert().values(name=name, equipment=equipment, section=section, met=met)
        )
        new_id = conn.execute(
            sa.select(exercises.c.id).where(exercises.c.name == name)
        ).scalar_one()
        if muscles:
            op.bulk_insert(
                exercise_muscles,
                [{"exercise_id": new_id, "muscle": m, "weight": w} for m, w in muscles.items()],
            )


def downgrade() -> None:
    conn = op.get_bind()
    names = [a[0] for a in ACTIVITIES]
    ids = [
        row[0] for row in conn.execute(sa.select(exercises.c.id).where(exercises.c.name.in_(names)))
    ]
    if ids:
        conn.execute(exercise_muscles.delete().where(exercise_muscles.c.exercise_id.in_(ids)))
        conn.execute(exercises.delete().where(exercises.c.id.in_(ids)))
    conn.execute(
        exercises.update().where(exercises.c.section == "calisthenics").values(section="gym")
    )
