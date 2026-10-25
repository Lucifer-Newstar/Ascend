"""Streaks with reasons, recomputed from history (no hidden mutable counter).

Rules (v1.3; v1.2 replaced the automatic freezes of plan v2):
  * an active day = a training day: a finished workout or at least one logged set. Meals,
    weigh-ins and quest ticks earn XP but no longer keep the streak (review S2);
  * a planned rest day of the program you follow is neutral: it neither adds to the
    streak nor breaks it, and never asks for a reason (review S1);
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
    rest_days: Iterable[date] | None = None,
) -> StreakState:
    """`reasons` maps a missed day to the day its reason was given; `rest_days` are the
    followed program's planned rest days (skipped: they keep the streak as it is)."""
    days = sorted({d for d in active_days if d <= today})
    if not days:
        return StreakState(0, 0, 0, False)
    active = set(days)
    rest = set(rest_days or ()) - active
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
        elif cursor in rest:
            pass  # a planned rest day: neutral
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


# v1.3 (review S5, S6, 1.6): numbers beside the streak that never reset.
SESSION_MILESTONES = (1, 3, 5, 10, 25, 50, 100)


def next_milestone(sessions: int) -> int | None:
    """The next lifetime-session milestone, or None past the last one."""
    return next((m for m in SESSION_MILESTONES if m > sessions), None)


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def weeks_in_a_row(met_weeks: Iterable[date], today: date) -> int:
    """Weeks (Monday starts) in a row whose plan was met. The current week counts once it
    is met, and does not break the run while it is still going."""
    met = set(met_weeks)
    week = week_start(today)
    if week not in met:
        week -= timedelta(days=7)
    n = 0
    while week in met:
        n += 1
        week -= timedelta(days=7)
    return n
