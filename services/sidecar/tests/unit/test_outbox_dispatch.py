from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core import outbox
from app.core.db import Base
from app.core.events import SetDeleted
from app.core.outbox_models import OutboxEvent, ProcessedEvent

T0 = datetime(2026, 10, 20, 8, 0, 0)


def session() -> Session:
    engine = create_engine("sqlite://")
    import app.models  # noqa: F401

    Base.metadata.create_all(engine)
    return Session(engine)


def test_once_claims_a_pair_only_once() -> None:
    s = session()
    assert outbox.once(s, "mailer", 1, T0) is True
    assert outbox.once(s, "mailer", 1, T0) is False
    assert outbox.once(s, "indexer", 1, T0) is True
    assert len(s.scalars(select(ProcessedEvent)).all()) == 2


def test_backoff_doubles_and_caps() -> None:
    assert [outbox.backoff(n).total_seconds() for n in (1, 2, 3)] == [5, 10, 20]
    assert outbox.backoff(30) == timedelta(hours=1)


def test_dispatch_delivers_and_marks_rows() -> None:
    s = session()
    for i in range(3):
        outbox.record(s, SetDeleted(set_id=i, workout_id=1, exercise_id=1), T0)
    got: list[dict[str, Any]] = []
    stats = outbox.dispatch_pending(s, {"collect": got.append}, T0)
    assert stats == {"dispatched": 3, "retrying": 0, "gave_up": 0}
    assert [e["payload"]["set_id"] for e in got] == [0, 1, 2]
    assert all(r.dispatched_at == T0 for r in s.scalars(select(OutboxEvent)))
    assert outbox.dispatch_pending(s, {"collect": got.append}, T0)["dispatched"] == 0


def test_failing_consumer_retries_with_backoff_then_gives_up() -> None:
    s = session()
    outbox.record(s, SetDeleted(set_id=1, workout_id=1, exercise_id=1), T0)
    calls = {"good": 0, "bad": 0}

    def good(_e: dict[str, Any]) -> None:
        calls["good"] += 1

    def bad(_e: dict[str, Any]) -> None:
        calls["bad"] += 1
        raise RuntimeError("disk full")

    consumers = {"good": good, "bad": bad}
    assert outbox.dispatch_pending(s, consumers, T0, max_attempts=3)["retrying"] == 1
    row = s.scalars(select(OutboxEvent)).one()
    assert row.attempts == 1 and row.next_attempt_at == T0 + timedelta(seconds=5)
    assert "disk full" in (row.last_error or "")
    # not due yet: nothing happens
    assert outbox.dispatch_pending(s, consumers, T0 + timedelta(seconds=1)) == {
        "dispatched": 0,
        "retrying": 0,
        "gave_up": 0,
    }
    outbox.dispatch_pending(s, consumers, T0 + timedelta(seconds=5), max_attempts=3)
    stats = outbox.dispatch_pending(s, consumers, T0 + timedelta(seconds=30), max_attempts=3)
    assert stats["gave_up"] == 1 and row.dispatched_at is not None
    assert calls == {"good": 1, "bad": 3}  # the consumer that succeeded ran once
