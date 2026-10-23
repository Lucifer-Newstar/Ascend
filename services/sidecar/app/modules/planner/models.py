from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class CustomProgram(Base):
    """A workout program the user generated with the planner (and may have edited).
    Followed through plan_enrollments with program_key "custom-<id>"."""

    __tablename__ = "custom_programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    summary: Mapped[str] = mapped_column(String(400), default="")
    level: Mapped[str] = mapped_column(String(16))
    equipment: Mapped[str] = mapped_column(String(16))
    days_json: Mapped[str] = mapped_column("days", Text)
    notes_json: Mapped[str] = mapped_column("notes", Text, default="[]")
    algo_version: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    @property
    def key(self) -> str:
        return f"custom-{self.id}"

    @property
    def days(self) -> list[dict[str, Any]]:
        return list(json.loads(self.days_json))

    @property
    def notes(self) -> list[str]:
        return list(json.loads(self.notes_json or "[]"))


class DietPlan(Base):
    """A saved meal plan (dietgen-v1). At most one is active."""

    __tablename__ = "diet_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    kcal_target: Mapped[int] = mapped_column(Integer)
    protein_target_g: Mapped[int] = mapped_column(Integer)
    diet: Mapped[str] = mapped_column(String(8))
    plan_json: Mapped[str] = mapped_column("plan", Text)
    algo_version: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
