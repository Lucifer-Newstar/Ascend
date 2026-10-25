"""everyday_moves: burpee, jumping jack and wall sit (v1.3).

Revision ID: 0032
Revises: 0031

Moves people log by name that the imported library lacks. A name that already exists (a
player's own exercise) is left alone. The downgrade removes the moves no logged set uses.
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.modules.workouts.everyday_seed import MOVES
from app.modules.workouts.library import slugify

revision: str = "0032"
down_revision: str | None = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

exercises = sa.table(
    "exercises",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("equipment", sa.String),
    sa.column("section", sa.String),
    sa.column("met", sa.Float),
    sa.column("slug", sa.String),
    sa.column("measure", sa.String),
    sa.column("difficulty", sa.String),
    sa.column("pattern", sa.String),
    sa.column("instructions", sa.Text),
    sa.column("aliases", sa.Text),
    sa.column("source", sa.String),
    sa.column("field_sources", sa.Text),
)
exercise_muscles = sa.table(
    "exercise_muscles",
    sa.column("exercise_id", sa.Integer),
    sa.column("muscle", sa.String),
    sa.column("weight", sa.Float),
)
workout_sets = sa.table("workout_sets", sa.column("exercise_id", sa.Integer))

SOURCES = json.dumps({"muscles": "library", "instructions": "library", "pattern": "library"})


def upgrade() -> None:
    conn = op.get_bind()
    names = {r[0] for r in conn.execute(sa.select(exercises.c.name))}
    slugs = {r[0] for r in conn.execute(sa.select(exercises.c.slug)) if r[0]}
    for d in MOVES:
        if d.name in names:
            continue
        slug = slugify(d.name)
        if slug in slugs:
            slug = f"{slug}-move"
        new_id = conn.execute(
            exercises.insert()
            .values(
                name=d.name,
                equipment="bodyweight",
                section="calisthenics",
                met=d.met,
                slug=slug,
                measure=d.measure,
                difficulty=d.difficulty,
                pattern=d.pattern,
                instructions=json.dumps(list(d.instructions)),
                aliases=json.dumps(list(d.aliases)),
                source="ascend",
                field_sources=SOURCES,
            )
            .returning(exercises.c.id)
        ).scalar_one()
        conn.execute(
            exercise_muscles.insert(),
            [{"exercise_id": new_id, "muscle": m, "weight": w} for m, w in d.muscles.items()],
        )


def downgrade() -> None:
    conn = op.get_bind()
    used = {r[0] for r in conn.execute(sa.select(workout_sets.c.exercise_id).distinct())}
    rows = conn.execute(
        sa.select(exercises.c.id).where(
            exercises.c.name.in_([d.name for d in MOVES]), exercises.c.source == "ascend"
        )
    ).all()
    drop = [r[0] for r in rows if r[0] not in used]
    if drop:
        conn.execute(exercise_muscles.delete().where(exercise_muscles.c.exercise_id.in_(drop)))
        conn.execute(exercises.delete().where(exercises.c.id.in_(drop)))
