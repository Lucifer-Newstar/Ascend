"""schedule-v1: the training schedule as plain rules, no I/O.

The program stays a rotation (programs-v1: the next session is the day after the last one
you trained). The schedule only says *which weekdays* you mean to train and at what time:
the other weekdays are planned rest (neutral for the streak), reminders wait for your time,
and the week view lines the coming sessions up on your days.

- Weekdays are 0 = Monday ... 6 = Sunday, as Python's ``date.weekday()``.
- A week starts on Monday, local date.
- A short session (``short_session``) keeps the first moves of today's session at two sets
  each with short rests, trimmed to fit the minutes asked for. Any logged set keeps the
  streak, so a 10-minute day counts.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

ALGO_VERSION = "schedule-v1"
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
WEEKDAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

# Spread n training days over a week with rest between them where it fits.
DEFAULT_DAYS: dict[int, tuple[int, ...]] = {
    1: (2,),
    2: (1, 4),
    3: (0, 2, 4),
    4: (0, 1, 3, 4),
    5: (0, 1, 2, 4, 5),
    6: (0, 1, 2, 3, 4, 5),
    7: (0, 1, 2, 3, 4, 5, 6),
}

_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

# Short session: seconds of work per set and the longest rest kept.
SET_WORK_S = 40
SHORT_REST_CAP_S = 45
SHORT_SETS = 2
SHORT_MAX_MOVES = 3


def parse_days(text: str | None) -> tuple[int, ...]:
    """ "0,2,4" -> (0, 2, 4); junk and duplicates are dropped."""
    if not text:
        return ()
    out = {int(p) for p in text.split(",") if p.strip().isdigit() and 0 <= int(p) <= 6}
    return tuple(sorted(out))


def format_days(days: Iterable[int]) -> str:
    return ",".join(str(d) for d in sorted(set(days)))


def default_days(n: int) -> tuple[int, ...]:
    return DEFAULT_DAYS[max(1, min(7, n))]


def valid_time(text: str | None) -> bool:
    return bool(text) and bool(_TIME.match(text or ""))


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def days_label(days: Sequence[int]) -> str:
    """(0, 2, 4) -> "Mon, Wed, Fri"."""
    return ", ".join(WEEKDAYS[d] for d in sorted(days)) if days else "no days"


@dataclass(frozen=True)
class DayPlan:
    day: date
    planned: bool
    done: bool
    session: str | None
    today: bool
    past: bool


def week_view(
    monday: date,
    planned: Sequence[int],
    trained: Iterable[date],
    upcoming: Sequence[str],
    today: date,
) -> list[DayPlan]:
    """Seven days from ``monday``: planned (a training weekday), done (trained that day) and,
    for planned days from today on that are not done yet, the coming sessions in order."""
    done_days = set(trained)
    plan = set(planned)
    queue = list(upcoming)
    out: list[DayPlan] = []
    for i in range(7):
        d = monday + timedelta(days=i)
        is_planned = d.weekday() in plan
        is_done = d in done_days
        session: str | None = None
        if is_planned and not is_done and d >= today and queue:
            session = queue.pop(0)
            queue.append(session)  # the rotation continues
        out.append(DayPlan(d, is_planned, is_done, session, d == today, d < today))
    return out


@dataclass(frozen=True)
class ShortItem:
    index: int  # position in the full session
    sets: int
    rest_s: int


def short_session(
    items: Sequence[tuple[str, int, str]], minutes: int = 10
) -> tuple[list[ShortItem], int]:
    """``items`` = (exercise, rest_s, measure) of today's session in order. Keep up to three
    moves at two sets each, rests capped at 45 s, dropping moves until it fits ``minutes``.
    Returns the kept items and the estimated minutes (rounded up)."""
    budget = max(5, minutes) * 60
    picked: list[ShortItem] = []
    used = 0
    for i, (_name, rest_s, measure) in enumerate(items):
        if len(picked) >= SHORT_MAX_MOVES:
            break
        if measure == "time":
            continue  # a 20-minute run does not shrink into ten
        rest = min(max(rest_s, 15), SHORT_REST_CAP_S)
        cost = SHORT_SETS * SET_WORK_S + (SHORT_SETS - 1) * rest + (rest if picked else 0)
        if used + cost > budget:
            break
        picked.append(ShortItem(i, SHORT_SETS, rest))
        used += cost
    return picked, max(1, -(-used // 60)) if picked else 0
