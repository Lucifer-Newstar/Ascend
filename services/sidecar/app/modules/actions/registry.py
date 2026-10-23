"""actions-v1: the fixed allowlist of in-app actions.

Each action is a typed parameter model plus three functions over existing services:
describe (what will change, shown on the confirm card), execute and, where possible, undo.
No action runs SQL, touches files or the network directly; they call the same services the
pages use. Nothing executes without a confirm call; destructive actions also need a word
typed by the user.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.events import EventBus
from app.modules.nutrition import service as nutrition
from app.modules.nutrition.schemas import MealIn, MealItemIn
from app.modules.progress import body
from app.modules.progress.schemas import BodyMetricIn
from app.modules.workouts import programs_service
from app.modules.workouts import service as workouts
from app.modules.workouts.models import Exercise
from app.modules.workouts.schemas import SetIn

ACTIONS_VERSION = "actions-v1"
Risk = Literal["low", "normal", "destructive"]


class ActionError(Exception):
    """A proposal that can't run (unknown exercise, food or program...)."""


# --- parameter models -----------------------------------------------------------------


class LogSetP(BaseModel):
    exercise: str = Field(min_length=1, max_length=80)
    reps: int = Field(ge=1, le=100)
    weight_kg: float = Field(default=0, ge=0, le=500)
    sets: int = Field(default=1, ge=1, le=10)
    rpe: float | None = Field(default=None, ge=1, le=10)


class LogHoldP(BaseModel):
    exercise: str = Field(min_length=1, max_length=80)
    seconds: int = Field(ge=1, le=3600)
    rpe: float | None = Field(default=None, ge=1, le=10)


class LogWeightP(BaseModel):
    weight_kg: float = Field(ge=20, le=300)


class LogMealP(BaseModel):
    food: str = Field(min_length=1, max_length=80)
    portions: float = Field(default=1, gt=0, le=20)
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"] = "snack"


class FollowProgramP(BaseModel):
    program: str = Field(min_length=1, max_length=80)


class EraseDataP(BaseModel):
    keep_preferences: bool = True


# --- name resolution ------------------------------------------------------------------

COMMON_EXERCISES = {
    "bench": "Barbell Bench Press",
    "bench press": "Barbell Bench Press",
    "squat": "Back Squat",
    "squats": "Back Squat",
    "deadlifts": "Deadlift",
    "ohp": "Overhead Press",
    "pullup": "Pull-up",
    "pull up": "Pull-up",
    "pull ups": "Pull-up",
    "pullups": "Pull-up",
    "pushup": "Push-up",
    "push up": "Push-up",
    "push ups": "Push-up",
    "pushups": "Push-up",
    "chinup": "Chin-up",
    "chin up": "Chin-up",
}
PROGRAM_ALIASES = {
    "ppl": "ppl_6",
    "push pull legs": "ppl_6",
    "push/pull/legs": "ppl_6",
    "upper lower": "upper_lower_4",
    "upper/lower": "upper_lower_4",
    "full body": "full_body_3",
    "home": "home_full_body_3",
    "home full body": "home_full_body_3",
    "bodyweight starter": "bodyweight_starter_3",
    "starter": "bodyweight_starter_3",
    "bar starter": "bar_floor_starter_3",
    "bar and floor": "bar_floor_starter_3",
}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def resolve_exercise(db: Session, query: str, strict: bool = False) -> Exercise:
    """An exercise by name, plural, alias or (unless `strict`) a name containing the query."""
    q = _norm(query)
    q = _norm(COMMON_EXERCISES.get(q, q))
    rows = [e for e in db.scalars(select(Exercise).where(Exercise.archived.is_(False)))]
    names = {_norm(e.name): e for e in rows}
    for cand in (q, q[:-1] if q.endswith("s") else q, q[:-2] if q.endswith("es") else q):
        if cand in names:
            return names[cand]
    for e in rows:
        if any(_norm(a) == q for a in e.aliases):
            return e
    hits = [] if strict else [e for k, e in names.items() if q in k]
    if hits:
        return min(hits, key=lambda e: (e.section != "gym", len(e.name)))
    raise ActionError(f"I couldn't find an exercise called \u201c{query}\u201d.")


