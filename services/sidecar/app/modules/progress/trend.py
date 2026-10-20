"""Trend weight and time-to-goal estimate (deterministic, versioned).

Trend weight is an exponentially smoothed average (the "Hacker's Diet"
method): each weigh-in moves the trend 10 % of the way towards it. Gaps of
several days apply the smoothing once per day, so a weigh-in after a week
away moves the trend more than one taken the next morning:

  alpha_eff = 1 - (1 - 0.10) ^ days_since_previous
  trend_i   = trend_(i-1) + alpha_eff x (weight_i - trend_(i-1))

The rate (kg/week) is the least-squares slope of the trend over the last 28
days. The ETA is a range, using the rate +-25 %, and is always an estimate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal

FORMULA_VERSION = "trend-v1"
ALPHA = 0.10
RATE_WINDOW_DAYS = 28
MIN_RATE_KG_PER_WEEK = 0.05
RANGE_FACTOR = 0.25

Confidence = Literal["low", "medium", "high"]


def smooth(points: list[tuple[datetime, float]]) -> list[float]:
    """Trend value for each (time, weight) point; input must be sorted by time."""
    out: list[float] = []
    trend: float | None = None
    prev: datetime | None = None
    for at, weight in points:
        if trend is None or prev is None:
            trend = weight
        else:
            days = max(1.0, (at - prev).total_seconds() / 86400)
            alpha = 1 - (1 - ALPHA) ** days
            trend = trend + alpha * (weight - trend)
        out.append(round(trend, 2))
        prev = at
    return out


@dataclass(frozen=True)
class Slope:
    kg_per_week: float
    r2: float
    points: int
    span_days: float


def slope(points: list[tuple[datetime, float]]) -> Slope | None:
    """Least-squares slope of (time, value) in kg/week, or None with < 2 points."""
    if len(points) < 2:
        return None
    t0 = points[0][0]
    xs = [(at - t0).total_seconds() / 86400 for at, _ in points]
    ys = [v for _, v in points]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    b = sxy / sxx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (my + b * (x - mx))) ** 2 for x, y in zip(xs, ys, strict=True))
    r2 = 1.0 if ss_tot == 0 else max(0.0, 1 - ss_res / ss_tot)
    return Slope(kg_per_week=b * 7, r2=r2, points=n, span_days=xs[-1] - xs[0])


def confidence(s: Slope | None) -> Confidence:
    if s is None:
        return "low"
    if s.points >= 14 and s.span_days >= 21 and s.r2 >= 0.6:
        return "high"
    if s.points >= 6 and s.span_days >= 14:
        return "medium"
    return "low"


@dataclass(frozen=True)
class Eta:
    goal_kg: float | None
    current_trend_kg: float | None
    rate_kg_per_week: float | None
    eta_from: date | None
    eta_to: date | None
    confidence: Confidence
    on_track: bool
    reason: str | None


def eta(points: list[tuple[datetime, float]], goal_kg: float | None, today: date) -> Eta:
    """Time to reach goal_kg from the trend of `points` (sorted weigh-ins)."""
    if not points:
        return Eta(goal_kg, None, None, None, None, "low", False, "No weigh-ins yet")
    trend = smooth(points)
    current = trend[-1]
    if goal_kg is None:
        return Eta(None, current, None, None, None, "low", False, "Set a target weight")
    window_start = points[-1][0] - timedelta(days=RATE_WINDOW_DAYS)
    recent = [(p[0], t) for p, t in zip(points, trend, strict=True) if p[0] >= window_start]
    s = slope(recent)
    conf = confidence(s)
    remaining = goal_kg - current
    if abs(remaining) < 0.25:
        return Eta(goal_kg, current, s.kg_per_week if s else None, today, today, conf, True, None)
    if s is None or conf == "low":
        return Eta(
            goal_kg,
            current,
            s.kg_per_week if s else None,
            None,
            None,
            "low",
            False,
            "Need at least 6 weigh-ins over 2 weeks",
        )
    rate = s.kg_per_week
    if abs(rate) < MIN_RATE_KG_PER_WEEK or (rate > 0) != (remaining > 0):
        return Eta(
            goal_kg,
            current,
            round(rate, 2),
            None,
            None,
            conf,
            False,
            "Trend is flat or moving away from the goal",
        )
    weeks = remaining / rate
    fast = weeks / (1 + RANGE_FACTOR)
    slow = weeks / (1 - RANGE_FACTOR)
    return Eta(
        goal_kg=goal_kg,
        current_trend_kg=current,
        rate_kg_per_week=round(rate, 2),
        eta_from=today + timedelta(days=round(fast * 7)),
        eta_to=today + timedelta(days=round(slow * 7)),
        confidence=conf,
        on_track=True,
        reason=None,
    )
