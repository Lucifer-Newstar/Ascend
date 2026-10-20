"""Deterministic, versioned game formulas.

All XP, level and rank numbers come from here. The AI coach never computes
them; it can only explain them. Bump FORMULA_VERSION when any constant
changes: every xp_event row stores the version it was awarded under.
"""

from __future__ import annotations

from dataclasses import dataclass

FORMULA_VERSION = "xp-v1"

# --- XP rules -------------------------------------------------------------
HARD_SET_RPE = 7.0
XP_PER_HARD_SET = 3
XP_PER_EASY_SET = 1
SESSION_BASE_XP = 20
XP_PER_ACTIVE_MINUTE = 0.5
SESSION_CAP = 150
XP_PER_MEAL = 5
MEAL_DAILY_CAP = 20
PR_XP = 40
DAILY_CAP = 600
STREAK_BONUS_PER_DAY = 0.02
STREAK_BONUS_MAX = 1.3


def set_xp(rpe: float | None) -> int:
    """XP for one working set. No RPE logged counts as a hard set (plan v2 rule)."""
    if rpe is None or rpe >= HARD_SET_RPE:
        return XP_PER_HARD_SET
    return XP_PER_EASY_SET


def session_completion_xp(active_minutes: float, set_xp_already: int) -> int:
    """Bonus for finishing a session: base + minutes, keeping the session under its cap."""
    raw = SESSION_BASE_XP + XP_PER_ACTIVE_MINUTE * max(0.0, active_minutes)
    return max(0, min(round(raw), SESSION_CAP - set_xp_already))


def meal_xp(meals_already_today: int) -> int:
    earned = meals_already_today * XP_PER_MEAL
    return max(0, min(XP_PER_MEAL, MEAL_DAILY_CAP - earned))


def streak_multiplier(streak_days: int) -> float:
    return min(STREAK_BONUS_MAX, 1 + STREAK_BONUS_PER_DAY * max(0, streak_days))


def apply_daily_cap(amount: int, earned_today: int) -> int:
    return max(0, min(amount, DAILY_CAP - earned_today))


# --- Levels ---------------------------------------------------------------


def xp_to_next(level: int) -> int:
    """XP needed to go from `level` to `level + 1` = round(100 x L^1.3)."""
    if level < 1:
        raise ValueError("level starts at 1")
    return round(100 * level**1.3)


@dataclass(frozen=True)
class LevelInfo:
    level: int
    xp_into_level: int
    xp_for_next: int
    total_xp: int

    @property
    def progress(self) -> float:
        return self.xp_into_level / self.xp_for_next


def level_from_total(total_xp: int) -> LevelInfo:
    level, remaining = 1, max(0, total_xp)
    while remaining >= xp_to_next(level):
        remaining -= xp_to_next(level)
        level += 1
    return LevelInfo(level, remaining, xp_to_next(level), max(0, total_xp))


# --- Ranks ----------------------------------------------------------------

# (letter, title, first level of the rank)
RANKS: list[tuple[str, str, int]] = [
    ("E", "Initiate", 1),
    ("D", "Striver", 10),
    ("C", "Vanguard", 20),
    ("B", "Warden", 35),
    ("A", "Paragon", 50),
    ("S", "Ascendant", 70),
]


def rank_for_level(level: int) -> tuple[str, str]:
    letter, title = RANKS[0][0], RANKS[0][1]
    for r_letter, r_title, min_level in RANKS:
        if level >= min_level:
            letter, title = r_letter, r_title
    return letter, title
