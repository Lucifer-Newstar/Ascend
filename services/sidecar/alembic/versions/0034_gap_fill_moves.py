"""gap_fill_moves: moves and practices real users ask about (v1.4, KB gap fill).

Revision ID: 0034
Revises: 0033

Adds the entries in gap_fill_seed.py (calisthenics, gym, interval cardio, Muay Thai and
boxing drills, yoga and mobility, breathing and meditation) and writes steps for the
ASCEND rows that shipped with none (Box Breathing, Shadowboxing, Pigeon Pose...). A name
that already exists (a player's own exercise) is left alone, and steps are only written
where the row's instructions are still empty. The downgrade removes the added entries no
logged set uses and empties the steps it wrote.
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.modules.workouts.gap_fill_seed import ENTRIES, INSTRUCTIONS
from app.modules.workouts.library import slugify

revision: str = "0034"
down_revision: str | None = "0033"
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


def _empty(value: str | None) -> bool:
    return not value or value.strip() in ("", "[]", "null")


def upgrade() -> None:
    conn = op.get_bind()
    names = {r[0] for r in conn.execute(sa.select(exercises.c.name))}
    slugs = {r[0] for r in conn.execute(sa.select(exercises.c.slug)) if r[0]}
    for e in ENTRIES:
        if e.name in names:
            continue
        slug = slugify(e.name)
        if slug in slugs:
            slug = f"{slug}-move"
        slugs.add(slug)
        new_id = conn.execute(
            exercises.insert()
            .values(
                name=e.name,
                equipment=e.equipment,
                section=e.section,
                met=e.met,
                slug=slug,
                measure=e.measure,
                difficulty=e.difficulty,
                pattern=e.pattern,
                instructions=json.dumps(list(e.instructions)),
                aliases=json.dumps(list(e.aliases)),
                source="ascend",
                field_sources=SOURCES,
            )
            .returning(exercises.c.id)
        ).scalar_one()
        if e.muscles:
            conn.execute(
                exercise_muscles.insert(),
                [{"exercise_id": new_id, "muscle": m, "weight": w} for m, w in e.muscles.items()],
            )
    rows = conn.execute(
        sa.select(exercises.c.id, exercises.c.name, exercises.c.instructions).where(
            exercises.c.name.in_(list(INSTRUCTIONS))
        )
    ).all()
    for row_id, name, current in rows:
        if _empty(current):
            conn.execute(
                exercises.update()
                .where(exercises.c.id == row_id)
                .values(instructions=json.dumps(list(INSTRUCTIONS[name])))
            )


def downgrade() -> None:
    conn = op.get_bind()
    for name, steps in INSTRUCTIONS.items():
        conn.execute(
            exercises.update()
            .where(exercises.c.name == name, exercises.c.instructions == json.dumps(list(steps)))
            .values(instructions="[]")
        )
    used = {r[0] for r in conn.execute(sa.select(workout_sets.c.exercise_id).distinct())}
    rows = conn.execute(
        sa.select(exercises.c.id).where(
            exercises.c.name.in_([e.name for e in ENTRIES]), exercises.c.source == "ascend"
        )
    ).all()
    drop = [r[0] for r in rows if r[0] not in used]
    if drop:
        conn.execute(exercise_muscles.delete().where(exercise_muscles.c.exercise_id.in_(drop)))
        conn.execute(exercises.delete().where(exercises.c.id.in_(drop)))
