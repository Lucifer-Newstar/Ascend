"""Transactional outbox.

`record` stores an event in events_outbox inside the caller's transaction, so an event
exists exactly when the change that caused it was committed. Readers (the /events
stream, the dispatcher below) work from the table, never from memory.

Status (v1.1.0): wired but unused. No consumer is registered (app.state.outbox_consumers
is empty) and the desktop app does not subscribe to /events yet; it refreshes by request.
Kept for the planned live updates (docs/contracts/ipc-contract.md §3, events:subscribe).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.events import Event
from app.core.outbox_models import OutboxEvent, ProcessedEvent

log = logging.getLogger("ascend.outbox")

Consumer = Callable[[dict[str, Any]], None]
MAX_ATTEMPTS = 5


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


def once(session: Session, handler: str, event_id: int, now: datetime) -> bool:
    """Claim (handler, event) for processing. True the first time, False on any re-delivery,
    so a consumer that crashed after doing its work is not run twice."""
    exists = session.get(ProcessedEvent, (handler, event_id))
    if exists is not None:
        return False
    session.add(ProcessedEvent(handler=handler, event_id=event_id, processed_at=now))
    session.flush()
    return True


def backoff(attempts: int) -> timedelta:
    """5 s, 10 s, 20 s, ... capped at one hour."""
    return timedelta(seconds=min(3600, 5 * 2 ** max(0, attempts - 1)))


def dispatch_pending(
    session: Session,
    consumers: dict[str, Consumer],
    now: datetime,
    limit: int = 100,
    max_attempts: int = MAX_ATTEMPTS,
) -> dict[str, int]:
    """Deliver undispatched events to every consumer.

    A consumer that raises leaves the event pending with a backoff; after `max_attempts`
    the event is closed with its last error so one bad event cannot block the queue.
    Consumers that already handled an event (processed_events) are skipped on retry."""
    stats = {"dispatched": 0, "retrying": 0, "gave_up": 0}
    due = (
        select(OutboxEvent)
        .where(OutboxEvent.dispatched_at.is_(None))
        .where((OutboxEvent.next_attempt_at.is_(None)) | (OutboxEvent.next_attempt_at <= now))
        .order_by(OutboxEvent.id)
        .limit(limit)
    )
    for row in session.scalars(due).all():
        event = as_dict(row)
        failed: str | None = None
        for name, consumer in consumers.items():
            if session.get(ProcessedEvent, (name, row.id)) is not None:
                continue
            try:
                with session.begin_nested():
                    consumer(event)
                    once(session, name, row.id, now)
            except Exception as exc:  # consumer bugs must not stop the loop
                failed = f"{name}: {exc}"[:500]
                log.warning("outbox event %s failed in %s: %s", row.id, name, exc)
                break
        if failed is None:
            row.dispatched_at = now
            stats["dispatched"] += 1
            continue
        row.attempts += 1
        row.last_error = failed
        if row.attempts >= max_attempts:
            row.dispatched_at = now
            stats["gave_up"] += 1
        else:
            row.next_attempt_at = now + backoff(row.attempts)
            stats["retrying"] += 1
    session.flush()
    return stats


def prune(session: Session, now: datetime, keep_days: int = 30) -> int:
    """Delete dispatched events older than `keep_days` (and their processed markers)."""
    cutoff = now - timedelta(days=keep_days)
    old_ids = select(OutboxEvent.id).where(
        OutboxEvent.dispatched_at.is_not(None), OutboxEvent.created_at < cutoff
    )
    session.execute(delete(ProcessedEvent).where(ProcessedEvent.event_id.in_(old_ids)))
    result = session.execute(
        delete(OutboxEvent).where(
            OutboxEvent.dispatched_at.is_not(None), OutboxEvent.created_at < cutoff
        )
    )
    return int(getattr(result, "rowcount", 0) or 0)
