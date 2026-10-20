"""E1 recovery and readiness engine, version recovery-v2 (ADR-0014).

Pure functions only: the inputs are logged sets (already joined to their exercise's
muscle weights), an optional morning check-in and the personal decay factors; the
output is one state per muscle region. No database, clock or randomness.

Dose. Each logged set adds an effective-set dose to every muscle the exercise works:

    ES = w(exercise, muscle) x I(RIR) x V(set)

  w     the exercise's muscle weight (1.0 primary, 0.5 or 0.3 secondary, from the library)
  I     intensity, from reps in reserve: I = clamp(1 - 0.1 x max(0, RIR - 1), 0.3, 1).
        RIR 0-1 counts fully, RIR 3 counts 0.8, RIR 5 counts 0.6 and very easy sets 0.3.
        RIR = 10 - RPE when RPE is logged (Zourdos et al. 2016 RIR-based RPE scale).
        Without RPE, RIR is estimated from the user's own best e1RM for that exercise
        (Epley inverse: reps possible = 30 x (e1RM / load - 1), RIR = that - reps done),
        and with neither the population default RIR 2 is used (I = 0.9).
  V     volume: 1 for 5-20 reps, 0.85 for 1-4 reps (heavy singles to quads fatigue the
        muscle less per set), 1.1 above 20 reps; a hold counts seconds / 30 (0.25-1.5);
        a timed bout counts min(3, minutes / 10), the load-v1 time rule.

Decay. Fatigue of muscle m at time t:

    F_m(t) = sum_i ES_i,m x 2 ^ (-(t - t_i) / (h_m x k_g))

  h_m   the muscle's prior half-life in hours (taxonomy.py, literature-informed estimates)
  k_g   the user's personal factor for the muscle's group (Push, Shoulders, Pull, Arms,
        Core, Legs), 1.0 until personalised, always in [0.6, 1.6] (see personal.py).

Check-in modifier (same day only, optional). Poor sleep and soreness make the same
fatigue count for more:

    M = 1 + 0.20 x (1 - sleep_unit) + soreness term
  sleep_unit = (sleep - 1) / 4 on the 1-5 scale; soreness "some" adds 0.10 and "a lot"
  0.25, only for muscles trained in the last 72 hours (DOMS belongs to trained muscles).
  M is therefore in [1, 1.45].

Readiness and status:

    readiness_m = 1 - min(1, M x F_m / C_m)        (C_m = capacity, taxonomy.py)
    ready_at    = when readiness reaches 0.70:  t + h_m k_g log2(M F_m / (0.3 C_m))

  status: over (ES this week > 1.25 x weekly_high), recovering (readiness < 0.70),
  under (ES this week < weekly_low), optimal, no_data (nothing in 28 days). The bands are
  the same as load-v1, so the muscle map, quests and coach keep their meaning.

Every state carries its inputs and formula, which the "Why?" panels show as they are.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

from app.modules.progress.taxonomy import MUSCLES, Muscle

ALGO_VERSION = "recovery-v2"

GROUPS: tuple[str, ...] = tuple(dict.fromkeys(m.group for m in MUSCLES))
K_MIN, K_MAX = 0.6, 1.6
DEFAULT_RIR = 2.0
RECOVERING_BELOW = 0.70
READY_AT_FATIGUE_FRACTION = 1 - RECOVERING_BELOW
OVER_FACTOR = 1.25
SLEEP_WEIGHT = 0.20
SORENESS_ADD: dict[str, float] = {"none": 0.0, "some": 0.10, "a_lot": 0.25}
SORENESS_WINDOW_H = 72.0
HOLD_SECONDS_PER_SET = 30.0
MINUTES_PER_TIME_SET = 10.0
MAX_TIME_SETS = 3.0
MAX_E1RM_REPS = 12
LOOKBACK_DAYS = 28
# Contributions older than this many half-lives are below 0.1 % and skipped.
MAX_HALF_LIVES = 10.0

Kind = Literal["reps", "hold", "time"]
Status = Literal["under", "optimal", "recovering", "over", "no_data"]
RirSource = Literal["rpe", "e1rm", "default"]


@dataclass(frozen=True)
class SetInput:
    """One logged set with what the dose needs. `muscles` maps muscle key -> weight."""

    at: datetime
    muscles: Mapping[str, float]
    kind: Kind = "reps"
    reps: int = 0
    weight_kg: float = 0.0
    rpe: float | None = None
    duration_s: int | None = None
    # The user's best e1RM for this exercise before this set (for the RIR estimate).
    e1rm_ref: float | None = None
    exercise: str = ""


@dataclass(frozen=True)
class CheckinInput:
    sleep: int  # 1-5
    soreness: str  # none | some | a_lot


@dataclass(frozen=True)
class Dose:
    es: float  # before the muscle weight
    intensity: float
    volume: float
    rir: float | None
    rir_source: RirSource


@dataclass(frozen=True)
class Contribution:
    muscle: str
    es: float
    at: datetime
    exercise: str = ""


@dataclass(frozen=True)
class MuscleRecovery:
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
    # Explainability: what went into the numbers above.
    half_life_h: float
    k: float
    capacity: float
    modifier: float
    readiness_population: float
    last_trained: datetime | None
    top_sets: list[tuple[str, float, float]] = field(default_factory=list)
    # (exercise, dose now after decay, hours ago) of the biggest remaining contributions


def clamp(x: float, lo: float, hi: float) -> float:
    if math.isnan(x):
        return lo
    return lo if x < lo else hi if x > hi else x


def intensity(rir: float) -> float:
    """I(RIR) = clamp(1 - 0.1 max(0, RIR - 1), 0.3, 1)."""
    return clamp(1.0 - 0.1 * max(0.0, rir - 1.0), 0.3, 1.0)


def estimate_rir(s: SetInput) -> tuple[float, RirSource]:
    """RIR from RPE, else from the user's own e1RM (Epley inverse), else the default."""
    if s.rpe is not None and not math.isnan(s.rpe):
        return clamp(10.0 - s.rpe, 0.0, 10.0), "rpe"
    if (
        s.kind == "reps"
        and s.e1rm_ref
        and s.weight_kg > 0
        and 1 <= s.reps <= MAX_E1RM_REPS
        and s.e1rm_ref > s.weight_kg
    ):
        possible = 30.0 * (s.e1rm_ref / s.weight_kg - 1.0)
        return clamp(possible - s.reps, 0.0, 10.0), "e1rm"
    return DEFAULT_RIR, "default"


