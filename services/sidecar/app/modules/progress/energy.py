"""Calories-out estimate for the burn ring (MET method). ESTIMATE ONLY.

kcal = MET x body weight (kg) x hours. Resistance training is taken as
MET 5.0 (Compendium of Physical Activities, "weight lifting, vigorous" is
~6.0, "moderate" ~3.5). Unfinished sessions count 2.5 min per logged set.
"""

from __future__ import annotations

STRENGTH_MET = 5.0
MINUTES_PER_SET_ESTIMATE = 2.5
DEFAULT_BURN_TARGET_KCAL = 350
MAX_SESSION_MINUTES = 180


def session_minutes(duration_min: float | None, set_count: int) -> float:
    if duration_min is None or duration_min <= 0:
        return set_count * MINUTES_PER_SET_ESTIMATE
    return min(duration_min, MAX_SESSION_MINUTES)


def strength_kcal(minutes: float, weight_kg: float) -> float:
    return STRENGTH_MET * weight_kg * (minutes / 60)
