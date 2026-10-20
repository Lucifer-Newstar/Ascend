"""Transactional outbox.

`record` stores an event in events_outbox inside the caller's transaction, so an event
exists exactly when the change that caused it was committed. Readers (the /events
stream, the dispatcher below) work from the table, never from memory.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.events import Event
from app.core.outbox_models import OutboxEvent


def record(session: Session, event: Event, now: datetime) -> OutboxEvent:
    row = OutboxEvent(
        type=event.event_name(),
        version=event.VERSION,
        payload=json.dumps(event.payload(), separators=(",", ":")),
        created_at=now.replace(microsecond=0),
        attempts=0,
    )
    session.add(row)
    session.flush()
    return row


def as_dict(row: OutboxEvent) -> dict[str, Any]:
    return {
        "id": row.id,
        "type": row.type,
        "version": row.version,
        "at": row.created_at.isoformat(),
        "payload": json.loads(row.payload),
    }


def after(session: Session, last_id: int, limit: int = 100) -> list[OutboxEvent]:
    """Events with id > last_id, oldest first."""
    stmt = select(OutboxEvent).where(OutboxEvent.id > last_id).order_by(OutboxEvent.id).limit(limit)
    return list(session.scalars(stmt).all())
