"""Reads the database for prog-v1 (progression.py) and records what the user decided.

next_target(db, exercise_id, now) gathers: the exercise's finished sessions (120 days),
the recovery-v2 readiness of its primary muscles, a "keep mine" decision in the last 7
days, the open skill-tree criterion it serves and whether this is a deload week."""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.intelligence import progression as prog
from app.modules.intelligence import recovery as rec
from app.modules.intelligence import recovery_service
from app.modules.intelligence.models import ProgressionDecision
from app.modules.workouts.models import Exercise, Workout, WorkoutSet

HISTORY_DAYS = 120
DELOAD_RPE = 7.0


class ExerciseMissing(Exception):
    pass


def exercise_info(e: Exercise) -> prog.ExerciseInfo:
    return prog.ExerciseInfo(
        name=e.name,
        equipment=e.equipment,
        measure=e.measure,
        mechanic=e.mechanic,
        pattern=e.pattern,
        rep_low=e.rep_low,
        rep_high=e.rep_high,
    )


def history(
    db: Session, exercise_id: int, now: datetime, days: int = HISTORY_DAYS
) -> list[prog.SessionRec]:
    """Finished sessions of one exercise, oldest first (the open session is not history)."""
    rows = db.execute(
        select(WorkoutSet, Workout.started_at)
        .join(Workout, Workout.id == WorkoutSet.workout_id)
        .where(
            WorkoutSet.exercise_id == exercise_id,
            Workout.finished_at.is_not(None),
            Workout.started_at >= now - timedelta(days=days),
            Workout.started_at <= now,
        )
        .order_by(Workout.started_at, WorkoutSet.performed_at, WorkoutSet.id)
    ).all()
    by: dict[int, tuple[datetime, list[prog.SetRec]]] = {}
    for ws, started in rows:
        by.setdefault(ws.workout_id, (started, []))[1].append(
            prog.SetRec(ws.reps, ws.weight_kg, ws.rpe, ws.duration_s)
        )
    return [prog.SessionRec(at, tuple(sets)) for at, sets in by.values()]


def primary_readiness(
    db: Session,
    e: Exercise,
    now: datetime,
    recovery: list[rec.MuscleRecovery] | None = None,
) -> tuple[float | None, str | None]:
    """The readiness of the move's main muscle. `recovery` is the state list when the
    caller already read it (a program day reads it once for all its moves)."""
    prim = [m.muscle for m in e.muscles if m.weight >= 1.0] or [
        m.muscle for m in e.muscles if m.weight >= 0.5
    ]
    if not prim:
        return None, None
    states = {
        m.key: m for m in (recovery if recovery is not None else recovery_service.states(db, now))
    }
    worst = min((states[m] for m in prim if m in states), key=lambda m: m.readiness, default=None)
    if worst is None or worst.last_trained is None:
        return None, None
    return worst.readiness, worst.label


def kept_at(db: Session, exercise_id: int, now: datetime) -> datetime | None:
    row = db.scalars(
        select(ProgressionDecision)
        .where(
            ProgressionDecision.exercise_id == exercise_id,
            ProgressionDecision.decided_at >= now - timedelta(days=prog.KEEP_DAYS),
            ProgressionDecision.decided_at <= now,
        )
        .order_by(ProgressionDecision.decided_at.desc(), ProgressionDecision.id.desc())
        .limit(1)
    ).first()
    return row.decided_at if row is not None and row.choice == "kept" else None


def skill_goal(db: Session, e: Exercise, now: datetime) -> prog.SkillGoal | None:
    """The open criterion this exercise must show for a step still to unlock (open steps
    first, then the one closest to done)."""
    from app.modules.skills import service as skills
    from app.modules.skills.custom import all_skills

    best: tuple[tuple[bool, float], prog.SkillGoal] | None = None
    ex = None
    for skill in all_skills(db):
        if not any(c.exercise == e.name for s in skill.steps for c in s.unlock):
            continue
        ex = ex or skills.exercises_by_name(db)
        res = skills._evaluate_one(db, skill, now, ex)
        # Steps still to unlock; one whose earlier steps are open ranks first, but a locked
        # step still sets the goal for the exercise you are training now.
        todo = [s for s in res.steps if s.status != "unlocked"]
        for step, c in ((s, c) for s in todo for c in s.criteria):
            if c.met or c.criterion.exercise != e.name:
                continue
            goal = prog.SkillGoal(
                skill_name=skill.name,
                step_name=step.step.name,
                sets=c.criterion.sets,
                target=c.criterion.target,
                is_hold=c.criterion.is_hold,
                added_kg=c.criterion.added_kg,
                sessions_met=c.sessions_met,
            )
            rank = (step.status == "next", c.pct)
            if best is None or rank > best[0]:
                best = (rank, goal)
    return best[1] if best else None


