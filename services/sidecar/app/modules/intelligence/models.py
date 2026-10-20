"""Tables of the intelligence layer."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class RecoveryParam(Base):
    """The personal recovery factor of one muscle group (personal.py), refitted after each
    finished session. Absent row = population value (k = 1)."""

    __tablename__ = "recovery_params"

    group: Mapped[str] = mapped_column("muscle_group", String(16), primary_key=True)
    k: Mapped[float] = mapped_column(Float)
    k_low: Mapped[float] = mapped_column(Float)
    k_high: Mapped[float] = mapped_column(Float)
    k_hat: Mapped[float | None] = mapped_column(Float, nullable=True)
    alpha: Mapped[float | None] = mapped_column(Float, nullable=True)
    n: Mapped[int] = mapped_column(Integer)
    personal: Mapped[bool] = mapped_column(Boolean, default=False)
    algo_version: Mapped[str] = mapped_column(String(16))
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class ProgressionDecision(Base):
    """What the user did with a prog-v1 target: "accepted" it or chose "kept" (keep my own
    numbers, which stops new targets for that exercise for 7 days)."""

    __tablename__ = "progression_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"), index=True
    )
    decided_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    choice: Mapped[str] = mapped_column(String(10))
    reason: Mapped[str] = mapped_column(String(24))
    target_json: Mapped[str] = mapped_column(Text, default="{}")
    algo_version: Mapped[str] = mapped_column(String(16))
