"""Workout programs: the stored choice, the log it is read from, and today's session with
prog-v1 targets (programs-v1, ADR-0020)."""

from __future__ import annotations

import math
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.intelligence import progression as prog
from app.modules.intelligence import progression_service
from app.modules.intelligence.schemas import Why
from app.modules.workouts import equipment, programs
from app.modules.workouts.models import Exercise, PlanEnrollment, Workout, WorkoutSet
from app.modules.workouts.schemas import PlanDayOut, PlanDoneOut, PlanItemOut, PlanOut, ProgramOut


class UnknownProgram(ValueError):
    pass


def _library(db: Session) -> dict[str, Exercise]:
    return {e.name: e for e in db.scalars(select(Exercise).where(Exercise.archived.is_(False)))}


# v1.1 stored holds as "1-1" (one hold per set); v1.2 doses holds in seconds and shows an
# old 1-1 hold as this range instead of "2 x 1-1".
LEGACY_HOLD_SECONDS = (20, 30)


def _item(s: programs.Slot, lib: dict[str, Exercise]) -> PlanItemOut:
    e = lib.get(s.exercise)
    measure = e.measure if e is not None else "reps"
    lo, hi = s.rep_low, s.rep_high
    if measure == "hold" and hi <= 1:
        lo, hi = LEGACY_HOLD_SECONDS
    return PlanItemOut(
        exercise_id=e.id if e is not None else None,
        exercise=s.exercise,
        sets=s.sets,
        rep_low=lo,
        rep_high=hi,
        target_rpe=s.target_rpe,
        rest_s=s.rest_s,
        measure=measure,
        section=e.section if e is not None else None,
    )


def _day_out(day: programs.Day, lib: dict[str, Exercise]) -> PlanDayOut:
    return PlanDayOut(
        key=day.key,
        name=day.name,
        focus=day.focus,
        weekday=day.weekday,
        items=[_item(s, lib) for s in day.slots],
    )


def catalog(db: Session) -> list[ProgramOut]:
    lib = _library(db)
    allowed = equipment.allowed_for_profile(db)
    out = []
    for p in programs.PROGRAMS.values():
        fits = all(
            equipment.fits(lib[n].equipment, allowed)
            for n in programs.exercise_names(p)
            if n in lib
        )
        out.append(
            ProgramOut(
                key=p.key,
                name=p.name,
                summary=p.summary,
                level=p.level,
                equipment=p.equipment,
                section=p.section_key,
                days_per_week=p.days_per_week,
                fits_equipment=fits,
                days=[_day_out(d, lib) for d in p.days],
            )
        )
    return out


def active(db: Session) -> PlanEnrollment | None:
    return db.scalars(
        select(PlanEnrollment)
        .where(PlanEnrollment.ended_at.is_(None))
        .order_by(PlanEnrollment.id.desc())
    ).first()


def get_program(db: Session, key: str) -> programs.Program | None:
    """A built-in program, or a custom one saved with the planner ("custom-<id>")."""
    from app.modules.planner.service import get_program as planner_get

    return planner_get(db, key)


def enroll(db: Session, key: str, now: datetime) -> PlanEnrollment:
    if get_program(db, key) is None:
        raise UnknownProgram(key)
    current = active(db)
    if current is not None:
        if current.program_key == key:
            return current
        current.ended_at = now
    e = PlanEnrollment(program_key=key, started_on=now.date(), created_at=now)
    db.add(e)
    db.flush()
    from app.modules.gamification import service as game

    game.follow_plan_today(db, now)  # v1.2: today's quest follows the new program
    db.commit()
    return e


def leave(db: Session, now: datetime) -> bool:
    current = active(db)
    if current is None:
        return False
    current.ended_at = now
    db.commit()
    return True


