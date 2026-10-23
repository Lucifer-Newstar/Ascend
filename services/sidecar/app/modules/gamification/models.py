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


class BossRaid(Base):
    """One weekly boss raid (boss-v1, ADR-0022). Damage is never stored: it is counted from
    the week's logged sets, so editing or deleting a set changes it like everything else."""

    __tablename__ = "boss_raids"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    week_start: Mapped[date] = mapped_column(Date, unique=True)
    name: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(40))
    hp: Mapped[int] = mapped_column(Integer)
    hp_source: Mapped[str] = mapped_column(String(16))
    hp_note: Mapped[str] = mapped_column(String(160))
    algo_version: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    defeated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    xp_awarded: Mapped[int] = mapped_column(Integer, default=0)
    # boss-v2: the tier the raid was spawned at (a seasonal boss follows your level);
    # None on raids from before v1.2 (their tier comes from the boss's name).
    tier: Mapped[str | None] = mapped_column(String(1), nullable=True)


class StreakReason(Base):
    """v1.2: why a day was missed. A reason given by the end of the next day keeps the
    streak (see streaks.py); the words stay on your machine like everything else."""

    __tablename__ = "streak_reasons"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    reason: Mapped[str] = mapped_column(String(120))
    given_on: Mapped[date] = mapped_column(Date)
    given_at: Mapped[datetime] = mapped_column(DateTime)
