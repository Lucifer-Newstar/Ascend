from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class XpEvent(Base):
    """Append-only XP ledger. Total XP = SUM(amount). Rows are never edited or deleted;
    a correction (e.g. a skill step revoked because its sets were deleted) is a new row
    with a negative amount that cancels an earlier grant."""

    __tablename__ = "xp_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    at: Mapped[datetime] = mapped_column(DateTime)
    source: Mapped[str] = mapped_column(String(16))  # set | session | meal | pr | quest | skill
    ref_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amount: Mapped[int] = mapped_column(Integer)
    formula_version: Mapped[str] = mapped_column(String(16))
    note: Mapped[str] = mapped_column(String(120), default="")


class QuestItem(Base):
    __tablename__ = "quest_items"
    __table_args__ = (UniqueConstraint("day", "code", name="uq_quest_day_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    kind: Mapped[str] = mapped_column(String(12))
    code: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(120))
    detail: Mapped[str] = mapped_column(String(200))
    metric: Mapped[str] = mapped_column(String(40))
    target: Mapped[int] = mapped_column(Integer)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    xp: Mapped[int] = mapped_column(Integer)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    generator_version: Mapped[str] = mapped_column(String(16))
