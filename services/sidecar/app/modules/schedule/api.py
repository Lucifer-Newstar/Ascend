"""Schedule API (schedule-v1): the training days and time, the week plan, short sessions."""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_now
from app.modules.schedule import service
from app.modules.schedule.schemas import (
    ScheduleIn,
    ScheduleOut,
    ShortSessionOut,
    WeekIn,
    WeekOut,
)

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.get("", response_model=ScheduleOut)
def get_schedule(db: Session = Depends(get_db)) -> ScheduleOut:
    """Your training weekdays and time (or the followed program's suggested weekdays)."""
    return service.read(db)


@router.put("", response_model=ScheduleOut)
def put_schedule(
    body: ScheduleIn, db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> ScheduleOut:
    """Pick your training weekdays and an optional time. The other weekdays become planned
    rest (neutral for the streak) from today on."""
    return service.save(db, body.days, body.time, now.date())


@router.get("/week", response_model=WeekOut)
def get_week(
    start: date | None = Query(default=None),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> WeekOut:
    """Seven days from the Monday of ``start`` (default: this week): planned vs done, and
    the coming sessions lined up on the planned days."""
    return service.week(db, now, start)


@router.put("/week", response_model=WeekOut)
def put_week(
    body: WeekIn, db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> WeekOut:
    """Plan one week (the Sunday plan-the-week screen). Past weeks cannot be changed."""
    if body.week_start < service.rules.week_start(now.date()):
        raise HTTPException(409, "That week is over; plan this week or a later one.")
    service.save_week(db, body.week_start, body.days)
    return service.week(db, now, body.week_start)


@router.get("/short-session", response_model=ShortSessionOut | None)
def get_short_session(
    minutes: int = Query(default=10, ge=5, le=30),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> ShortSessionOut | None:
    """A short version of today's session (default 10 minutes), or null with no program."""
    return service.short_session(db, now, minutes)
