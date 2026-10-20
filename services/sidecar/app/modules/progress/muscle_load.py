"""Muscle load + recovery engine (deterministic, plan v2 "Load model").

  effort(RPE)   = 1.0 if RPE >= 7 . 0.5 if 5-6.5 . 0.25 below . no RPE -> 1.0
  ES (effective sets) per set and muscle = weight(exercise, muscle) x effort
  fatigue F_m(t) = sum ES x 2^(-(t - t_set) / half_life_m)
  readiness_m    = 1 - min(1, F_m / C_m)

Status precedence: over > recovering > under / optimal.
  over        ES_7d > weekly_high x 1.25
  recovering  readiness < 0.70
  under       ES_7d < weekly_low
  optimal     otherwise
  no_data     nothing logged for this muscle in 28 days
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from app.modules.progress.taxonomy import MUSCLES, Muscle

FORMULA_VERSION = "load-v1"
RECOVERING_BELOW = 0.70
READY_AT_FATIGUE_FRACTION = 0.30
OVER_FACTOR = 1.25

Status = Literal["under", "optimal", "recovering", "over", "no_data"]


def effort(rpe: float | None) -> float:
    if rpe is None or rpe >= 7:
        return 1.0
    if rpe >= 5:
        return 0.5
    return 0.25


@dataclass(frozen=True)
class Contribution:
    """One set's effective-set contribution to one muscle."""

    muscle: str
    es: float
    at: datetime


@dataclass(frozen=True)
class MuscleState:
    key: str
    label: str
    group: str
    map_slug: str
    status: Status
    es_7d: float
    weekly_low: float
    weekly_high: float
    fatigue: float
    readiness: float
    ready_at: datetime | None


def decayed(es: float, hours_ago: float, half_life_h: float) -> float:
    return es * 2 ** (-max(0.0, hours_ago) / half_life_h)


def _ready_at(fatigue: float, muscle: Muscle, now: datetime) -> datetime | None:
    threshold = READY_AT_FATIGUE_FRACTION * muscle.capacity_es
    if fatigue <= threshold:
        return None
    hours = muscle.half_life_h * math.log2(fatigue / threshold)
    return now + timedelta(hours=hours)


def classify(muscle: Muscle, es_7d: float, readiness: float, has_data: bool) -> Status:
    if not has_data:
        return "no_data"
    if es_7d > muscle.weekly_high * OVER_FACTOR:
        return "over"
    if readiness < RECOVERING_BELOW:
        return "recovering"
    if es_7d < muscle.weekly_low:
        return "under"
    return "optimal"


def compute_states(contributions: Iterable[Contribution], now: datetime) -> list[MuscleState]:
    contribs = [c for c in contributions if c.at <= now]
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=28)
    states: list[MuscleState] = []
    for m in MUSCLES:
        mine = [c for c in contribs if c.muscle == m.key]
        es_7d = sum(c.es for c in mine if c.at >= week_ago)
        fatigue = sum(decayed(c.es, (now - c.at).total_seconds() / 3600, m.half_life_h) for c in mine)
        readiness = 1 - min(1.0, fatigue / m.capacity_es)
        has_data = any(c.at >= month_ago for c in mine)
        states.append(
            MuscleState(
                key=m.key,
                label=m.label,
                group=m.group,
                map_slug=m.map_slug,
                status=classify(m, es_7d, readiness, has_data),
                es_7d=round(es_7d, 2),
                weekly_low=m.weekly_low,
                weekly_high=m.weekly_high,
                fatigue=round(fatigue, 2),
                readiness=round(readiness, 3),
                ready_at=_ready_at(fatigue, m, now),
            )
        )
    return states


STATUS_PRECEDENCE: dict[str, int] = {
    "over": 4,
    "recovering": 3,
    "under": 2,
    "optimal": 1,
    "no_data": 0,
}


def worst_status(statuses: Iterable[str]) -> str:
    """Several regions share one figure slug (e.g. 3 delt heads); show the most urgent."""
    return max(statuses, key=lambda s: STATUS_PRECEDENCE[s], default="no_data")
