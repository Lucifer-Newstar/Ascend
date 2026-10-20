"""Weekly review (deterministic, versioned): collect the week, score findings
with fixed rules, keep the top 3 and write a template summary.

Spec: docs/ai/adaptive-planning-ai.md section 5. Rules implemented here:

  code               severity  condition
  ADHERENCE_LOW      3         sessions < 70 % of planned, this week and last
  WEIGHT_FAST_GAIN   3         bulking and trend rising > 0.5 % of body weight / week
  DELOAD_DUE         3         the deload engine recommends a deload
  WEIGHT_STALL       2         bulking (or cutting) and the trend moves < 0.1 kg / week
  MUSCLE_UNDER       2         a trained muscle under its weekly minimum, 2 weeks running
  MUSCLE_OVER        2         a muscle above its weekly range
  E1RM_FLAT          1         a key lift trained 3 weeks running with no e1RM gain
  PROTEIN_LOW        1         protein under target on >= 4 of the logged days

PAIN_ACTIVE needs the injury module (Phase 2) and is not scored yet.
Every number in the summary comes from a finding; the coach model may later
rephrase the summary but is given these numbers and may not change them.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.nutrition.service import day_totals, meal_count
from app.modules.progress import body
from app.modules.progress import service as progress
from app.modules.progress import trend as trend_engine
from app.modules.progress.models import MuscleLoadEvent
from app.modules.progress.muscle_load import Contribution, compute_states
from app.modules.workouts import deload, deload_service
from app.modules.workouts.models import Exercise, Workout, WorkoutSet

FORMULA_VERSION = "review-v1"
ADHERENCE_MIN = 0.70
FAST_GAIN_FRACTION = 0.005
STALL_KG_PER_WEEK = 0.1
PROTEIN_LOW_DAYS = 4
DEFAULT_SESSIONS_PER_WEEK = 3
TOP_N = 3


@dataclass
class Finding:
    code: str
    severity: int
    title: str
    detail: str
    proposal: str | None
    numbers: dict[str, Any] = field(default_factory=dict)


@dataclass
class Review:
    week_start: date
    week_end: date
    sessions_done: int
    sessions_planned: int
    findings: list[Finding]
    top: list[Finding]
    summary: str
    summary_source: str = "template"
    algo_version: str = FORMULA_VERSION


def _sessions(db: Session, start: date, end: date) -> int:
    return int(
        db.scalar(
            select(func.count(Workout.id)).where(
                Workout.finished_at.is_not(None), Workout.day >= start, Workout.day <= end
            )
        )
        or 0
    )


def _planned(db: Session) -> int:
    raw = progress.get_setting(db, "sessions_per_week", str(DEFAULT_SESSIONS_PER_WEEK))
    return max(1, int(raw))


def _muscle_states_at(db: Session, at: datetime) -> list[Any]:
    rows = db.scalars(
        select(MuscleLoadEvent).where(MuscleLoadEvent.at >= at - timedelta(days=28))
    ).all()
    return compute_states([Contribution(r.muscle, r.es, r.at) for r in rows], at)


def _weekly_best(db: Session, exercise_id: int, start: date) -> float | None:
    value = db.scalar(
        select(func.max(WorkoutSet.e1rm))
        .join(Workout, Workout.id == WorkoutSet.workout_id)
        .where(
            WorkoutSet.exercise_id == exercise_id,
            Workout.day >= start,
            Workout.day < start + timedelta(days=7),
        )
    )
    return float(value) if value is not None else None


def _adherence(db: Session, end: date) -> Finding | None:
    first = db.scalar(select(func.min(Workout.day)))
    if first is None or first > end - timedelta(days=13):
        return None  # fewer than two full weeks of history: nothing to judge yet
    planned = _planned(db)
    this_week = _sessions(db, end - timedelta(days=6), end)
    last_week = _sessions(db, end - timedelta(days=13), end - timedelta(days=7))
    if this_week < ADHERENCE_MIN * planned and last_week < ADHERENCE_MIN * planned:
        return Finding(
            "ADHERENCE_LOW",
            3,
            "Fewer sessions than planned two weeks running",
            f"{this_week} of {planned} sessions this week and {last_week} of {planned} last week.",
            "Shorten sessions or drop one training day so the plan fits your week.",
            {"sessions_this_week": this_week, "sessions_last_week": last_week, "planned": planned},
        )
    return None


def _weight(db: Session, now: datetime) -> Finding | None:
    profile = progress.get_profile(db)
    if profile is None:
        return None
    trend_kg = body.eta_for(db, None, now).current_trend_kg
    rows = body.list_metrics(db, now, 14)
    s = trend_engine.slope([(m.measured_at, m.trend_kg) for m in rows])
    if trend_kg is None or s is None or len(rows) < 6 or s.span_days < 10:
        return None
    rate = round(s.kg_per_week, 2)
    if profile.goal == "bulk" and rate > FAST_GAIN_FRACTION * trend_kg:
        return Finding(
            "WEIGHT_FAST_GAIN",
            3,
            "Weight is rising faster than a lean bulk needs",
            f"Trend weight is rising {rate} kg per week "
            f"(guide: up to {round(FAST_GAIN_FRACTION * trend_kg, 2)} kg).",
            "Lower the calorie target by about 150 kcal.",
            {"rate_kg_per_week": rate, "trend_kg": trend_kg},
        )
    stalled = abs(rate) < STALL_KG_PER_WEEK
    if profile.goal in ("bulk", "cut") and (stalled or (profile.goal == "cut" and rate > 0)):
        direction = "+150" if profile.goal == "bulk" else "-150"
        return Finding(
            "WEIGHT_STALL",
            2,
            "Weight trend has stalled",
            f"Trend weight moved {rate} kg per week over the last 2 weeks "
            f"while the goal is to {profile.goal}.",
            f"Adjust the calorie target by {direction} kcal.",
            {"rate_kg_per_week": rate, "trend_kg": trend_kg},
        )
    return None


def _muscles(db: Session, now: datetime) -> list[Finding]:
    found: list[Finding] = []
    current = _muscle_states_at(db, now)
    previous = {m.key: m for m in _muscle_states_at(db, now - timedelta(days=7))}
    under = [
        m
        for m in current
        if m.status not in ("no_data",)
        and m.es_7d < m.weekly_low
        and previous[m.key].es_7d < m.weekly_low
    ]
    if under:
        worst = min(under, key=lambda m: m.es_7d - m.weekly_low)
        found.append(
            Finding(
                "MUSCLE_UNDER",
                2,
                f"{worst.label} under its weekly target",
                f"{worst.label}: {worst.es_7d:g} effective sets this week and "
                f"{previous[worst.key].es_7d:g} last week "
                f"(target {worst.weekly_low:g}-{worst.weekly_high:g}).",
                f"Add 2-4 sets for {worst.label.lower()} across the week.",
                {"muscle": worst.key, "es_7d": worst.es_7d, "weekly_low": worst.weekly_low},
            )
        )
    over = [m for m in current if m.es_7d > m.weekly_high]
    if over:
        top = max(over, key=lambda m: m.es_7d - m.weekly_high)
        found.append(
            Finding(
                "MUSCLE_OVER",
                2,
                f"{top.label} above its weekly range",
                f"{top.label}: {top.es_7d:g} effective sets this week "
                f"(range {top.weekly_low:g}-{top.weekly_high:g}).",
                "Remove an overlapping accessory exercise next week.",
                {"muscle": top.key, "es_7d": top.es_7d, "weekly_high": top.weekly_high},
            )
        )
    return found


def _e1rm_flat(db: Session, end: date) -> Finding | None:
    this_monday = deload.week_start(end)
    for name in deload.KEY_LIFTS:
        ex = db.scalars(select(Exercise).where(Exercise.name == name)).first()
        if ex is None:
            continue
        maybe = [_weekly_best(db, ex.id, this_monday - timedelta(weeks=k)) for k in (2, 1, 0)]
        bests = [b for b in maybe if b is not None]
        if len(bests) == 3 and max(bests[1:]) <= bests[0]:
            return Finding(
                "E1RM_FLAT",
                1,
                f"{name} has not progressed for 3 weeks",
                f"{name} best e1RM per week: " + ", ".join(f"{b:g} kg" for b in bests) + ".",
                "Try a new variation or a different rep range for 3-4 weeks.",
                {"lift": name, "weekly_best_e1rm": bests},
            )
    return None


def _protein(db: Session, end: date) -> Finding | None:
    profile = progress.get_profile(db)
    if profile is None:
        return None
    target = progress.energy_for(profile).protein_target_g
    days = [end - timedelta(days=i) for i in range(7)]
    logged = [d for d in days if meal_count(db, d) > 0]
    low = [d for d in logged if day_totals(db, d).protein_g < target]
    if len(logged) >= PROTEIN_LOW_DAYS and len(low) >= PROTEIN_LOW_DAYS:
        return Finding(
            "PROTEIN_LOW",
            1,
            "Protein below target most days",
            f"Protein was under {target} g on {len(low)} of {len(logged)} logged days.",
            None,
            {"days_low": len(low), "days_logged": len(logged), "target_g": target},
        )
    return None


def _deload(db: Session, now: datetime) -> Finding | None:
    a = deload_service.advice(db, now)
    if not a.recommended:
        return None
    active = [s.code for s in a.signals if s.active]
    why = (
        f"{a.training_weeks} training weeks in a row"
        if a.kind == "planned"
        else "signals: " + ", ".join(active)
    )
    return Finding(
        "DELOAD_DUE",
        3,
        "A deload week is due",
        f"Deload due ({a.kind}): {why}.",
        "Take a deload week: same weights, about half the sets, RPE 7 or easier.",
        {"kind": a.kind, "training_weeks": a.training_weeks, "signals": active},
    )


def template_summary(sessions_done: int, planned: int, top: list[Finding]) -> str:
    first = f"This week: {sessions_done} of {planned} planned sessions done."
    if not top:
        return first + " No issues found; keep the current plan."
    main = f" Main finding: {top[0].detail}"
    rest = [f.title.lower() for f in top[1:]]
    tail = f" Also: {'; '.join(rest)}." if rest else ""
    return first + main + tail + " Review each proposal below."


def review(db: Session, now: datetime) -> Review:
    end = now.date()
    start = end - timedelta(days=6)
    at_end = datetime.combine(end, time.max).replace(microsecond=0)
    at_end = min(at_end, now)
    rules: list[Callable[[], Finding | list[Finding] | None]] = [
        lambda: _adherence(db, end),
        lambda: _weight(db, at_end),
        lambda: _deload(db, at_end),
        lambda: _muscles(db, at_end),
        lambda: _e1rm_flat(db, end),
        lambda: _protein(db, end),
    ]
    findings: list[Finding] = []
    for rule in rules:
        result = rule()
        if result is None:
            continue
        findings.extend(result if isinstance(result, list) else [result])
    ranked = sorted(findings, key=lambda f: -f.severity)  # stable: rule order breaks ties
    top = ranked[:TOP_N]
    done = _sessions(db, start, end)
    planned = _planned(db)
    return Review(
        week_start=start,
        week_end=end,
        sessions_done=done,
        sessions_planned=planned,
        findings=ranked,
        top=top,
        summary=template_summary(done, planned, top),
    )
