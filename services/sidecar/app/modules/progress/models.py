from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Profile(Base):
    """Single-row table (id = 1): the local user's body data and goal."""

    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), default="")
    age: Mapped[int] = mapped_column(Integer)
    sex: Mapped[str] = mapped_column(String(10))
    target_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    height_cm: Mapped[float] = mapped_column(Float)
    weight_kg: Mapped[float] = mapped_column(Float)
    goal: Mapped[str] = mapped_column(String(10))
    activity: Mapped[str] = mapped_column(String(16), default="moderate")
    # Onboarding ("Awakening"): training focus, the equipment checklist (JSON list; empty
    # means not stated, so nothing is filtered) and the baseline test (JSON object).
    focus: Mapped[str | None] = mapped_column(String(12), nullable=True)
    equipment_json: Mapped[str] = mapped_column(
        "equipment", Text, default="[]", server_default="[]"
    )
    baseline_json: Mapped[str] = mapped_column("baseline", Text, default="{}", server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    @property
    def equipment(self) -> list[str]:
        return list(json.loads(self.equipment_json or "[]"))

    @equipment.setter
    def equipment(self, value: list[str]) -> None:
        self.equipment_json = json.dumps(sorted(set(value)))

    @property
    def baseline(self) -> dict[str, Any] | None:
        data = json.loads(self.baseline_json or "{}")
        return data or None


class BodyMetric(Base):
    """A weigh-in (plus optional waist and resting heart rate)."""

    __tablename__ = "body_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    weight_kg: Mapped[float] = mapped_column(Float)
    waist_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    resting_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Measurement(Base):
    """A tape measurement at one body site."""

    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    site: Mapped[str] = mapped_column(String(16), index=True)
    cm: Mapped[float] = mapped_column(Float)


class Checkin(Base):
    """Morning readiness check-in; at most one per day (a re-submit replaces it)."""

    __tablename__ = "checkins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[date] = mapped_column(Date, unique=True)
    sleep: Mapped[int] = mapped_column(Integer)
    energy: Mapped[int] = mapped_column(Integer)
    soreness: Mapped[str] = mapped_column(String(8))
    mood: Mapped[int] = mapped_column(Integer)
    readiness: Mapped[int] = mapped_column(Integer)
    band: Mapped[str] = mapped_column(String(8))
    algo_version: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    # What this check-in did to today's quest, as shown to the user (see checkins.record).
    quest_note: Mapped[str | None] = mapped_column(String(160), nullable=True)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(256))


class MuscleLoadEvent(Base):
    """Effective-set contribution of one logged set to one muscle (written by an event handler)."""

    __tablename__ = "muscle_load_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    set_id: Mapped[int] = mapped_column(
        ForeignKey("workout_sets.id", ondelete="CASCADE"), index=True
    )
    muscle: Mapped[str] = mapped_column(String(32), index=True)
    es: Mapped[float] = mapped_column(Float)
    at: Mapped[datetime] = mapped_column(DateTime, index=True)
    formula_version: Mapped[str] = mapped_column(String(16))
