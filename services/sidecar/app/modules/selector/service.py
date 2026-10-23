"""Reads the player state from the log and runs the selector; one ledger for every
proactive post (catalog items, watcher events, System notices) so caps and cooldowns hold
across all of them."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.gamification import service as game
from app.modules.gamification.formulas import level_from_total
from app.modules.nutrition import service as nutrition
from app.modules.progress import service as progress
from app.modules.progress.models import BodyMetric, Checkin
from app.modules.selector import catalog, engine
from app.modules.selector.models import SelectorPick
from app.modules.selector.state import (
    PATTERN_CATEGORY,
    WEEKLY_TARGET,
    PlayerState,
    StrengthRatios,
    experience_level,
)
from app.modules.workouts.models import Exercise, Workout, WorkoutSet

KEY_LIFTS = {"squat": "Back Squat", "bench": "Barbell Bench Press", "deadlift": "Deadlift"}
VOLUME_SECTIONS = ("gym", "calisthenics", "martial_arts")

# Watcher events: the gap between two posts of the same kind (days). Celebrations have none
# (each is a different event) but still count toward the daily cap.
WATCH_COOLDOWN: dict[str, int] = {
    "missed": 3,
    "overtraining": 2,
    "plateau": 7,
    "weight_trend": 7,
    "weigh_in": 7,
    "photo_reminder": 25,
}
WATCH_WHY: dict[str, str] = {
    "pr": "you set a new best estimated 1RM in the last 3 days",
    "skill": "you unlocked a skill step in the last 3 days",
    "boss": "you beat this week's boss",
    "streak": "your streak reached a milestone",
    "program": "you finished a block of your program",
    "missed": "it has been longer than your usual gap since your last session",
    "first_session": "your profile is set up but no session is logged yet",
    "overtraining": "some muscles are over their weekly range",
    "plateau": "a lift's estimated 1RM hasn't risen for two weeks",
    "weight_trend": "you are losing more than 1% of body weight a week",
    "weigh_in": "your last weigh-in is over 10 days old",
    "photo_reminder": "it has been a month since your last progress photo",
}


def _slope_per_week(points: Sequence[tuple[date, float]]) -> float | None:
    if len(points) < 3:
        return None
    xs = [(d - points[0][0]).days for d, _ in points]
    ys = [w for _, w in points]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / den * 7


def player_state(db: Session, now: datetime) -> PlayerState:
    today = now.date()
    p = progress.get_profile(db)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=28)
    rows = db.execute(
        select(Workout.day, Exercise.section, Exercise.pattern, WorkoutSet.duration_s)
        .join(Workout, WorkoutSet.workout_id == Workout.id)
        .join(Exercise, WorkoutSet.exercise_id == Exercise.id)
        .where(Workout.day > month_ago)
    ).all()
    load = dict.fromkeys(WEEKLY_TARGET, 0.0)
    sets_28 = 0
    for day, section, pattern, duration in rows:
        if section in VOLUME_SECTIONS:
            sets_28 += 1
        if day <= week_ago:
            continue
        if section == "cardio":
            load["cardio"] += (duration or 0) / 60
            continue
        if section == "calisthenics":
            load["calisthenics"] += 1
        cat = PATTERN_CATEGORY.get(pattern or "")
        if cat and section in VOLUME_SECTIONS:
            load[cat] += 1
    ratio = {k: round(min(v / WEEKLY_TARGET[k], 3.0), 3) for k, v in load.items()}

    first = db.scalar(select(func.min(Workout.day)))
    training_weeks = (today - first).days / 7 if first else 0.0
    bw = p.weight_kg if p else None
    ratios: dict[str, float | None] = {}
    for key, name in KEY_LIFTS.items():
        best = db.scalar(
            select(func.max(WorkoutSet.e1rm))
            .join(Exercise, WorkoutSet.exercise_id == Exercise.id)
            .where(Exercise.name == name)
        )
        ratios[key] = round(best / bw, 2) if best and bw else None
    sr = StrengthRatios(**ratios)
    level = experience_level(
        training_weeks, sets_28 / 4, sr, p.experience if p else None, has_log=first is not None
    )

    checkin = db.scalars(select(Checkin).where(Checkin.day == today)).first()
    if checkin is not None:
        readiness, source = int(checkin.readiness), "checkin"
    else:
        trained = [m.readiness for m in progress.muscle_states(db, now) if m.es_7d > 0]
        if trained:
            readiness, source = round(sum(trained) / len(trained) * 100), "recovery"
        else:
            readiness, source = 75, "unknown"

    last = db.scalar(select(func.max(Workout.day)))
    sessions_14d = (
        db.scalar(
            select(func.count(func.distinct(Workout.day))).where(
                Workout.day > today - timedelta(days=14)
            )
        )
        or 0
    )
    kcal_ratio = protein_ratio = None
    meal_days = 0
    if p is not None:
        e = progress.energy_for(p)
        totals = [nutrition.day_totals(db, today - timedelta(days=i)) for i in range(1, 8)]
        logged = [t for t in totals if t.kcal > 0]
        meal_days = len(logged)
        if logged and e.kcal_target:
            kcal_ratio = round(sum(t.kcal for t in logged) / len(logged) / e.kcal_target, 3)
        if logged and e.protein_target_g:
            protein_ratio = round(
                sum(t.protein_g for t in logged) / len(logged) / e.protein_target_g, 3
            )
    points = [
        (m.measured_at.date(), m.weight_kg)
        for m in db.scalars(
            select(BodyMetric)
            .where(BodyMetric.measured_at >= now - timedelta(days=14))
            .order_by(BodyMetric.measured_at)
        )
    ]
    slope = _slope_per_week(points)
    goal = p.goal if p else None
    matches: bool | None = None
    if slope is not None and goal:
        if goal == "cut":
            matches = slope < 0.1
        elif goal == "bulk":
            matches = slope > -0.1
        else:
            matches = abs(slope) < 0.5
    return PlayerState(
        level=level,
        game_level=level_from_total(game.total_xp(db)).level,
        age=p.age if p else None,
        training_weeks=round(training_weeks, 1),
        sets_per_week=round(sets_28 / 4, 1),
        ratios=sr,
        load=ratio,
        readiness=readiness,
        readiness_source=source,  # type: ignore[arg-type]
        streak=game.streak(db, today).current,
        days_since_workout=(today - last).days if last else None,
        sessions_14d=int(sessions_14d),
        planned_per_week=int(progress.get_setting(db, "sessions_per_week", "3")),
        kcal_ratio=kcal_ratio,
        protein_ratio=protein_ratio,
        meal_days_7d=meal_days,
        goal=goal,
        weight_trend_kg_week=round(slope, 2) if slope is not None else None,
        trend_matches_goal=matches,
        hide_calories=progress.get_setting(db, "hide_calories", "false") == "true",
    )


def _today_counts(db: Session, today: date) -> dict[str, int]:
    rows = db.execute(
        select(SelectorPick.kind, func.count())
        .where(SelectorPick.day == today)
        .group_by(SelectorPick.kind)
    ).all()
    return {k: int(n) for k, n in rows}


def _record(
    db: Session, now: datetime, source: str, item_id: str, kind: str, text: str, why: list[str]
) -> SelectorPick:
    row = SelectorPick(
        day=now.date(),
        source=source,
        item_id=item_id,
        kind=kind,
        text=text[:400],
        why_json=json.dumps(why),
        created_at=now,
    )
    db.add(row)
    db.flush()
    return row


def posted_today(db: Session, today: date) -> int:
    return int(db.scalar(select(func.count(SelectorPick.id)).where(SelectorPick.day == today)) or 0)


def gate_watch(db: Session, notices: Sequence[Any], now: datetime) -> list[tuple[Any, list[str]]]:
    """Watcher notices allowed today (in order), each with its why, recorded in the ledger.
    The rest wait: their keys are event-based, so they can post on a later day if still
    relevant."""
    today = now.date()
    left = engine.DAILY_CAP - posted_today(db, today)
    out: list[tuple[Any, list[str]]] = []
    for n in notices:
        if left <= 0:
            break
        gap = WATCH_COOLDOWN.get(n.kind)
        if gap:
            last = db.scalar(
                select(func.max(SelectorPick.day)).where(
                    SelectorPick.source == "watch", SelectorPick.kind == n.kind
                )
            )
            if last is not None and (today - last).days < gap:
                continue
        why = [WATCH_WHY.get(n.kind, n.kind)]
        _record(db, now, "watch", n.key, n.kind, n.text, why)
        out.append((n, why))
        left -= 1
    return out


def gate_system(db: Session, notices: Sequence[Any], now: datetime) -> list[Any]:
    """System notices (deload, raised targets, recovered): one already posted stays
    visible; a new one posts only under today's cap."""
    out = []
    for n in notices:
        seen = db.scalars(
            select(SelectorPick).where(
                SelectorPick.source == "system", SelectorPick.item_id == n.id
            )
        ).first()
        if seen is not None:
            out.append(n)
            continue
        if posted_today(db, now.date()) >= engine.DAILY_CAP:
            continue
        _record(db, now, "system", n.id, n.code, n.text, [f"the {n.code} rule fired"])
        out.append(n)
    db.commit()
    return out


