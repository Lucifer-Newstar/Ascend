"""Schedule service: reads and writes the schedule in settings, builds the week view and
today's short session. Settings keys: ``schedule.days`` ("0,2,4"), ``schedule.time``
("18:30" or ""), ``schedule.since`` (the local date it was set) and ``schedule.week.<monday>``
for a week picked on the plan-the-week screen."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.modules.progress import service as progress
from app.modules.schedule import rules
from app.modules.schedule.schemas import (
    ScheduleOut,
    ShortItemOut,
    ShortSessionOut,
    WeekDayOut,
    WeekOut,
)

DAYS_KEY = "schedule.days"
TIME_KEY = "schedule.time"
SINCE_KEY = "schedule.since"


def _week_key(monday: date) -> str:
    return f"schedule.week.{monday.isoformat()}"


def own_days(db: Session) -> tuple[int, ...]:
    return rules.parse_days(progress.get_setting(db, DAYS_KEY, ""))


def since(db: Session) -> date | None:
    raw = progress.get_setting(db, SINCE_KEY, "")
    try:
        return date.fromisoformat(raw) if raw else None
    except ValueError:
        return None


def program_days(db: Session) -> tuple[int, ...]:
    from app.modules.workouts import programs_service

    e = programs_service.active(db)
    p = programs_service.get_program(db, e.program_key) if e is not None else None
    if p is None or not p.days:
        return ()
    return tuple(sorted({d.weekday % 7 for d in p.days}))


def read(db: Session) -> ScheduleOut:
    days = own_days(db)
    t = progress.get_setting(db, TIME_KEY, "") or None
    if days:
        return ScheduleOut(days=list(days), time=t, source="you", label=rules.days_label(days))
    prog = program_days(db)
    if prog:
        return ScheduleOut(days=list(prog), time=t, source="program", label=rules.days_label(prog))
    return ScheduleOut(days=[], time=t, source="none", label="no days")


def save(db: Session, days: list[int], time: str | None, today: date) -> ScheduleOut:
    progress.set_setting(db, DAYS_KEY, rules.format_days(days))
    progress.set_setting(db, TIME_KEY, time or "")
    if since(db) is None:
        progress.set_setting(db, SINCE_KEY, today.isoformat())
    progress.set_setting(db, "sessions_per_week", str(len(days)))
    db.commit()
    return read(db)


def week_override(db: Session, monday: date) -> tuple[int, ...] | None:
    raw = progress.get_setting(db, _week_key(monday), "\x00")
    return None if raw == "\x00" else rules.parse_days(raw)


def days_for_week(db: Session, monday: date) -> tuple[tuple[int, ...], str, bool]:
    """(weekdays, source, custom) for the week starting ``monday``."""
    over = week_override(db, monday)
    if over is not None:
        return over, "you", True
    days = own_days(db)
    if days:
        return days, "you", False
    prog = program_days(db)
    return (prog, "program", False) if prog else ((), "none", False)


def save_week(db: Session, monday: date, days: list[int]) -> None:
    progress.set_setting(db, _week_key(rules.week_start(monday)), rules.format_days(days))
    if since(db) is None:
        progress.set_setting(db, SINCE_KEY, rules.week_start(monday).isoformat())
    db.commit()


def scheduled_rest_days(db: Session, start: date, end: date) -> set[date] | None:
    """Planned rest days from the user's own schedule between ``start`` and ``end``, from the
    day it was first set; None when there is no schedule of their own."""
    first = since(db)
    if first is None:
        return None
    out: set[date] = set()
    day = max(start, first)
    weeks: dict[date, tuple[int, ...]] = {}
    while day <= end:
        monday = rules.week_start(day)
        if monday not in weeks:
            days, source, _ = days_for_week(db, monday)
            weeks[monday] = days if source == "you" else ()
        planned = weeks[monday]
        if planned and day.weekday() not in planned:
            out.add(day)
        day += timedelta(days=1)
    return out


def week_target(db: Session, today: date) -> int | None:
    days, source, _ = days_for_week(db, rules.week_start(today))
    return len(days) if source == "you" and days else None


def _upcoming(db: Session, now: datetime) -> list[str]:
    from app.modules.workouts import programs_service

    plan = programs_service.plan(db, now)
    if plan is None:
        return []
    keys = [d.key for d in plan.days]
    start = keys.index(plan.next.key) if plan.next.key in keys else 0
    return [plan.days[(start + i) % len(keys)].name for i in range(len(keys))]


def week(db: Session, now: datetime, start: date | None = None) -> WeekOut:
    from app.modules.gamification import service as game

    today = now.date()
    monday = rules.week_start(start or today)
    days, source, custom = days_for_week(db, monday)
    trained = {d for d in game.active_days(db) if monday <= d < monday + timedelta(days=7)}
    upcoming = _upcoming(db, now) if monday + timedelta(days=6) >= today else []
    view = rules.week_view(monday, days, trained, upcoming, today)
    return WeekOut(
        week_start=monday,
        days=[
            WeekDayOut(
                day=v.day,
                weekday=v.day.weekday(),
                planned=v.planned,
                done=v.done,
                session=v.session,
                today=v.today,
                past=v.past,
            )
            for v in view
        ],
        planned=sum(1 for v in view if v.planned),
        done=len(trained),
        custom=custom,
        source=source,  # type: ignore[arg-type]
    )


def short_session(db: Session, now: datetime, minutes: int = 10) -> ShortSessionOut | None:
    from app.modules.workouts import programs_service

    plan = programs_service.plan(db, now)
    if plan is None:
        return None
    items = plan.next.items
    kept, est = rules.short_session([(i.exercise, i.rest_s, i.measure) for i in items], minutes)
    if not kept:
        return None
    out = []
    for k in kept:
        it = items[k.index]
        out.append(
            ShortItemOut(
                exercise_id=it.exercise_id,
                exercise=it.exercise,
                sets=k.sets,
                rep_low=it.rep_low,
                rep_high=it.rep_high,
                rest_s=k.rest_s,
                measure=it.measure,
                section=it.section,
            )
        )
    return ShortSessionOut(
        session=plan.next.name,
        minutes=est,
        items=out,
        note=(
            f"A {est}-minute version of {plan.next.name}: the first moves at two sets each. "
            "It counts for your streak like any session; the full session stays next."
        ),
    )
