"""The Awakening baseline test: a few max-effort results logged as one real session.

The results go through the normal set logger, so they seed everything the same way any
logged set would: XP (and so level and rank), the skill trees' progress and the hunter
stats. Nothing is invented: a test the user skipped logs nothing.
"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.events import EventBus
from app.modules.gamification import formulas as f
from app.modules.gamification import service as game
from app.modules.progress import body
from app.modules.progress.schemas import BaselineIn, BaselineOut, BaselineResult, BodyMetricIn
from app.modules.progress.service import get_profile
from app.modules.skills import service as skills
from app.modules.workouts import service as workouts
from app.modules.workouts.models import Exercise
from app.modules.workouts.schemas import SetIn

# Test -> (library exercise, how it is logged). RPE 10: each test is a max effort.
_TESTS: tuple[tuple[str, str, str], ...] = (
    ("pushups", "Push-up", "reps"),
    ("pullups", "Pull-up", "reps"),
    ("dead_hang_s", "Dead Hang", "hold"),
    ("plank_s", "Plank", "hold"),
    ("squats_60s", "Bodyweight Squat", "reps"),
)


class BaselineEmpty(ValueError):
    pass


def run_baseline(db: Session, bus: EventBus, data: BaselineIn, now: datetime) -> BaselineOut:
    results = [(k, name, how, getattr(data, k)) for k, name, how in _TESTS if getattr(data, k)]
    if not results and not data.bodyweight_kg:
        raise BaselineEmpty("enter at least one result (or skip the test)")
    xp_before = game.total_xp(db)
    unlocked: list[str] = []
    workout_id = 0
    sets = 0
    if results:
        by_name = {
            e.name: e
            for e in db.query(Exercise).filter(Exercise.name.in_([r[1] for r in results])).all()
        }
        workout = workouts.start_workout(db, now, "calisthenics")
        workout.notes = "Baseline test"
        workout_id = workout.id
        for _key, name, how, value in results:
            ex = by_name.get(name)
            if ex is None:
                continue
            set_in = (
                SetIn(exercise_id=ex.id, duration_s=int(value), rpe=10)
                if how == "hold"
                else SetIn(exercise_id=ex.id, reps=int(value), weight_kg=0, rpe=10)
            )
            row, _ = workouts.log_set(db, bus, workout.id, set_in, now)
            sets += 1
            for u in skills.unlocks_for_set(db, row.id):
                unlocked.append(f"{u.skill_name}: {u.step_name}")
        if sets:
            workouts.finish_workout(db, bus, workout.id, now)
    profile = get_profile(db)
    if data.bodyweight_kg:
        body.log_metric(db, BodyMetricIn(weight_kg=data.bodyweight_kg), now)
        if profile is not None:
            profile.weight_kg = data.bodyweight_kg
    result = BaselineResult(**data.model_dump(), taken_at=now)
    if profile is not None:
        profile.baseline_json = json.dumps(result.model_dump(mode="json"))
    db.flush()
    total = game.total_xp(db)
    level = f.level_from_total(total).level
    return BaselineOut(
        baseline=result,
        workout_id=workout_id,
        sets_logged=sets,
        xp_awarded=total - xp_before,
        level=level,
        rank=f.rank_for_level(level)[0],
        steps_unlocked=unlocked,
    )
