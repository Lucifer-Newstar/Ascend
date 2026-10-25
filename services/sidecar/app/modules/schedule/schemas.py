"""Schedule API shapes (schedule-v1)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.schemas import StrictIn
from app.modules.schedule import rules


class ScheduleOut(BaseModel):
    # Weekdays 0 = Monday ... 6 = Sunday.
    days: list[int]
    time: str | None
    # "you" = picked in Settings, "program" = the followed program's suggested weekdays,
    # "none" = no schedule and no program yet.
    source: Literal["you", "program", "none"]
    label: str
    algo_version: str = rules.ALGO_VERSION


class ScheduleIn(StrictIn):
    days: list[int] = Field(min_length=1, max_length=7)
    # "HH:MM" local time, or null for no set time.
    time: str | None = None

    @field_validator("days")
    @classmethod
    def _days(cls, v: list[int]) -> list[int]:
        if any(d < 0 or d > 6 for d in v):
            raise ValueError("weekdays are 0 (Monday) to 6 (Sunday)")
        return sorted(set(v))

    @field_validator("time")
    @classmethod
    def _time(cls, v: str | None) -> str | None:
        if v in (None, ""):
            return None
        if not rules.valid_time(v):
            raise ValueError("time is HH:MM, for example 18:30")
        return v


class WeekDayOut(BaseModel):
    day: date
    weekday: int
    planned: bool
    done: bool
    session: str | None
    today: bool
    past: bool


class WeekOut(BaseModel):
    week_start: date
    days: list[WeekDayOut]
    planned: int
    done: int
    # True when this week's days were picked on the plan-the-week screen.
    custom: bool
    source: Literal["you", "program", "none"]
    algo_version: str = rules.ALGO_VERSION


class WeekIn(StrictIn):
    week_start: date
    days: list[int] = Field(max_length=7)

    @field_validator("days")
    @classmethod
    def _days(cls, v: list[int]) -> list[int]:
        if any(d < 0 or d > 6 for d in v):
            raise ValueError("weekdays are 0 (Monday) to 6 (Sunday)")
        return sorted(set(v))


class ShortItemOut(BaseModel):
    exercise_id: int | None
    exercise: str
    sets: int
    rep_low: int
    rep_high: int
    rest_s: int
    measure: str = "reps"
    section: str | None = None


class ShortSessionOut(BaseModel):
    session: str
    minutes: int
    items: list[ShortItemOut]
    note: str
    algo_version: str = rules.ALGO_VERSION