def resolve_food(db: Session, query: str) -> tuple[int, str]:
    q = query.strip()
    for cand in (q, q[:-1] if q.endswith("s") else q):
        foods = nutrition.search_foods(db, cand, 5)
        if foods:
            best = min(foods, key=lambda f: len(f.name))
            return best.id, best.name
    raise ActionError(f"\u201c{query}\u201d isn't in the food table.")


def resolve_program(db: Session, query: str) -> tuple[str, str]:
    q = _norm(query)
    key = PROGRAM_ALIASES.get(q)
    catalog = programs_service.catalog(db)
    for p in catalog:
        if p.key == key or _norm(p.name) == q or (len(q) >= 3 and q in _norm(p.name)):
            return p.key, p.name
    from app.modules.planner import service as planner

    for c in planner.list_programs(db):
        if _norm(c.name) == q or (len(q) >= 3 and q in _norm(c.name)):
            return c.key, c.name
    raise ActionError(f"I don't know a program called \u201c{query}\u201d.")


def _kg(x: float) -> str:
    return f"{x:g} kg"


# --- the allowlist --------------------------------------------------------------------

Describe = Callable[[Session, Any], list[str]]
Execute = Callable[[Session, EventBus, datetime, Any], tuple[dict[str, Any], dict[str, Any] | None]]
Undo = Callable[[Session, EventBus, datetime, dict[str, Any]], None]


@dataclass(frozen=True)
class Spec:
    kind: str
    label: str
    risk: Risk
    params: type[BaseModel]
    describe: Describe
    execute: Execute
    undo: Undo | None = None
    confirm_word: str | None = None  # destructive: the word the user must type


def _workout_for(db: Session, now: datetime, ex: Exercise) -> int:
    w = workouts.active_workout(db)
    if w is None or w.day != now.date():
        w = workouts.start_workout(
            db, now, ex.section if ex.section in ("gym", "calisthenics") else "gym"
        )
    return w.id


def _describe_set(db: Session, p: LogSetP) -> list[str]:
    ex = resolve_exercise(db, p.exercise)
    load = _kg(p.weight_kg) if p.weight_kg else "bodyweight"
    rpe = f" at RPE {p.rpe:g}" if p.rpe else ""
    return [f"Log {p.sets} \u00d7 {p.reps} {ex.name}, {load}{rpe}, in today's session."]


