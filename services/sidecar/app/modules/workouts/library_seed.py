"""Data step of migration 0010: fill the exercise library (v1 of the library seed).

Runs inside Alembic with SQLAlchemy Core only, so it never depends on the ORM models
of a later version. Order:
  1. backfill the new columns on the existing ASCEND rows (slug, measure, pattern...);
  2. "Plank (60 s = 1 set)" becomes a real timed hold called "Plank";
  3. add the calisthenics progressions (calisthenics_seed.py);
  4. add free-exercise-db, merging its duplicates of ASCEND rows (library.FEDB_DUPLICATES).
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa

from app.modules.workouts.calisthenics_seed import CALISTHENICS, CALISTHENICS_SOURCE
from app.modules.workouts.library import (
    FEDB_DUPLICATES,
    FEDB_SOURCE,
    default_range,
    fedb_entries,
    normalize,
    slugify,
)

OLD_PLANK = "Plank (60 s = 1 set)"
TIME_SECTIONS = ("cardio", "martial_arts", "flexibility", "meditation")

# Movement pattern and difficulty for the 41 hand-made lifts of 0002 (time-based
# activities of 0004 get "locomotion"/"mobility"/"other" by section).
EXISTING_META: dict[str, tuple[str, str]] = {
    "Barbell Bench Press": ("push", "intermediate"),
    "Incline Barbell Bench Press": ("push", "intermediate"),
    "Dumbbell Bench Press": ("push", "beginner"),
    "Incline Dumbbell Press": ("push", "beginner"),
    "Cable Fly": ("push", "beginner"),
    "Push-up": ("push", "beginner"),
    "Chest Dip": ("push", "intermediate"),
    "Overhead Press": ("push", "intermediate"),
    "Seated Dumbbell Shoulder Press": ("push", "beginner"),
    "Lateral Raise": ("push", "beginner"),
    "Rear Delt Fly": ("pull", "beginner"),
    "Face Pull": ("pull", "beginner"),
    "Pull-up": ("pull", "intermediate"),
    "Chin-up": ("pull", "intermediate"),
    "Lat Pulldown": ("pull", "beginner"),
    "Barbell Row": ("pull", "intermediate"),
    "Seated Cable Row": ("pull", "beginner"),
    "One-arm Dumbbell Row": ("pull", "beginner"),
    "Barbell Shrug": ("pull", "beginner"),
    "Deadlift": ("hinge", "intermediate"),
    "Back Extension": ("hinge", "beginner"),
    "Barbell Curl": ("pull", "beginner"),
    "Dumbbell Curl": ("pull", "beginner"),
    "Hammer Curl": ("pull", "beginner"),
    "Triceps Pushdown": ("push", "beginner"),
    "Overhead Triceps Extension": ("push", "beginner"),
    "Close-grip Bench Press": ("push", "intermediate"),
    "Wrist Curl": ("pull", "beginner"),
    "Back Squat": ("squat", "intermediate"),
    "Front Squat": ("squat", "intermediate"),
    "Leg Press": ("squat", "beginner"),
    "Romanian Deadlift": ("hinge", "intermediate"),
    "Walking Lunge": ("lunge", "beginner"),
    "Bulgarian Split Squat": ("lunge", "intermediate"),
    "Leg Curl": ("hinge", "beginner"),
    "Leg Extension": ("squat", "beginner"),
    "Hip Thrust": ("hinge", "beginner"),
    "Standing Calf Raise": ("other", "beginner"),
    "Plank": ("isometric", "beginner"),
    OLD_PLANK: ("isometric", "beginner"),
    "Hanging Leg Raise": ("core", "intermediate"),
    "Russian Twist": ("core", "beginner"),
}
EXISTING_ALIASES: dict[str, list[str]] = {
    "Pull-up": ["pullup", "pull up", "pullups"],
    "Chin-up": ["chinup", "chin up"],
    "Push-up": ["pushup", "press-up"],
    "Chest Dip": ["dip", "parallel bar dip", "dips"],
    "Back Squat": ["squat", "barbell squat"],
    "Overhead Press": ["ohp", "military press", "shoulder press"],
    "Deadlift": ["conventional deadlift"],
    "Romanian Deadlift": ["rdl"],
    "Plank": ["front plank", "forearm plank"],
    "Hanging Leg Raise": ["hanging knee raise"],
}


def tables() -> tuple[sa.TableClause, sa.TableClause, sa.TableClause]:
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
        sa.column("mechanic", sa.String),
        sa.column("instructions", sa.Text),
        sa.column("aliases", sa.Text),
        sa.column("image", sa.String),
        sa.column("source", sa.String),
        sa.column("source_ref", sa.String),
        sa.column("field_sources", sa.Text),
        sa.column("rep_low", sa.Integer),
        sa.column("rep_high", sa.Integer),
    )
    muscles = sa.table(
        "exercise_muscles",
        sa.column("exercise_id", sa.Integer),
        sa.column("muscle", sa.String),
        sa.column("weight", sa.Float),
    )
    sets = sa.table(
        "workout_sets",
        sa.column("id", sa.Integer),
        sa.column("exercise_id", sa.Integer),
        sa.column("duration_s", sa.Integer),
    )
    return exercises, muscles, sets


def _sources(**fields: str) -> str:
    return json.dumps(fields, sort_keys=True)


def upgrade(conn: sa.Connection) -> None:
    exercises, muscles, sets = tables()
    rows = conn.execute(sa.select(exercises.c.id, exercises.c.name, exercises.c.section)).all()
    by_name: dict[str, int] = {}
    # 1 + 2: backfill existing rows
    for ex_id, name, section in rows:
        new_name = "Plank" if name == OLD_PLANK else name
        if section in TIME_SECTIONS:
            measure = "time"
            pattern = {"cardio": "locomotion", "flexibility": "mobility"}.get(section, "other")
            difficulty = "beginner"
        else:
            measure = "hold" if new_name == "Plank" else "reps"
            pattern, difficulty = EXISTING_META.get(name, ("other", "beginner"))
        low, high = default_range(measure)
        conn.execute(
            exercises.update()
            .where(exercises.c.id == ex_id)
            .values(
                name=new_name,
                slug=slugify(new_name),
                measure=measure,
                pattern=pattern,
                difficulty=difficulty,
                aliases=json.dumps(EXISTING_ALIASES.get(new_name, [])),
                instructions="[]",
                source="ascend",
                field_sources=_sources(muscles="library", pattern="library"),
                rep_low=low,
                rep_high=high,
            )
        )
        by_name[new_name] = ex_id
        if name == OLD_PLANK:
            # Old plank sets meant "one set = 60 s"; give them that duration.
            conn.execute(
                sets.update()
                .where(sets.c.exercise_id == ex_id, sets.c.duration_s.is_(None))
                .values(duration_s=60)
            )

    # 3: calisthenics progressions
    for row in CALISTHENICS:
        low, high = default_range(row["measure"])
        values: dict[str, Any] = {
            "equipment": row["equipment"],
            "section": row["section"],
            "slug": slugify(row["name"]),
            "measure": row["measure"],
            "difficulty": row["difficulty"],
            "pattern": row["pattern"],
            "instructions": json.dumps(row["instructions"]),
            "aliases": json.dumps(row["aliases"]),
            "source": CALISTHENICS_SOURCE,
            "field_sources": _sources(muscles="library", pattern="library", instructions="library"),
            "rep_low": low,
            "rep_high": high,
        }
        if row["name"] in by_name:
            ex_id = by_name[row["name"]]
            conn.execute(exercises.update().where(exercises.c.id == ex_id).values(**values))
            conn.execute(muscles.delete().where(muscles.c.exercise_id == ex_id))
        else:
            ex_id = int(
                conn.execute(
                    exercises.insert().values(name=row["name"], **values).returning(exercises.c.id)
                ).scalar_one()
            )
            by_name[row["name"]] = ex_id
        conn.execute(
            muscles.insert(),
            [{"exercise_id": ex_id, "muscle": m, "weight": w} for m, w in row["muscles"].items()],
        )

    # 4: free-exercise-db
    taken_slugs = {slugify(n) for n in by_name}
    for entry in fedb_entries():
        target = FEDB_DUPLICATES.get(entry.source_id or "")
        if target and target in by_name:
            ex_id = by_name[target]
            current = conn.execute(
                sa.select(exercises.c.instructions, exercises.c.aliases).where(
                    exercises.c.id == ex_id
                )
            ).one()
            instructions = json.loads(current.instructions or "[]") or entry.instructions
            aliases = json.loads(current.aliases or "[]")
            known = {normalize(a) for a in [target, *aliases]}
            if normalize(entry.name) not in known:
                aliases.append(entry.name)
            conn.execute(
                exercises.update()
                .where(exercises.c.id == ex_id)
                .values(
                    instructions=json.dumps(instructions),
                    aliases=json.dumps(aliases),
                    image=entry.image,
                    mechanic=entry.mechanic,
                    source_ref=entry.source_id,
                )
            )
            continue
        if entry.name in by_name or entry.slug in taken_slugs:
            continue  # same name already in the library: keep the ASCEND row
        ex_id = int(
            conn.execute(
                exercises.insert()
                .values(
                    name=entry.name,
                    equipment=entry.equipment,
                    section=entry.section,
                    met=entry.met,
                    slug=entry.slug,
                    measure=entry.measure,
                    difficulty=entry.difficulty,
                    pattern=entry.pattern,
                    mechanic=entry.mechanic,
                    instructions=json.dumps(entry.instructions),
                    aliases="[]",
                    image=entry.image,
                    source=FEDB_SOURCE,
                    source_ref=entry.source_id,
                    field_sources=_sources(
                        muscles="library", pattern="rules", instructions="library"
                    ),
                    rep_low=entry.rep_low,
                    rep_high=entry.rep_high,
                )
                .returning(exercises.c.id)
            ).scalar_one()
        )
        by_name[entry.name] = ex_id
        taken_slugs.add(entry.slug)
        if entry.muscles:
            conn.execute(
                muscles.insert(),
                [
                    {"exercise_id": ex_id, "muscle": m, "weight": w}
                    for m, w in entry.muscles.items()
                ],
            )


def downgrade(conn: sa.Connection) -> None:
    """Remove library rows that no logged set uses, and restore the old plank name."""
    exercises, muscles, sets = tables()
    used = {r[0] for r in conn.execute(sa.select(sets.c.exercise_id).distinct())}
    added = [
        r[0]
        for r in conn.execute(
            sa.select(exercises.c.id).where(
                exercises.c.source.in_([FEDB_SOURCE, CALISTHENICS_SOURCE])
            )
        )
    ]
    # Rows from 0002/0004 are also source "ascend"; keep them by name.
    from app.modules.workouts.activity_seed import ACTIVITIES
    from app.modules.workouts.seed import EXERCISES

    original = {n for n, _, _ in EXERCISES} | {a[0] for a in ACTIVITIES} | {"Plank"}
    names = dict(conn.execute(sa.select(exercises.c.id, exercises.c.name)).all())
    drop = [i for i in added if i not in used and names.get(i) not in original]
    if drop:
        conn.execute(muscles.delete().where(muscles.c.exercise_id.in_(drop)))
        conn.execute(exercises.delete().where(exercises.c.id.in_(drop)))
    conn.execute(exercises.update().where(exercises.c.name == "Plank").values(name=OLD_PLANK))
