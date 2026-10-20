"""Personal-record detection with the Epley one-rep-max estimate.

Epley (1985): e1RM = w x (1 + reps / 30). A standard estimation formula, only
meaningful for roughly 1-10 reps, so higher-rep sets never count as PRs.
"""

from __future__ import annotations

FORMULA_VERSION = "pr-epley-v1"
MAX_REPS_FOR_E1RM = 10


def epley_e1rm(weight_kg: float, reps: int) -> float:
    if weight_kg < 0 or reps < 1:
        raise ValueError("weight must be >= 0 and reps >= 1")
    if reps == 1:
        return float(weight_kg)
    return weight_kg * (1 + reps / 30)


def e1rm_or_none(weight_kg: float, reps: int) -> float | None:
    """e1RM for PR purposes, or None when the set can't be used (bodyweight, >10 reps)."""
    if weight_kg <= 0 or reps < 1 or reps > MAX_REPS_FOR_E1RM:
        return None
    return round(epley_e1rm(weight_kg, reps), 1)


def is_new_pr(candidate_e1rm: float | None, previous_best: float | None) -> bool:
    """A PR is a strictly higher e1RM than any earlier set of the same exercise.

    The very first logged set of an exercise is a baseline, not a PR.
    """
    if candidate_e1rm is None or previous_best is None:
        return False
    return candidate_e1rm > previous_best + 1e-9