def today(db: Session, now: datetime) -> list[SelectorPick]:
    """Today's catalog picks (selected once a day, after the watcher's events)."""
    day = now.date()
    done = db.scalars(
        select(SelectorPick).where(SelectorPick.day == day, SelectorPick.source == "catalog")
    ).all()
    ran = progress.get_setting(db, "selector_ran", "") == day.isoformat()
    if ran or progress.get_profile(db) is None:
        return list(done)
    state = player_state(db, now)
    last_rows = db.execute(
        select(SelectorPick.item_id, func.max(SelectorPick.day))
        .where(SelectorPick.source == "catalog")
        .group_by(SelectorPick.item_id)
    ).all()
    last = {i: d for i, d in last_rows}
    picks = engine.select(state, catalog.ITEMS, last, day, _today_counts(db, day))
    rows = [_record(db, now, "catalog", p.item.id, p.item.kind, p.text, p.why) for p in picks]
    progress.set_setting(db, "selector_ran", day.isoformat())
    db.commit()
    return [*done, *rows]


def explain(db: Session, now: datetime) -> list[dict[str, object]]:
    """Every catalog item with whether it is eligible right now and why (for the docs/viva)."""
    s = player_state(db, now)
    out: list[dict[str, object]] = []
    for item in catalog.ITEMS:
        v = engine.check(item, s)
        out.append(
            {"id": item.id, "kind": item.kind, "eligible": v.eligible, "why": v.why,
             "blocked_by": v.blocked_by}
        )  # fmt: skip
    return out


def latest(db: Session, limit: int = 20) -> list[SelectorPick]:
    return list(
        db.scalars(select(SelectorPick).order_by(SelectorPick.id.desc()).limit(limit)).all()
    )
