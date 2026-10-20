"""Deload triggers (deterministic, versioned): planned 3+1 blocks and reactive.

Planned: after 3 consecutive training weeks (>= 2 finished sessions each)
since the last deload, week 4 is a deload week.

Reactive: a deload is recommended when at least 2 of these 5 signals hold
(docs/ai/adaptive-planning-ai.md; deload-v2 added STALLED_LIFTS from prog-v1):

  LOW_READINESS     >= 3 check-ins in the last 7 days averaging < 50
  HEAVY_SORENESS    soreness "a lot" on >= 3 of the last 7 check-ins
  PERFORMANCE_DROP  >= 2 key lifts whose best e1RM in the last 14 days is
                    >= 3 % below their best in the 21 days before
  FATIGUE_BUILDUP   >= 3 muscles over their weekly range or under 50 % readiness
  STALLED_LIFTS     >= 2 exercises trained in the last 14 days with no rep record in
                    their last 3 sessions (prog-v1 stall detection, ADR-0015)

Deload guidance: keep the weights, cut working sets by about half and stop
every set at RPE 7 or below for one week. That is a common coaching rule of
thumb, not a personalised prescription.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal

FORMULA_VERSION = "deload-v2"
KEY_LIFTS = ("Back Squat", "Barbell Bench Press", "Deadlift", "Overhead Press")
TRAINING_WEEK_SESSIONS = 2
PLANNED_AFTER_WEEKS = 3
LOW_READINESS_BELOW = 50
MIN_CHECKINS = 3
SORE_DAYS = 3
DROP_FRACTION = 0.03
DROPPED_LIFTS = 2
STRAINED_MUSCLES = 3
STALLED_NEEDED = 2
SIGNALS_NEEDED = 2

GUIDANCE = (
    "Deload week: keep your working weights, do about half your usual working sets "
    "and stop every set at RPE 7 or easier. Normal training resumes next week."
)


@dataclass(frozen=True)
class LiftTrend:
    name: str
    recent_best: float | None  # best e1RM in the last 14 days
    previous_best: float | None  # best e1RM in the 21 days before that


@dataclass(frozen=True)
class DeloadInputs:
    weekly_sessions: Sequence[int]  # completed weeks since the last deload, oldest first
    readiness_7d: Sequence[int]
    soreness_7d: Sequence[str]
    lifts: Sequence[LiftTrend]
    strained_muscles: int
    in_deload_week: bool = False
    stalled_lifts: Sequence[str] = ()


@dataclass(frozen=True)
class Signal:
    code: str
    active: bool
    detail: str


@dataclass(frozen=True)
class DeloadAdvice:
    recommended: bool
    kind: Literal["planned", "reactive", "active", "none"]
    signals: list[Signal] = field(default_factory=list)
    training_weeks: int = 0
    guidance: str | None = None
    algo_version: str = FORMULA_VERSION


def consecutive_training_weeks(weekly_sessions: Sequence[int]) -> int:
    count = 0
    for sessions in reversed(weekly_sessions):
        if sessions < TRAINING_WEEK_SESSIONS:
            break
        count += 1
    return count


def reactive_signals(i: DeloadInputs) -> list[Signal]:
    avg = sum(i.readiness_7d) / len(i.readiness_7d) if i.readiness_7d else None
    low = len(i.readiness_7d) >= MIN_CHECKINS and avg is not None and avg < LOW_READINESS_BELOW
    sore = sum(1 for s in i.soreness_7d if s == "a_lot")
    dropped = [
        lt.name
        for lt in i.lifts
        if lt.recent_best is not None
        and lt.previous_best
        and lt.recent_best <= lt.previous_best * (1 - DROP_FRACTION)
    ]
    return [
        Signal(
            "LOW_READINESS",
            low,
            f"{len(i.readiness_7d)} check-ins, average readiness "
            + (f"{avg:.0f}" if avg is not None else "n/a"),
        ),
        Signal("HEAVY_SORENESS", sore >= SORE_DAYS, f"Very sore on {sore} of the last 7 check-ins"),
        Signal(
            "PERFORMANCE_DROP",
            len(dropped) >= DROPPED_LIFTS,
            (
                "e1RM down 3% or more on " + ", ".join(dropped)
                if dropped
                else "No key lift has dropped 3% or more in e1RM"
            ),
        ),
        Signal(
            "FATIGUE_BUILDUP",
            i.strained_muscles >= STRAINED_MUSCLES,
            f"{i.strained_muscles} muscles over range or under 50% readiness",
        ),
        Signal(
            "STALLED_LIFTS",
            len(i.stalled_lifts) >= STALLED_NEEDED,
            (
                "No rep record in 3 sessions on " + ", ".join(i.stalled_lifts)
                if i.stalled_lifts
                else "No stalled lifts"
            ),
        ),
    ]


def advise(i: DeloadInputs) -> DeloadAdvice:
    weeks = consecutive_training_weeks(i.weekly_sessions)
    signals = reactive_signals(i)
    if i.in_deload_week:
        return DeloadAdvice(False, "active", signals, weeks, GUIDANCE)
    if sum(s.active for s in signals) >= SIGNALS_NEEDED:
        return DeloadAdvice(True, "reactive", signals, weeks, GUIDANCE)
    if weeks >= PLANNED_AFTER_WEEKS:
        return DeloadAdvice(True, "planned", signals, weeks, GUIDANCE)
    return DeloadAdvice(False, "none", signals, weeks, None)


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())
