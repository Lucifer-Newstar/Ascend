from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Profile(Base):
    """Single-row table (id = 1): the local user's body data and goal."""

    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), default="")
    age: Mapped[int] = mapped_column(Integer)
    sex: Mapped[str] = mapped_column(String(10))
    height_cm: Mapped[float] = mapped_column(Float)
    weight_kg: Mapped[float] = mapped_column(Float)
    goal: Mapped[str] = mapped_column(String(10))
    activity: Mapped[str] = mapped_column(String(16), default="moderate")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


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
