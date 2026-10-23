"""Streaks with reasons, recomputed from history (no hidden mutable counter).

Rules (v1.2, replacing the automatic freezes of plan v2):
  * an active day = any workout finished, any quest item completed, or any quick log
    (a set, a meal or a weigh-in);
  * a missed day keeps the streak when you give a reason for it by the end of the next
    day; it does not add to the streak ("excused");
  * two missed days in a row reset the streak, reason or not;
  * a missed day with no reason resets the streak once the next day is over;
  * yesterday can still get its reason today, so it does not break the streak yet: it is
    reported as `reason_due` so the app can ask;
  * today not being active yet does not break the streak (the day isn't over).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class StreakState:
    current: int
    best: int
    excused: int
    active_today: bool
    reason_due: date | None = None


def excused_ok(missed: date, given_on: date) -> bool:
    """A reason counts when it was given on the missed day itself or the day after."""
    return given_on <= missed + timedelta(days=1)


def compute_streak(
    active_days: Iterable[date],
    today: date,
    reasons: Mapping[date, date] | None = None,
) -> StreakState:
    """`reasons` maps a missed day to the day its reason was given."""
    days = sorted({d for d in active_days if d <= today})
    if not days:
        return StreakState(0, 0, 0, False)
    active = set(days)
    reasons = reasons or {}
    current = best = excused = 0
    due: date | None = None
    prev_missed = False
    cursor = days[0]
    yesterday = today - timedelta(days=1)
    # Walk every day from the first active day up to yesterday; today is judged leniently.
    while cursor < today:
        if cursor in active:
            current += 1
            prev_missed = False
        else:
            given = reasons.get(cursor)
            if prev_missed:
                current = 0  # two missed days in a row
                excused = 0
            elif given is not None and excused_ok(cursor, given):
                excused += 1  # kept, but an excused day does not add to the streak
            elif cursor == yesterday and current > 0:
                due = cursor  # the reason can still come today
            else:
                current = 0
                excused = 0
            prev_missed = True
        best = max(best, current)
        cursor += timedelta(days=1)
    active_today = today in active
    if active_today:
        current += 1
        best = max(best, current)
    return StreakState(current, best, excused, active_today, due)
