"""Workout logging use-cases. Side effects (XP, muscle load, quests) happen in
event handlers owned by other modules, never here."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.events import EventBus, SetDeleted, SetLogged, SetUpdated, WorkoutLogged
from app.modules.gamification.formulas import HARD_SET_RPE
from app.modules.workouts import library, pr
from app.modules.workouts.activity_seed import TIME_BASED_SECTIONS
from app.modules.workouts.models import Exercise, ExerciseMuscle, Workout, WorkoutSet
from app.modules.workouts.schemas import (
    AttributionOut,
    ExerciseDetail,
    ExerciseOut,
    MuscleWeight,
    PROut,
    SetIn,
    SetOut,
    SetPatch,
    SkillLinkOut,
    WorkoutOut,
    WorkoutSummary,
)


class NotFound(Exception):
    pass


class Conflict(Exception):
    pass


class Invalid(Exception):
    """The request is well-formed but wrong for this exercise (mapped to 422)."""


@dataclass(frozen=True)
class ExerciseFilter:
    q: str = ""
    section: str | None = None
    muscle: str | None = None
    equipment: str | None = None
    difficulty: str | None = None
    custom: bool | None = None
    include_archived: bool = False


def list_exercises(
    db: Session, q: str = "", section: str | None = None, f: ExerciseFilter | None = None
) -> list[Exercise]:
    """Library search. `q` matches the name or an alias, ignoring case, hyphens and
    plurals ("pullups" finds "Pull-up")."""
    f = f or ExerciseFilter(q=q, section=section)
    stmt = select(Exercise).order_by(Exercise.name)
    if f.section:
        stmt = stmt.where(Exercise.section == f.section)
    if f.equipment:
        stmt = stmt.where(Exercise.equipment == f.equipment)
    if f.difficulty:
        stmt = stmt.where(Exercise.difficulty == f.difficulty)
    if f.custom is not None:
        stmt = stmt.where(Exercise.is_custom.is_(f.custom))
    if not f.include_archived:
        stmt = stmt.where(Exercise.archived.is_(False))
    if f.muscle:
        stmt = stmt.where(
            Exercise.id.in_(
                select(ExerciseMuscle.exercise_id).where(
                    ExerciseMuscle.muscle == f.muscle, ExerciseMuscle.weight >= 0.5
                )
            )
        )
    rows = list(db.scalars(stmt).all())
    if f.q.strip():
        rows = [e for e in rows if library.matches_query(f.q, e.name, e.aliases)]
    return rows


def exercise_out(e: Exercise) -> ExerciseOut:
    return ExerciseOut(
        id=e.id,
        name=e.name,
        equipment=e.equipment,
        section=e.section,
        met=e.met,
        time_based=e.section in TIME_BASED_SECTIONS,
        muscles=[
            MuscleWeight(muscle=m.muscle, weight=m.weight)
            for m in sorted(e.muscles, key=lambda m: (-m.weight, m.muscle))
        ],
        slug=e.slug,
        measure=e.measure,
        difficulty=e.difficulty,
        pattern=e.pattern,
        image=e.image,
        source=e.source,
        is_custom=e.is_custom,
        aliases=e.aliases,
    )


# Skill trees register a lookup here (exercise id -> links) so this module never imports
# the skills module; see skills/service.py.
SkillLinker = Callable[[Session, Exercise], list[SkillLinkOut]]
_skill_linkers: list[SkillLinker] = []


def register_skill_linker(fn: SkillLinker) -> None:
    if fn not in _skill_linkers:
        _skill_linkers.append(fn)


def exercise_detail(db: Session, exercise_id: int) -> ExerciseDetail:
    e = db.get(Exercise, exercise_id)
    if e is None:
        raise NotFound(f"exercise {exercise_id} not found")
    links: list[SkillLinkOut] = []
    for linker in _skill_linkers:
        links.extend(linker(db, e))
    logged = int(
        db.scalar(select(func.count(WorkoutSet.id)).where(WorkoutSet.exercise_id == e.id)) or 0
    )
    return ExerciseDetail(
        **exercise_out(e).model_dump(),
        instructions=e.instructions,
        mechanic=e.mechanic,
        rep_low=e.rep_low,
        rep_high=e.rep_high,
        field_sources=e.field_sources,
        attribution=[AttributionOut(**a) for a in e.attribution],
        source_ref=e.source_ref,
        created_at=e.created_at,
        skills=links,
        sets_logged=logged,
    )


def set_out(s: WorkoutSet) -> SetOut:
    return SetOut(
        id=s.id,
        exercise_id=s.exercise_id,
        exercise_name=s.exercise.name,
        weight_kg=s.weight_kg,
        reps=s.reps,
        rpe=s.rpe,
        duration_s=s.duration_s,
        distance_m=s.distance_m,
        avg_hr=s.avg_hr,
        e1rm=s.e1rm,
        is_pr=s.is_pr,
        performed_at=s.performed_at,
    )


def workout_out(w: Workout) -> WorkoutOut:
    return WorkoutOut(
        id=w.id,
        day=w.day,
        section=w.section,
        started_at=w.started_at,
        finished_at=w.finished_at,
        sets=[set_out(s) for s in w.sets],
        source=w.source,
        title=w.notes if w.source != "app" else "",
    )


def start_workout(db: Session, now: datetime, section: str = "gym") -> Workout:
    workout = Workout(day=now.date(), started_at=now, section=section)
    db.add(workout)
    db.flush()
    return workout


def active_workout(db: Session) -> Workout | None:
    stmt = select(Workout).where(Workout.finished_at.is_(None)).order_by(Workout.id.desc())
    return db.scalars(stmt).first()


def get_workout(db: Session, workout_id: int) -> Workout:
    workout = db.get(Workout, workout_id)
    if workout is None:
        raise NotFound(f"workout {workout_id} not found")
    return workout


def best_e1rm(db: Session, exercise_id: int) -> float | None:
    return db.scalar(select(func.max(WorkoutSet.e1rm)).where(WorkoutSet.exercise_id == exercise_id))


def log_set(
    db: Session, bus: EventBus, workout_id: int, data: SetIn, now: datetime
) -> tuple[WorkoutSet, float | None]:
    workout = get_workout(db, workout_id)
    if workout.finished_at is not None:
        raise Conflict("workout already finished")
    exercise = db.get(Exercise, data.exercise_id)
    if exercise is None:
        raise NotFound(f"exercise {data.exercise_id} not found")
    time_based = exercise.section in TIME_BASED_SECTIONS
    if time_based and not data.duration_s:
        raise Invalid(f"{exercise.name} is logged by time: send duration_s")
    if not workout.sets and workout.section != exercise.section:
        # A session takes the section of its first set (a run started from Gym is cardio).
        workout.section = exercise.section

    # e1RM/PR only make sense for loaded lifts.
    e1rm = None if time_based else pr.e1rm_or_none(data.weight_kg, data.reps)
    previous = best_e1rm(db, data.exercise_id)
    row = WorkoutSet(
        workout_id=workout.id,
        exercise_id=data.exercise_id,
        weight_kg=data.weight_kg,
        reps=data.reps,
        rpe=data.rpe,
        duration_s=data.duration_s,
        distance_m=data.distance_m,
        avg_hr=data.avg_hr,
        e1rm=e1rm,
        is_pr=pr.is_new_pr(e1rm, previous),
        performed_at=now,
    )
    # Append through the relationship so a session that already loaded `workout.sets`
    # sees the new set (the seeder and other multi-step callers share one session).
    workout.sets.append(row)
    db.flush()
    bus.publish(
        db,
        SetLogged(
            set_id=row.id,
            workout_id=workout.id,
            exercise_id=row.exercise_id,
            weight_kg=row.weight_kg,
            reps=row.reps,
            rpe=row.rpe,
            performed_at=now,
            is_pr=row.is_pr,
            section=exercise.section,
            duration_s=row.duration_s,
        ),
    )
    db.refresh(row)
    return row, previous


def finish_workout(
    db: Session, bus: EventBus, workout_id: int, now: datetime
) -> tuple[Workout, float, int]:
    workout = get_workout(db, workout_id)
    if workout.finished_at is not None:
        raise Conflict("workout already finished")
    if not workout.sets:
        raise Conflict("log at least one set before finishing")
    workout.finished_at = now
    minutes = min(180.0, (now - workout.started_at).total_seconds() / 60)
    hard = sum(1 for s in workout.sets if s.rpe is None or s.rpe >= HARD_SET_RPE)
    db.flush()
    bus.publish(
        db,
        WorkoutLogged(
            workout_id=workout.id, day=workout.day, hard_sets=hard, active_minutes=round(minutes, 1)
        ),
    )
    return workout, round(minutes, 1), hard


@dataclass(frozen=True)
class WorkoutFilters:
    section: str | None = None
    source: str | None = None
    since: date | None = None
    until: date | None = None


def list_workouts(
    db: Session,
    limit: int = 20,
    before: datetime | None = None,
    filters: WorkoutFilters | None = None,
) -> list[WorkoutSummary]:
    """Finished and active workouts, newest first. `before` is the started_at of the
    last item on the previous page (keyset pagination: stable while new rows arrive)."""
    from app.modules.gamification import service as game

    stmt = select(Workout).order_by(Workout.started_at.desc(), Workout.id.desc()).limit(limit)
    if before is not None:
        stmt = stmt.where(Workout.started_at < before)
    f = filters or WorkoutFilters()
    if f.section is not None:
        stmt = stmt.where(Workout.section == f.section)
    if f.source is not None:
        stmt = stmt.where(Workout.source == f.source)
    if f.since is not None:
        stmt = stmt.where(Workout.day >= f.since)
    if f.until is not None:
        stmt = stmt.where(Workout.day <= f.until)
    out: list[WorkoutSummary] = []
    for w in db.scalars(stmt).all():
        xp = game.xp_for_refs(db, sources=("session",), ref_id=w.id) + sum(
            game.xp_for_refs(db, sources=("set", "pr"), ref_id=s.id) for s in w.sets
        )
        out.append(
            WorkoutSummary(
                id=w.id,
                day=w.day,
                section=w.section,
                started_at=w.started_at,
                finished_at=w.finished_at,
                sets=len(w.sets),
                volume_kg=round(sum(s.weight_kg * s.reps for s in w.sets), 1),
                xp=xp,
                source=w.source,
                title=w.notes if w.source != "app" else "",
            )
        )
    return out


def _get_set(db: Session, workout_id: int, set_id: int) -> WorkoutSet:
    row = db.get(WorkoutSet, set_id)
    if row is None or row.workout_id != workout_id:
        raise NotFound(f"set {set_id} not found in workout {workout_id}")
    return row


def recompute_prs(db: Session, exercise_id: int) -> None:
    """Re-derive e1RM and the PR flag for every set of one exercise, oldest first.

    Needed after an edit or delete: fixing a typo (100 kg instead of 10 kg) must
    also clear the false PR it created and restore later PRs it masked.
    """
    rows = db.scalars(
        select(WorkoutSet)
        .where(WorkoutSet.exercise_id == exercise_id)
        .order_by(WorkoutSet.performed_at, WorkoutSet.id)
    ).all()
    best: float | None = None
    for row in rows:
        row.e1rm = pr.e1rm_or_none(row.weight_kg, row.reps)
        row.is_pr = pr.is_new_pr(row.e1rm, best)
        if row.e1rm is not None and (best is None or row.e1rm > best):
            best = row.e1rm


def update_set(
    db: Session, bus: EventBus, workout_id: int, set_id: int, patch: SetPatch
) -> WorkoutSet:
    row = _get_set(db, workout_id, set_id)
    changes = patch.model_dump(exclude_unset=True)
    for key, value in changes.items():
        if key in ("weight_kg", "reps") and value is None:
            continue  # cannot null a required field; ignore
        setattr(row, key, value)
    db.flush()
    recompute_prs(db, row.exercise_id)
    db.flush()
    bus.publish(
        db,
        SetUpdated(
            set_id=row.id,
            workout_id=row.workout_id,
            exercise_id=row.exercise_id,
            weight_kg=row.weight_kg,
            reps=row.reps,
            rpe=row.rpe,
            performed_at=row.performed_at,
            section=row.exercise.section,
            duration_s=row.duration_s,
        ),
    )
    db.refresh(row)
    return row


def delete_set(db: Session, bus: EventBus, workout_id: int, set_id: int) -> None:
    row = _get_set(db, workout_id, set_id)
    exercise_id = row.exercise_id
    bus.publish(db, SetDeleted(set_id=row.id, workout_id=workout_id, exercise_id=exercise_id))
    db.delete(row)
    db.flush()
    recompute_prs(db, exercise_id)


def personal_records(db: Session, exercise_id: int | None = None) -> list[PROut]:
    """Current best e1RM per exercise (earliest set wins a tie), best first."""
    stmt = select(WorkoutSet).where(WorkoutSet.e1rm.is_not(None))
    if exercise_id is not None:
        stmt = stmt.where(WorkoutSet.exercise_id == exercise_id)
    best: dict[int, WorkoutSet] = {}
    for s in db.scalars(stmt.order_by(WorkoutSet.performed_at, WorkoutSet.id)).all():
        current = best.get(s.exercise_id)
        if current is None or (s.e1rm or 0) > (current.e1rm or 0) + 1e-9:
            best[s.exercise_id] = s
    rows = sorted(best.values(), key=lambda s: -(s.e1rm or 0))
    return [
        PROut(
            exercise_id=s.exercise_id,
            exercise=s.exercise.name,
            value=s.e1rm or 0.0,
            weight_kg=s.weight_kg,
            reps=s.reps,
            algo_version=pr.FORMULA_VERSION,
            achieved_at=s.performed_at,
            set_id=s.id,
        )
        for s in rows
    ]
