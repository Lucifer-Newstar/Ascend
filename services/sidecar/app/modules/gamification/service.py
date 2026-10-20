"""Gamification use-cases + event handlers.

Writes happen only in response to events (or an explicit quest check-off);
reads of other modules go through their query functions.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.events import EventBus, MealLogged, QuestCompleted, SetLogged, WorkoutLogged
from app.modules.gamification import formulas as f
from app.modules.gamification.models import QuestItem, XpEvent
from app.modules.gamification.quests import (
    GENERATOR_VERSION,
    ExerciseRef,
    generate_daily_quest,
)
from app.modules.gamification.schemas import GameSummary, QuestItemOut, StreakOut, XpOut
from app.modules.gamification.streaks import StreakState, compute_streak


class QuestNotFound(Exception):
    pass


# --- XP ledger ---------------------------------------------------------------


def earned_on(db: Session, day: date) -> int:
    return int(db.scalar(select(func.coalesce(func.sum(XpEvent.amount), 0)).where(XpEvent.day == day)) or 0)


def total_xp(db: Session) -> int:
    return int(db.scalar(select(func.coalesce(func.sum(XpEvent.amount), 0))) or 0)


def award(db: Session, at: datetime, source: str, ref_id: int | None, amount: int, note: str = "") -> int:
    """Append an XP event, clipped by the daily cap. Returns the XP actually granted."""
    granted = f.apply_daily_cap(amount, earned_on(db, at.date()))
    if granted > 0:
        db.add(XpEvent(day=at.date(), at=at, source=source, ref_id=ref_id, amount=granted,
                       formula_version=f.FORMULA_VERSION, note=note))
        db.flush()
    return granted


def xp_for_refs(db: Session, sources: Iterable[str], ref_id: int) -> int:
    stmt = select(func.coalesce(func.sum(XpEvent.amount), 0)).where(
        XpEvent.source.in_(list(sources)), XpEvent.ref_id == ref_id
    )
    return int(db.scalar(stmt) or 0)


# --- streaks -----------------------------------------------------------------


def active_days(db: Session) -> set[date]:
    from app.modules.workouts.models import Workout

    days = set(db.scalars(select(Workout.day).where(Workout.finished_at.is_not(None))).all())
    days |= set(db.scalars(select(QuestItem.day).where(QuestItem.completed_at.is_not(None))).all())
    return days


def streak(db: Session, today: date) -> StreakState:
    return compute_streak(active_days(db), today)


# --- quests --------------------------------------------------------------------


def _exercise_refs(db: Session) -> list[ExerciseRef]:
    from app.modules.workouts.models import Exercise

    return [ExerciseRef(e.id, e.name, {m.muscle: m.weight for m in e.muscles})
            for e in db.scalars(select(Exercise)).all()]


def _completion_rate(db: Session, today: date) -> float | None:
    rows = db.scalars(select(QuestItem).where(QuestItem.day >= today - timedelta(days=7),
                                              QuestItem.day < today)).all()
    if not rows:
        return None
    return sum(1 for r in rows if r.completed_at) / len(rows)


def ensure_quest(db: Session, now: datetime) -> list[QuestItem]:
    from app.modules.progress import service as progress

    today = now.date()
    items = list(db.scalars(select(QuestItem).where(QuestItem.day == today).order_by(QuestItem.id)).all())
    if items:
        return items
    profile = progress.get_profile(db)
    protein = progress.energy_for(profile).protein_target_g if profile else None
    had_history = db.scalar(select(func.count()).select_from(QuestItem).where(QuestItem.day < today))
    yesterday = today - timedelta(days=1)
    missed = bool(had_history) and yesterday not in active_days(db)
    specs = generate_daily_quest(today, progress.muscle_states(db, now), _exercise_refs(db),
                                 protein, _completion_rate(db, today), missed)
    for s in specs:
        db.add(QuestItem(day=today, kind=s.kind, code=s.code, title=s.title, detail=s.detail,
                         metric=s.metric, target=s.target, xp=s.xp,
                         generator_version=GENERATOR_VERSION))
    db.flush()
    return list(db.scalars(select(QuestItem).where(QuestItem.day == today).order_by(QuestItem.id)).all())


def _metric_value(db: Session, metric: str, day: date) -> int | None:
    from app.modules.nutrition import service as nutrition
    from app.modules.workouts.models import ExerciseMuscle, Workout, WorkoutSet

    if metric.startswith("sets:"):
        muscle = metric.split(":", 1)[1]
        stmt = (
            select(func.count(WorkoutSet.id))
            .join(Workout, Workout.id == WorkoutSet.workout_id)
            .join(ExerciseMuscle, ExerciseMuscle.exercise_id == WorkoutSet.exercise_id)
            .where(Workout.day == day, ExerciseMuscle.muscle == muscle,
                   ExerciseMuscle.weight >= 1.0,
                   (WorkoutSet.rpe.is_(None)) | (WorkoutSet.rpe >= f.HARD_SET_RPE))
        )
        return int(db.scalar(stmt) or 0)
    if metric == "meals":
        return nutrition.meal_count(db, day)
    if metric == "protein_g":
        return round(nutrition.day_totals(db, day).protein_g)
    return None  # manual items are checked off by the user


def _complete(db: Session, bus: EventBus, item: QuestItem, now: datetime) -> None:
    item.completed_at = now
    item.progress = max(item.progress, item.target)
    mult = f.streak_multiplier(streak(db, now.date()).current)
    granted = award(db, now, "quest", item.id, round(item.xp * mult), note=item.title)
    bus.publish(db, QuestCompleted(quest_item_id=item.id, day=item.day, xp=granted))


def refresh_quest(db: Session, bus: EventBus, now: datetime) -> None:
    for item in ensure_quest(db, now):
        if item.completed_at:
            continue
        value = _metric_value(db, item.metric, item.day)
        if value is None:
            continue
        item.progress = min(value, item.target)
        if value >= item.target:
            _complete(db, bus, item, now)
    db.flush()


def complete_manual(db: Session, bus: EventBus, item_id: int, now: datetime) -> QuestItem:
    item = db.get(QuestItem, item_id)
    if item is None or item.day != now.date():
        raise QuestNotFound(f"quest item {item_id} is not part of today's quest")
    if item.metric != "manual":
        raise ValueError("this item completes automatically from your logs")
    if not item.completed_at:
        _complete(db, bus, item, now)
    db.flush()
    return item


# --- summary ---------------------------------------------------------------------


def summary(db: Session, bus: EventBus, now: datetime) -> GameSummary:
    refresh_quest(db, bus, now)
    total = total_xp(db)
    info = f.level_from_total(total)
    letter, title = f.rank_for_level(info.level)
    s = streak(db, now.date())
    return GameSummary(
        xp=XpOut(total=total, today=earned_on(db, now.date()), level=info.level,
                 xp_into_level=info.xp_into_level, xp_for_next=info.xp_for_next, rank=letter,
                 rank_title=title, daily_cap=f.DAILY_CAP, formula_version=f.FORMULA_VERSION),
        streak=StreakOut(current=s.current, best=s.best, freezes_held=s.freezes_held,
                         freezes_used=s.freezes_used, active_today=s.active_today),
        quest=[QuestItemOut.model_validate(q) for q in ensure_quest(db, now)],
    )


# --- event handlers ------------------------------------------------------------------


def make_handlers(bus: EventBus) -> None:
    def on_set_logged(db: Session, e: SetLogged) -> None:
        award(db, e.performed_at, "set", e.set_id, f.set_xp(e.rpe))
        if e.is_pr:
            award(db, e.performed_at, "pr", e.set_id, f.PR_XP, note="new e1RM PR")
        refresh_quest(db, bus, e.performed_at)

    def on_workout_logged(db: Session, e: WorkoutLogged) -> None:
        from app.modules.workouts.models import Workout

        workout = db.get(Workout, e.workout_id)
        at = workout.finished_at if workout and workout.finished_at else datetime.now()
        set_ids = [s.id for s in workout.sets] if workout else []
        already = int(db.scalar(select(func.coalesce(func.sum(XpEvent.amount), 0)).where(
            XpEvent.source == "set", XpEvent.ref_id.in_(set_ids))) or 0)
        bonus = f.session_completion_xp(e.active_minutes, already)
        mult = f.streak_multiplier(streak(db, at.date()).current)
        award(db, at, "session", e.workout_id, round(bonus * mult), note="session complete")
        refresh_quest(db, bus, at)

    def on_meal_logged(db: Session, e: MealLogged) -> None:
        from app.modules.nutrition import service as nutrition

        meal = nutrition.get_meal(db, e.meal_id)
        meals_before = max(0, nutrition.meal_count(db, e.day) - 1)
        award(db, meal.logged_at, "meal", e.meal_id, f.meal_xp(meals_before))
        refresh_quest(db, bus, meal.logged_at)

    bus.subscribe(SetLogged, on_set_logged)
    bus.subscribe(WorkoutLogged, on_workout_logged)
    bus.subscribe(MealLogged, on_meal_logged)


def register(bus: EventBus) -> None:
    make_handlers(bus)
