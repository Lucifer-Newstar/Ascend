"""Tables of the intelligence layer."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
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