def _exec_set(
    db: Session, bus: EventBus, now: datetime, p: LogSetP
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    ex = resolve_exercise(db, p.exercise)
    wid = _workout_for(db, now, ex)
    ids = []
    for _ in range(p.sets):
        row, _prev = workouts.log_set(
            db,
            bus,
            wid,
            SetIn(exercise_id=ex.id, weight_kg=p.weight_kg, reps=p.reps, rpe=p.rpe),
            now,
        )
        ids.append(row.id)
    return {"exercise": ex.name, "set_ids": ids, "workout_id": wid}, {
        "workout_id": wid,
        "set_ids": ids,
    }


def _undo_sets(db: Session, bus: EventBus, now: datetime, u: dict[str, Any]) -> None:
    for sid in u["set_ids"]:
        try:
            workouts.delete_set(db, bus, u["workout_id"], sid)
        except workouts.NotFound:
            continue


def _describe_hold(db: Session, p: LogHoldP) -> list[str]:
    ex = resolve_exercise(db, p.exercise)
    return [f"Log a {p.seconds} s {ex.name} hold in today's session."]


def _exec_hold(
    db: Session, bus: EventBus, now: datetime, p: LogHoldP
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    ex = resolve_exercise(db, p.exercise)
    wid = _workout_for(db, now, ex)
    row, _ = workouts.log_set(
        db, bus, wid, SetIn(exercise_id=ex.id, duration_s=p.seconds, rpe=p.rpe), now
    )
    return {"exercise": ex.name, "set_ids": [row.id]}, {"workout_id": wid, "set_ids": [row.id]}


def _describe_weight(db: Session, p: LogWeightP) -> list[str]:
    return [f"Add a weigh-in of {_kg(p.weight_kg)} for now."]


def _exec_weight(
    db: Session, bus: EventBus, now: datetime, p: LogWeightP
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    out = body.log_metric(db, BodyMetricIn(weight_kg=p.weight_kg), now)
    return {"metric_id": out.id, "weight_kg": p.weight_kg}, {"metric_id": out.id}


def _undo_weight(db: Session, bus: EventBus, now: datetime, u: dict[str, Any]) -> None:
    body.delete_metric(db, u["metric_id"])


def _describe_meal(db: Session, p: LogMealP) -> list[str]:
    _, name = resolve_food(db, p.food)
    return [f"Log {p.portions:g} \u00d7 {name} as {p.meal_type}."]


def _exec_meal(
    db: Session, bus: EventBus, now: datetime, p: LogMealP
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    fid, name = resolve_food(db, p.food)
    meal = nutrition.log_meal(
        db,
        bus,
        MealIn(meal_type=p.meal_type, items=[MealItemIn(food_id=fid, portions=p.portions)]),
        now,
    )
    return {"meal_id": meal.id, "food": name}, {"meal_id": meal.id}


def _undo_meal(db: Session, bus: EventBus, now: datetime, u: dict[str, Any]) -> None:
    try:
        nutrition.delete_meal(db, u["meal_id"])
    except nutrition.NotFound:
        pass


def _describe_follow(db: Session, p: FollowProgramP) -> list[str]:
    _, name = resolve_program(db, p.program)
    cur = programs_service.active(db)
    then = f" (instead of {cur.program_key})" if cur else ""
    return [f"Follow {name}{then}. Your logged history stays as it is."]


def _exec_follow(
    db: Session, bus: EventBus, now: datetime, p: FollowProgramP
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    key, name = resolve_program(db, p.program)
    cur = programs_service.active(db)
    prev = cur.program_key if cur else None
    programs_service.enroll(db, key, now)
    return {"program": name, "key": key}, {"previous": prev}


def _undo_follow(db: Session, bus: EventBus, now: datetime, u: dict[str, Any]) -> None:
    if u.get("previous"):
        programs_service.enroll(db, u["previous"], now)
    else:
        programs_service.leave(db, now)


def _describe_erase(db: Session, p: EraseDataP) -> list[str]:
    from app.models import Base  # noqa: F401  (all tables registered)
    from app.modules.workouts.models import Workout

    n = db.scalar(select(func.count(Workout.id))) or 0
    keep = "Your preferences are kept." if p.keep_preferences else "Preferences are reset too."
    return [
        f"Erase your profile, {n} workouts, meals, weigh-ins, XP and photos.",
        "A backup is made first; restore it from Settings > Backups.",
        f"The exercise library and food table stay. {keep}",
    ]


def _exec_erase(
    db: Session, bus: EventBus, now: datetime, p: EraseDataP
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    # Run by the service with the request's data folder (see service.confirm).
    raise NotImplementedError


SPECS: dict[str, Spec] = {
    s.kind: s
    for s in (
        Spec("log_set", "Log sets", "low", LogSetP, _describe_set, _exec_set, _undo_sets),
        Spec("log_hold", "Log a hold", "low", LogHoldP, _describe_hold, _exec_hold, _undo_sets),
        Spec("log_weight", "Log a weigh-in", "low", LogWeightP, _describe_weight, _exec_weight,
             _undo_weight),
        Spec("log_meal", "Log food", "low", LogMealP, _describe_meal, _exec_meal, _undo_meal),
        Spec("follow_program", "Switch program", "normal", FollowProgramP, _describe_follow,
             _exec_follow, _undo_follow),
        Spec("erase_data", "Erase my data", "destructive", EraseDataP, _describe_erase,
             _exec_erase, None, confirm_word="ERASE"),
    )
}  # fmt: skip


def dumps(d: Any) -> str:
    return json.dumps(d, default=str)