def volume(s: SetInput) -> float:
    if s.kind == "hold":
        return clamp((s.duration_s or 0) / HOLD_SECONDS_PER_SET, 0.25, 1.5) if s.duration_s else 0
    if s.kind == "time":
        if not s.duration_s or s.duration_s <= 0:
            return 0.0
        return min(MAX_TIME_SETS, s.duration_s / 60 / MINUTES_PER_TIME_SET)
    if s.reps <= 0:
        return 0.0
    if s.reps <= 4:
        return 0.85
    if s.reps > 20:
        return 1.1
    return 1.0


def dose(s: SetInput) -> Dose:
    rir, source = estimate_rir(s)
    i = intensity(rir)
    v = volume(s)
    return Dose(es=i * v, intensity=i, volume=v, rir=rir, rir_source=source)


def contributions(sets: Iterable[SetInput]) -> list[Contribution]:
    out: list[Contribution] = []
    for s in sets:
        d = dose(s)
        if d.es <= 0:
            continue
        for muscle, w in s.muscles.items():
            es = w * d.es
            if es > 0 and math.isfinite(es):
                out.append(Contribution(muscle, round(es, 4), s.at, s.exercise))
    return out


def decay(hours_ago: float, half_life_h: float) -> float:
    return float(2.0 ** (-max(0.0, hours_ago) / half_life_h))