def _finished_gym(db: Session, since: date, today: date) -> list[tuple[date, set[str]]]:
    """Finished workouts with the moves they trained. v1.2: every section counts (v1.1 read
    only gym workouts, so a bodyweight program logged under Calisthenics never advanced)."""
    rows = db.execute(
        select(Workout.id, Workout.day, Exercise.name)
        .join(WorkoutSet, WorkoutSet.workout_id == Workout.id)
        .join(Exercise, Exercise.id == WorkoutSet.exercise_id)
        .where(
            Workout.finished_at.is_not(None),
            Workout.day >= since,
            Workout.day <= today,
        )
    ).all()
    by_workout: dict[int, tuple[date, set[str]]] = {}
    for wid, day, name in rows:
        by_workout.setdefault(wid, (day, set()))[1].add(name)
    return [by_workout[k] for k in sorted(by_workout)]


def _open_sets(db: Session) -> dict[int, int]:
    """Sets per exercise in the unfinished workout, if one is open."""
    w = db.scalars(select(Workout).where(Workout.finished_at.is_(None))).first()
    out: dict[int, int] = {}
    if w is not None:
        for s in w.sets:
            out[s.exercise_id] = out.get(s.exercise_id, 0) + 1
    return out


def target_text(t: prog.Target, sets: int) -> str | None:
    """The program's sets with prog-v1's reps (or seconds), load and RPE; None when prog-v1
    has nothing to go on yet (no history), so the program's own rep zone is shown."""
    if t.seconds is not None:
        work = f"{sets} × {t.seconds} s"
    elif t.reps is not None:
        work = f"{sets} × {t.reps}"
    else:
        return None
    load = f" @ {t.weight_kg:g} kg" if t.weight_kg > 0 else ""
    rpe = f", RPE {t.rpe:g}" if t.rpe is not None else ""
    return work + load + rpe


def plan(db: Session, now: datetime) -> PlanOut | None:
    e = active(db)
    if e is None:
        return None
    p = get_program(db, e.program_key)
    if p is None:  # a program removed from the catalog in a later version, or deleted
        return None
    today = now.date()
    state = programs.plan_state(p, e.started_on, _finished_gym(db, e.started_on, today), today)
    lib = _library(db)
    nxt = _day_out(p.days[state.next_index], lib)
    open_sets = _open_sets(db)
    deload = progression_service.in_deload_week(db, now)
    for item in nxt.items:
        if deload:  # deload-v2 week: half the sets (prog-v1 also drops the RPE to 7)
            item.sets = max(1, math.ceil(item.sets / 2))
        if item.exercise_id is None or item.measure == "time":
            continue  # time-based moves keep the program's minutes
        _, t = progression_service.next_target(db, item.exercise_id, now)
        item.target = target_text(t, item.sets)
        item.target_reason = t.reason if item.target else None
        item.done_sets = open_sets.get(item.exercise_id, 0)
    return PlanOut(
        id=e.id,
        source="custom" if p.key.startswith("custom-") else "program",
        algo_version=programs.ALGO_VERSION,
        program_key=p.key,
        name=p.name,
        started_on=e.started_on,
        days_per_week=p.days_per_week,
        days=[_day_out(d, lib) for d in p.days],
        next=nxt,
        sessions_done=state.sessions_done,
        this_week_done=state.this_week_done,
        last_trained=state.last_trained,
        deload_week=deload,
        recent=[
            PlanDoneOut(day=d.day, key=p.days[d.index].key, name=p.days[d.index].name)
            for d in state.done[-5:][::-1]
        ],
        reason=state.reason + (" (deload week: half the sets at RPE 7)" if deload else ""),
        why=Why(
            formula=(
                "next = the day after the last program day you trained; a finished workout "
                f"counts as a program day when it trained at least {programs.MATCH_SHARE:.0%} "
                "of that day's exercises. Sets come from the program (halved in a deload "
                "week); reps, load and RPE per exercise come from prog-v1."
            ),
            inputs={
                "program": p.key,
                "started_on": e.started_on.isoformat(),
                "sessions_done": state.sessions_done,
                "last_trained": state.last_trained.isoformat() if state.last_trained else None,
                "next_day": nxt.key,
                "deload_week": "yes" if deload else "no",
            },
        ),
    )
