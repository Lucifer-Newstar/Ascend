"""Streaks with freezes, recomputed from history (no hidden mutable counter).

Rules (plan v2):
  * an active day = any workout finished or any quest item completed;
  * every 7 consecutive active days earns 1 freeze, hold at most 2;
  * a missed day automatically spends a freeze instead of breaking the streak;
  * today not being active yet does not break the streak (the day isn't over).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

FREEZE_EVERY = 7
MAX_FREEZES = 2


@dataclass(frozen=True)
class StreakState:
    current: int
    best: int
    freezes_held: int
    freezes_used: int
    active_today: bool


def compute_streak(active_days: Iterable[date], today: date) -> StreakState:
    days = sorted({d for d in active_days if d <= today})
    if not days:
        return StreakState(0, 0, 0, 0, False)
    active = set(days)
    current = best = freezes = used = 0
    run_since_freeze = 0
    cursor = days[0]
    # Walk every day from the first active day up to yesterday; today is judged leniently.
    while cursor < today:
        if cursor in active:
            current += 1
            run_since_freeze += 1
            if run_since_freeze == FREEZE_EVERY:
                freezes = min(MAX_FREEZES, freezes + 1)
                run_since_freeze = 0
        elif freezes > 0 and current > 0:
            freezes -= 1
            used += 1  # streak survives, but a frozen day does not add to it
        else:
            current = 0
            run_since_freeze = 0
        best = max(best, current)
        cursor += timedelta(days=1)
    active_today = today in active
    if active_today:
        current += 1
        best = max(best, current)
    return StreakState(current, best, freezes, used, active_today)