def in_deload_week(db: Session, now: datetime) -> bool:
    from app.modules.workouts import deload, deload_service

    raw = deload_service.progress.get_setting(db, deload_service.DELOAD_SETTING, "")
    return bool(raw) and raw == deload.week_start(now.date()).isoformat()


def deloaded(t: prog.Target) -> prog.Target:
    """Deload week (deload-v1 guidance): same load, about half the sets, RPE 7."""
    if t.kind == "none" or t.change == "first":
        return t
    sets = max(1, math.ceil(t.sets / 2))
    facts = dict(t.facts)
    facts.update({"sets": sets, "target_rpe": DELOAD_RPE})
    return replace(
        t,
        sets=sets,
        rpe=DELOAD_RPE,
        change="hold",
        reason="deload_week",
        why=f"Deload week: same numbers, {sets} set{'s' if sets != 1 else ''}, stop at RPE 7.",
        facts=facts,
    )


def next_target(
    db: Session,
    exercise_id: int,
    now: datetime,
    recovery: list[rec.MuscleRecovery] | None = None,
    program_range: tuple[int, int] | None = None,
) -> tuple[Exercise, prog.Target]:
    """`program_range`: the rep range the followed program gives this move (see
    programs_service.program_rep_ranges); it replaces the library's range for reps moves,
    so the Train card, Today and the logger's suggestion agree with the program."""
    e = db.get(Exercise, exercise_id)
    if e is None:
        raise ExerciseMissing(f"exercise {exercise_id} not found")
    hist = history(db, exercise_id, now)
    readiness, muscle = primary_readiness(db, e, now, recovery) if hist else (None, None)
    info = exercise_info(e)
    if program_range is not None and e.measure == "reps":
        info = replace(
            info,
            rep_low=program_range[0],
            rep_high=program_range[1],
            range_source="your program's range",
        )
    t = prog.next_target(
        info,
        hist,
        now,
        readiness=readiness,
        readiness_muscle=muscle,
        kept_at=kept_at(db, exercise_id, now),
        skill=skill_goal(db, e, now) if e.equipment in BODYWEIGHT or e.measure == "hold" else None,
    )
    if in_deload_week(db, now):
        t = deloaded(t)
    return e, t


BODYWEIGHT = {"bodyweight", "bar", "rings", "parallettes", "none", "band", "other"}


def stalled_lifts(db: Session, now: datetime, days: int = 14) -> list[tuple[Exercise, prog.Target]]:
    """Exercises trained in the last `days` whose target says stalled (for deload-v2)."""
    ids = db.scalars(
        select(WorkoutSet.exercise_id)
        .join(Workout, Workout.id == WorkoutSet.workout_id)
        .where(Workout.finished_at.is_not(None), Workout.started_at >= now - timedelta(days=days))
        .distinct()
    ).all()
    out = []
    for i in sorted(ids):
        e = db.get(Exercise, i)
        if e is None or e.measure == "time":
            continue
        t = prog.next_target(exercise_info(e), history(db, i, now), now)
        if t.stall.stalled:
            out.append((e, t))
    return out


def decide(
    db: Session, exercise_id: int, choice: str, now: datetime, target: prog.Target
) -> ProgressionDecision:
    row = ProgressionDecision(
        exercise_id=exercise_id,
        decided_at=now,
        choice=choice,
        reason=target.reason,
        target_json=json.dumps(
            {
                "sets": target.sets,
                "reps": target.reps,
                "seconds": target.seconds,
                "weight_kg": target.weight_kg,
                "rpe": target.rpe,
            }
        ),
        algo_version=target.algo_version,
    )
    db.add(row)
    db.flush()
    return row


def decisions(db: Session, exercise_id: int, limit: int = 20) -> Sequence[ProgressionDecision]:
    return db.scalars(
        select(ProgressionDecision)
        .where(ProgressionDecision.exercise_id == exercise_id)
        .order_by(ProgressionDecision.decided_at.desc(), ProgressionDecision.id.desc())
        .limit(limit)
    ).all()
