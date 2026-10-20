"""Hunter stats (STR, AGI, END, VIT, INT): five 0-100 scores computed from your own logs.

Nothing here is allocated by hand or by a model; every score is a formula over the
last weeks of data, and the API returns the inputs next to each value so the UI can
show "why". Version: ``stats-v1``.

  STR  Strength: the better of (a) strength skill-tree progress (muscle-up, one-arm
       push-up, dips, pistol, nordic curl) as a share of their earned steps (entry
       steps, which start unlocked, do not count), and (b) your best
       weighted e1RM in 90 days relative to body weight, on ASCEND's own scale where
       2.0 x body weight = 100. (b) is a scale chosen by ASCEND, not a population norm.
  AGI  Agility / skill: share of steps unlocked in the skill trees (L-sit, handstand,
       front lever, back lever, planche, human flag, dragon flag).
  END  Endurance: cardio and martial-arts minutes in the last 28 days against 600 min
       (the WHO's 150 min of moderate activity a week, times 4).
  VIT  Vitality: half for how many of the last 28 days have a morning check-in, half
       for the average readiness those check-ins reported.
  INT  Discipline: half for how many of the last 28 days have a logged meal, half for
       the share of daily-quest tasks completed in that window.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

STATS_VERSION = "stats-v1"
WINDOW_DAYS = 28
E1RM_WINDOW_DAYS = 90
STRENGTH_TREES = ("muscle_up", "one_arm_push_up", "dips", "pistol", "nordic_curl")
SKILL_TREES = (
    "l_sit",
    "handstand",
    "front_lever",
    "back_lever",
    "planche",
    "human_flag",
    "dragon_flag",
)
REL_E1RM_FULL = 2.0  # x body weight = 100 on ASCEND's scale
CARDIO_FULL_MIN = 600  # WHO 150 min/week x 4 weeks
CARDIO_SECTIONS = ("cardio", "martial_arts")


@dataclass(frozen=True)
class StatInputs:
    strength_steps: tuple[int, int] = (0, 0)  # unlocked, total
    skill_steps: tuple[int, int] = (0, 0)
    best_e1rm_kg: float | None = None
    bodyweight_kg: float | None = None
    cardio_min: float = 0.0
    checkin_days: int = 0
    mean_readiness: float | None = None
    meal_days: int = 0
    quest_done: int = 0
    quest_total: int = 0
    window_days: int = WINDOW_DAYS


@dataclass(frozen=True)
class Stat:
    key: str
    label: str
    value: int
    formula: str
    inputs: dict[str, float | int | str | None] = field(default_factory=dict)


def _share(a: int, b: int) -> float:
    return a / b if b > 0 else 0.0


def _pct(x: float) -> int:
    return round(100 * min(1.0, max(0.0, x)))


def compute_stats(i: StatInputs) -> list[Stat]:
    """Pure: the five stats from their inputs (unit-tested on fixtures)."""
    tree = _share(*i.strength_steps)
    rel = (i.best_e1rm_kg / i.bodyweight_kg) if i.best_e1rm_kg and i.bodyweight_kg else None
    lift = min(1.0, rel / REL_E1RM_FULL) if rel is not None else 0.0
    w = i.window_days
    readiness = (i.mean_readiness or 0.0) / 100
    return [
        Stat(
            "str",
            "Strength",
            _pct(max(tree, lift)),
            "Better of: strength skill-tree steps unlocked, or best e1RM ÷ body weight "
            "(2.0× = 100)",
            {
                "strength_steps_unlocked": i.strength_steps[0],
                "strength_steps_total": i.strength_steps[1],
                "best_e1rm_kg_90d": i.best_e1rm_kg,
                "bodyweight_kg": i.bodyweight_kg,
                "relative_e1rm": round(rel, 2) if rel is not None else None,
            },
        ),
        Stat(
            "agi",
            "Agility",
            _pct(_share(*i.skill_steps)),
            "Skill-tree steps unlocked (levers, planche, handstand, flag, L-sit, dragon flag)",
            {"skill_steps_unlocked": i.skill_steps[0], "skill_steps_total": i.skill_steps[1]},
        ),
        Stat(
            "end",
            "Endurance",
            _pct(i.cardio_min / CARDIO_FULL_MIN),
            f"Cardio minutes in {w} days ÷ {CARDIO_FULL_MIN} (WHO: 150 min a week)",
            {"cardio_minutes": round(i.cardio_min), "target_minutes": CARDIO_FULL_MIN},
        ),
        Stat(
            "vit",
            "Vitality",
            _pct(0.5 * _share(i.checkin_days, w) + 0.5 * readiness),
            f"Half: check-in days of the last {w}; half: average readiness reported",
            {
                "checkin_days": i.checkin_days,
                "window_days": w,
                "mean_readiness": round(i.mean_readiness) if i.mean_readiness is not None else None,
            },
        ),
        Stat(
            "int",
            "Discipline",
            _pct(0.5 * _share(i.meal_days, w) + 0.5 * _share(i.quest_done, i.quest_total)),
            f"Half: days with a logged meal of the last {w}; half: quest tasks completed",
            {
                "meal_days": i.meal_days,
                "window_days": w,
                "quest_done": i.quest_done,
                "quest_total": i.quest_total,
            },
        ),
    ]


def gather(db: Session, now: datetime) -> StatInputs:
    """Read the inputs from the other modules' tables (read-only)."""
    from app.modules.gamification.models import QuestItem
    from app.modules.nutrition.models import Meal
    from app.modules.progress.models import BodyMetric, Checkin, Profile
    from app.modules.skills import service as skills
    from app.modules.skills.catalog import SKILLS
    from app.modules.workouts.models import Exercise, Workout, WorkoutSet

    today = now.date()
    since = today - timedelta(days=WINDOW_DAYS - 1)
    summaries = {s.key: s for s in skills.summaries(db, now)}

    # Entry steps (no criteria) start unlocked, so they are not earned progress.
    entry = {k.key: sum(1 for st in k.steps if not st.unlock) for k in SKILLS}

    def steps(keys: tuple[str, ...]) -> tuple[int, int]:
        rows = [summaries[k] for k in keys if k in summaries]
        earned = sum(max(0, r.steps_unlocked - entry.get(r.key, 0)) for r in rows)
        total = sum(max(0, r.steps_total - entry.get(r.key, 0)) for r in rows)
        return earned, total

    best = db.scalar(
        select(func.max(WorkoutSet.e1rm))
        .join(Workout, Workout.id == WorkoutSet.workout_id)
        .where(
            Workout.day >= today - timedelta(days=E1RM_WINDOW_DAYS - 1),
            WorkoutSet.weight_kg > 0,
        )
    )
    latest = db.scalar(
        select(BodyMetric.weight_kg).order_by(BodyMetric.measured_at.desc()).limit(1)
    )
    profile = db.get(Profile, 1)
    bodyweight = latest or (profile.weight_kg if profile else None)
    cardio_s = db.scalar(
        select(func.coalesce(func.sum(WorkoutSet.duration_s), 0))
        .join(Workout, Workout.id == WorkoutSet.workout_id)
        .join(Exercise, Exercise.id == WorkoutSet.exercise_id)
        .where(Workout.day >= since, Exercise.section.in_(CARDIO_SECTIONS))
    )
    checkins = db.execute(
        select(func.count(), func.avg(Checkin.readiness)).where(Checkin.day >= since)
    ).one()
    meal_days = db.scalar(select(func.count(func.distinct(Meal.day))).where(Meal.day >= since)) or 0
    quest = db.execute(
        select(func.count(), func.count(QuestItem.completed_at)).where(QuestItem.day >= since)
    ).one()
    return StatInputs(
        strength_steps=steps(STRENGTH_TREES),
        skill_steps=steps(SKILL_TREES),
        best_e1rm_kg=float(best) if best else None,
        bodyweight_kg=float(bodyweight) if bodyweight else None,
        cardio_min=float(cardio_s or 0) / 60,
        checkin_days=int(checkins[0] or 0),
        mean_readiness=float(checkins[1]) if checkins[1] is not None else None,
        meal_days=int(meal_days),
        quest_done=int(quest[1] or 0),
        quest_total=int(quest[0] or 0),
    )
