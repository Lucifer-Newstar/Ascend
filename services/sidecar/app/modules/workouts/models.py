from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    equipment: Mapped[str] = mapped_column(String(20))
    # gym | calisthenics | cardio | martial_arts | flexibility | meditation
    section: Mapped[str] = mapped_column(
        String(16), default="gym", server_default="gym", index=True
    )
    # Metabolic equivalent for time-based activities (None for lifts: see energy.py).
    met: Mapped[float | None] = mapped_column(Float, nullable=True)
    # --- library v2 (migration 0010) ---
    slug: Mapped[str | None] = mapped_column(String(80), unique=True, nullable=True)
    # reps | hold (seconds per set, isometric) | time (cardio, stretching, meditation)
    measure: Mapped[str] = mapped_column(String(8), default="reps", server_default="reps")
    difficulty: Mapped[str | None] = mapped_column(String(12), nullable=True)
    pattern: Mapped[str] = mapped_column(String(16), default="other", server_default="other")
    mechanic: Mapped[str | None] = mapped_column(String(12), nullable=True)
    instructions_json: Mapped[str] = mapped_column(
        "instructions", Text, default="[]", server_default="[]"
    )
    aliases_json: Mapped[str] = mapped_column("aliases", Text, default="[]", server_default="[]")
    image: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # ascend | free-exercise-db | custom
    source: Mapped[str] = mapped_column(String(24), default="ascend", server_default="ascend")
    source_ref: Mapped[str | None] = mapped_column(String(80), nullable=True)
    field_sources_json: Mapped[str] = mapped_column(
        "field_sources", Text, default="{}", server_default="{}"
    )
    rep_low: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rep_high: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    attribution_json: Mapped[str] = mapped_column(
        "attribution", Text, default="[]", server_default="[]"
    )
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    muscles: Mapped[list[ExerciseMuscle]] = relationship(
        back_populates="exercise", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def instructions(self) -> list[str]:
        return list(json.loads(self.instructions_json or "[]"))

    @property
    def aliases(self) -> list[str]:
        return list(json.loads(self.aliases_json or "[]"))

    @property
    def field_sources(self) -> dict[str, str]:
        return dict(json.loads(self.field_sources_json or "{}"))

    @property
    def attribution(self) -> list[dict[str, Any]]:
        return list(json.loads(self.attribution_json or "[]"))


class ExerciseMuscle(Base):
    __tablename__ = "exercise_muscles"

    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"), primary_key=True
    )
    muscle: Mapped[str] = mapped_column(String(32), primary_key=True)
    weight: Mapped[float] = mapped_column(Float)
    exercise: Mapped[Exercise] = relationship(back_populates="muscles")


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    section: Mapped[str] = mapped_column(String(16), default="gym", server_default="gym")
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(String(500), default="")
    # "app" for sessions logged in ASCEND; "strong" / "hevy" for imported history.
    source: Mapped[str] = mapped_column(String(16), default="app", server_default="app")
    # Stable key of an imported workout, so importing the same file twice adds nothing.
    import_key: Mapped[str | None] = mapped_column(
        String(160), nullable=True, unique=True, index=True
    )
    sets: Mapped[list[WorkoutSet]] = relationship(
        back_populates="workout",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="WorkoutSet.id",
    )


class WorkoutSet(Base):
    __tablename__ = "workout_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workout_id: Mapped[int] = mapped_column(
        ForeignKey("workouts.id", ondelete="CASCADE"), index=True
    )
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), index=True)
    weight_kg: Mapped[float] = mapped_column(Float)
    reps: Mapped[int] = mapped_column(Integer)
    rpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Time/distance sets (cardio, martial arts rounds, stretch holds, meditation).
    duration_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    e1rm: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_pr: Mapped[bool] = mapped_column(Boolean, default=False)
    performed_at: Mapped[datetime] = mapped_column(DateTime)
    workout: Mapped[Workout] = relationship(back_populates="sets")
    exercise: Mapped[Exercise] = relationship(lazy="joined")
