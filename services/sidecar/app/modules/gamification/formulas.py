"""Deterministic, versioned game formulas.

All XP, level and rank numbers come from here. The AI coach never computes
them; it can only explain them. Bump FORMULA_VERSION when any constant
changes: every xp_event row stores the version it was awarded under.
"""

from __future__ import annotations

from dataclasses import dataclass

# xp-v2: adds minute-based XP for timed sets (lifting constants unchanged from xp-v1).
# xp-v3: anti-farming. Set XP stops after 10 sets of one exercise or 40 sets in a day;
#        PR XP at most once per exercise per day and 3 times a day, never for a jump of
#        more than 25% over the previous best (a likely typo); the session bonus needs 3
#        sets (or 10 timed minutes), counts at most 10 minutes per set, and is paid twice
#        a day at most. Deleting a set reverses its XP; an edit can remove PR XP, never add it.
FORMULA_VERSION = "xp-v3"

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


# --- anti-farming (xp-v3) --------------------------------------------------
SETS_PER_EXERCISE_DAY = 10
SETS_PER_DAY = 40
PR_PER_DAY = 3
PR_MAX_JUMP = 0.25
SESSION_MIN_SETS = 3
SESSION_MIN_TIMED_MINUTES = 10
SESSION_MINUTES_PER_SET = 10
SESSIONS_PAID_PER_DAY = 2


def set_xp_allowed(sets_of_exercise_before: int, sets_today_before: int) -> bool:
    """Whether a set still earns XP today (diminishing returns: none past the limits)."""
    return sets_of_exercise_before < SETS_PER_EXERCISE_DAY and sets_today_before < SETS_PER_DAY


def pr_xp_allowed(
    value: float | None,
    previous_best: float | None,
    prs_of_exercise_today: int,
    prs_today: int,
) -> bool:
    """PR XP: once per exercise per day, PR_PER_DAY a day, and not for implausible jumps."""
    if value is None or previous_best is None or previous_best <= 0:
        return False
    if value > previous_best * (1 + PR_MAX_JUMP):
        return False
    return prs_of_exercise_today == 0 and prs_today < PR_PER_DAY


def session_minutes(wall_minutes: float, sets: int, timed_minutes: float) -> float:
    """Minutes that earn session XP: wall time, but no more than the work shows."""
    evidence = sets * SESSION_MINUTES_PER_SET + timed_minutes
    return max(0.0, min(wall_minutes, evidence))


def session_qualifies(sets: int, timed_minutes: float, paid_today: int) -> bool:
    if paid_today >= SESSIONS_PAID_PER_DAY:
        return False
    return sets >= SESSION_MIN_SETS or timed_minutes >= SESSION_MIN_TIMED_MINUTES


def set_xp(rpe: float | None) -> int:
    """XP for one working set. No RPE logged counts as a hard set (plan v2 rule)."""
    if rpe is None or rpe >= HARD_SET_RPE:
        return XP_PER_HARD_SET
    return XP_PER_EASY_SET


# Timed sets: XP per active minute, capped per set so one long bout can't dominate.
XP_PER_TIMED_MINUTE = 0.5
TIMED_SET_CAP = 30
XP_PER_CALM_MINUTE = 1.0
CALM_SET_CAP = 20


def timed_set_xp(duration_s: int | None, section: str) -> int:
    """XP for a cardio / martial arts / flexibility bout or a meditation sit."""
    if not duration_s or duration_s <= 0:
        return 0
    minutes = duration_s / 60
    if section == "meditation":
        return min(CALM_SET_CAP, round(minutes * XP_PER_CALM_MINUTE))
    return min(TIMED_SET_CAP, max(1, round(minutes * XP_PER_TIMED_MINUTE)))


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


# v1.3 (review M8): the first session after an unplanned miss earns a welcome-back bonus,
# at most once per calendar week, so coming back is rewarded instead of shamed.
WELCOME_BACK_XP = 25


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


# v1.3 (review M5, near goals): each rank shows three steps, E1 -> E2 -> E3 -> D1. Display
# only: levels and ranks are unchanged. S has no next rank, so its steps are 10 levels each.
SUB_STEPS = 3
S_STEP_LEVELS = 10


def _sub_starts(i: int) -> list[int]:
    start = RANKS[i][2]
    if i + 1 < len(RANKS):
        span = RANKS[i + 1][2] - start
        return [start + (span * k) // SUB_STEPS for k in range(SUB_STEPS)]
    return [start + S_STEP_LEVELS * k for k in range(SUB_STEPS)]


def sub_rank_for_level(level: int) -> tuple[str, str | None, int | None]:
    """(this sub-rank, the next one, the level it starts at); the last has no next."""
    steps = [
        (f"{r[0]}{k + 1}", start)
        for i, r in enumerate(RANKS)
        for k, start in enumerate(_sub_starts(i))
    ]
    idx = max((n for n, (_, start) in enumerate(steps) if level >= start), default=0)
    if idx + 1 < len(steps):
        return steps[idx][0], steps[idx + 1][0], steps[idx + 1][1]
    return steps[idx][0], None, None
