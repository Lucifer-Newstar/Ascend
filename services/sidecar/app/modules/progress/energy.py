"""Calories-out estimate for the burn ring (MET method). ESTIMATE ONLY.

kcal = MET x body weight (kg) x hours. Resistance training is taken as
MET 5.0 (Compendium of Physical Activities, "weight lifting, vigorous" is
~6.0, "moderate" ~3.5). Unfinished sessions count 2.5 min per logged set.

Timed sets (cardio, martial arts, stretching, meditation) use their own
activity MET over their own duration; the rest of the session's minutes are
counted as lifting.
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


def timed_kcal(met: float, duration_s: int, weight_kg: float) -> float:
    return met * weight_kg * (duration_s / 3600)


def workout_kcal(
    duration_min: float | None,
    lifting_sets: int,
    timed: list[tuple[float, int]],
    weight_kg: float,
) -> float:
    """Burn for one session. `timed` holds (MET, duration_s) for each timed set."""
    timed_kcal_total = sum(timed_kcal(met, secs, weight_kg) for met, secs in timed)
    timed_min = sum(secs for _, secs in timed) / 60
    if duration_min is not None and duration_min > 0:
        lifting_min = max(0.0, min(duration_min, MAX_SESSION_MINUTES) - timed_min)
    else:
        lifting_min = lifting_sets * MINUTES_PER_SET_ESTIMATE
    if lifting_sets == 0:
        lifting_min = 0.0
    return timed_kcal_total + strength_kcal(lifting_min, weight_kg)