def checkin_modifier(c: CheckinInput | None, trained_recently: bool) -> float:
    """M = 1 + 0.20 (1 - sleep_unit) + soreness (only for recently trained muscles)."""
    if c is None:
        return 1.0
    sleep_unit = clamp((c.sleep - 1) / 4, 0.0, 1.0)
    m = 1.0 + SLEEP_WEIGHT * (1.0 - sleep_unit)
    if trained_recently:
        m += SORENESS_ADD.get(c.soreness, 0.0)
    return m


def fatigue(
    contribs: Sequence[Contribution], now: datetime, half_life_h: float
) -> tuple[float, list[tuple[str, float, float]]]:
    total = 0.0
    parts: list[tuple[str, float, float]] = []
    horizon = half_life_h * MAX_HALF_LIVES
    for c in contribs:
        hours = (now - c.at).total_seconds() / 3600
        if hours < 0 or hours > horizon:
            continue
        v = c.es * decay(hours, half_life_h)
        total += v
        parts.append((c.exercise, v, hours))
    parts.sort(key=lambda p: -p[1])
    return total, parts


def readiness_from(fatigue_value: float, capacity: float, modifier: float = 1.0) -> float:
    return 1.0 - min(1.0, modifier * max(0.0, fatigue_value) / capacity)


def ready_at(
    fatigue_value: float, m: Muscle, half_life_h: float, modifier: float, now: datetime
) -> datetime | None:
    threshold = READY_AT_FATIGUE_FRACTION * m.capacity_es
    eff = modifier * fatigue_value
    if eff <= threshold:
        return None
    return now + timedelta(hours=half_life_h * math.log2(eff / threshold))


def classify(m: Muscle, es_7d: float, readiness: float, has_data: bool) -> Status:
    if not has_data:
        return "no_data"
    if es_7d > m.weekly_high * OVER_FACTOR:
        return "over"
    if readiness < RECOVERING_BELOW:
        return "recovering"
    if es_7d < m.weekly_low:
        return "under"
    return "optimal"


def compute(
    sets: Iterable[SetInput],
    now: datetime,
    k: Mapping[str, float] | None = None,
    checkin: CheckinInput | None = None,
) -> list[MuscleRecovery]:
    """Every muscle's state at `now` (sets after `now` are ignored)."""
    by_muscle: dict[str, list[Contribution]] = {}
    for c in contributions(s for s in sets if s.at <= now):
        by_muscle.setdefault(c.muscle, []).append(c)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=LOOKBACK_DAYS)
    out: list[MuscleRecovery] = []
    for m in MUSCLES:
        mine = by_muscle.get(m.key, [])
        kg = clamp((k or {}).get(m.group, 1.0), K_MIN, K_MAX)
        h = m.half_life_h * kg
        f, parts = fatigue(mine, now, h)
        f_pop, _ = fatigue(mine, now, m.half_life_h) if kg != 1.0 else (f, parts)
        last = max((c.at for c in mine), default=None)
        recent = last is not None and (now - last).total_seconds() / 3600 <= SORENESS_WINDOW_H
        mod = checkin_modifier(checkin, recent)
        r = readiness_from(f, m.capacity_es, mod)
        es_7d = sum(c.es for c in mine if c.at >= week_ago)
        has_data = last is not None and last >= month_ago
        out.append(
            MuscleRecovery(
                key=m.key,
                label=m.label,
                group=m.group,
                map_slug=m.map_slug,
                status=classify(m, es_7d, r, has_data),
                es_7d=round(es_7d, 2),
                weekly_low=m.weekly_low,
                weekly_high=m.weekly_high,
                fatigue=round(f, 3),
                readiness=round(r, 3),
                ready_at=ready_at(f, m, h, mod, now),
                half_life_h=round(h, 1),
                k=round(kg, 3),
                capacity=m.capacity_es,
                modifier=round(mod, 3),
                readiness_population=round(readiness_from(f_pop, m.capacity_es, mod), 3),
                last_trained=last,
                top_sets=[(e, round(v, 3), round(hr, 1)) for e, v, hr in parts[:5]],
            )
        )
    return out


def formula() -> str:
    return (
        "readiness = 1 - min(1, M x F / C); F = sum of ES x 2^(-hours / (h x k)); "
        "ES = muscle weight x I(RIR) x V"
    )
