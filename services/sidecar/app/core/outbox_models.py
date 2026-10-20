"""ORM rows for the transactional outbox (see app/core/outbox.py)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, PrimaryKeyConstraint, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class OutboxEvent(Base):
    """Every published domain event, written in the same transaction as its cause."""

    __tablename__ = "events_outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer)
    payload: Mapped[str] = mapped_column(Text)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)


class ProcessedEvent(Base):
    """(handler, event) pairs already handled, so a re-delivered event is a no-op."""

    __tablename__ = "processed_events"
    __table_args__ = (PrimaryKeyConstraint("handler", "event_id"),)

    handler: Mapped[str] = mapped_column(String(128))
    event_id: Mapped[int] = mapped_column(Integer)
    processed_at: Mapped[datetime] = mapped_column(DateTime)
