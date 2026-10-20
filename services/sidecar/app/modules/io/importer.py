"""Turn parsed rows into ASCEND workouts and sets.

A dry run does all the work except writing, so the report the user approves is
exactly what the real import will do. Rules:

* rows are grouped into workouts by (start time, workout title);
* a workout already imported (same import key) is skipped, so re-importing a newer
  export only adds the sessions that are new;
* sets whose exercise is not in the library are skipped and reported by name;
* warm-ups are skipped unless asked for; empty sets (no reps and no time) are dropped;
* values outside what the logger accepts (e.g. 600 kg) are dropped with a warning;
* PRs are recomputed for every touched exercise, oldest first, so an imported
  best becomes the bar for future sets. Imported sets earn no XP.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Sequence
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.events import EventBus, SetImported, WorkoutsImported
from app.modules.io.formats import Format, ImportedSet
from app.modules.io.matcher import ExerciseMatcher
from app.modules.io.schemas import ImportReport
from app.modules.workouts import pr
from app.modules.workouts.activity_seed import TIME_BASED_SECTIONS
from app.modules.workouts.models import Exercise, Workout, WorkoutSet
from app.modules.workouts.service import recompute_prs

SOURCE_BY_FORMAT: dict[Format, str] = {
    "strong_csv": "strong",
    "strong_csv_2025": "strong",
    "hevy_csv": "hevy",
}
MAX_WEIGHT_KG = 500
MAX_REPS = 100
MAX_WARNINGS = 20
DEFAULT_SET_GAP = timedelta(minutes=3)


def import_key(source: str, started_at: datetime, title: str) -> str:
    return f"{source}:{started_at.isoformat()}:{title.strip()[:100]}"


def _valid(row: ImportedSet, time_based: bool) -> str | None:
    """Why a row cannot be stored, or None if it is fine."""
    if time_based:
        if not row.duration_s:
            return "no duration"
        if row.duration_s > 6 * 3600:
            return "longer than 6 h"
        return None
    if row.reps <= 0:
        return "no reps"
    if row.reps > MAX_REPS:
        return f"more than {MAX_REPS} reps"
    if row.weight_kg < 0 or row.weight_kg > MAX_WEIGHT_KG:
        return f"weight outside 0-{MAX_WEIGHT_KG} kg"
    return None


def run_import(
    db: Session,
    bus: EventBus,
    fmt: Format,
    rows: Sequence[ImportedSet],
    *,
    dry_run: bool,
    include_warmups: bool = False,
) -> ImportReport:
    source = SOURCE_BY_FORMAT[fmt]
    library = {e.name: e for e in db.scalars(select(Exercise)).all()}
    matcher = ExerciseMatcher(library)

    groups: OrderedDict[tuple[datetime, str], list[ImportedSet]] = OrderedDict()
    for row in sorted(rows, key=lambda r: (r.started_at, r.workout_title)):
        groups.setdefault((row.started_at, row.workout_title), []).append(row)

    existing = set(
        db.scalars(select(Workout.import_key).where(Workout.import_key.is_not(None))).all()
    )
    report = ImportReport(format=fmt, workouts=0, sets=0, dry_run=dry_run)
    unmatched: set[str] = set()
    touched: set[int] = set()
    written: list[tuple[WorkoutSet, Exercise]] = []
    days = []

    for (started, title), items in groups.items():
        key = import_key(source, started, title)
        if key in existing:
            report.skipped_duplicates += 1
            continue
        keep: list[tuple[ImportedSet, Exercise]] = []
        for row in items:
            if row.warmup and not include_warmups:
                report.skipped_warmups += 1
                continue
            name = matcher.match(row.exercise)
            if name is None:
                unmatched.add(row.exercise)
                continue
            report.matched_exercises.setdefault(row.exercise, name)
            exercise = library[name]
            problem = _valid(row, exercise.section in TIME_BASED_SECTIONS)
            if problem:
                if len(report.warnings) < MAX_WARNINGS:
                    report.warnings.append(
                        f"{started:%Y-%m-%d} {row.exercise} set {row.set_index}: {problem}"
                    )
                continue
            keep.append((row, exercise))
        if not keep:
            continue
        report.workouts += 1
        report.sets += len(keep)
        days.append(started.date())
        if dry_run:
            continue

        finished = items[0].finished_at or started + DEFAULT_SET_GAP * len(keep)
        workout = Workout(
            day=started.date(),
            section=keep[0][1].section,
            started_at=started,
            finished_at=finished,
            notes=title[:500],
            source=source,
            import_key=key,
        )
        db.add(workout)
        db.flush()
        span = max(finished - started, timedelta(minutes=1))
        for i, (row, exercise) in enumerate(keep):
            time_based = exercise.section in TIME_BASED_SECTIONS
            performed = started + span * (i / max(len(keep), 1))
            ws = WorkoutSet(
                workout_id=workout.id,
                exercise_id=exercise.id,
                weight_kg=0.0 if time_based else row.weight_kg,
                reps=1 if time_based else row.reps,
                rpe=row.rpe if row.rpe is None or 1 <= row.rpe <= 10 else None,
                duration_s=row.duration_s if time_based else None,
                distance_m=row.distance_m if time_based else None,
                e1rm=None if time_based else pr.e1rm_or_none(row.weight_kg, row.reps),
                performed_at=performed,
            )
            db.add(ws)
            written.append((ws, exercise))
            touched.add(exercise.id)
        db.flush()

    if unmatched:
        report.unmatched_exercises = sorted(unmatched)
    if dry_run or not written:
        return report

    for exercise_id in touched:
        recompute_prs(db, exercise_id)
    db.flush()
    for ws, exercise in written:
        bus.publish(
            db,
            SetImported(
                set_id=ws.id,
                workout_id=ws.workout_id,
                exercise_id=ws.exercise_id,
                weight_kg=ws.weight_kg,
                reps=ws.reps,
                rpe=ws.rpe,
                performed_at=ws.performed_at,
                section=exercise.section,
                duration_s=ws.duration_s,
            ),
        )
    bus.publish(
        db,
        WorkoutsImported(
            source=source,
            workouts=report.workouts,
            sets=report.sets,
            first_day=min(days) if days else None,
            last_day=max(days) if days else None,
        ),
    )
    return report
