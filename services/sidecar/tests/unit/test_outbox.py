from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core import outbox
from app.core.db import Base
from app.core.events import Event, EventBus, SetDeleted
from app.core.outbox_models import OutboxEvent

NOW = datetime(2026, 10, 20, 7, 30, 15, 123456)


def session() -> Session:
    engine = create_engine("sqlite://")
    import app.models  # noqa: F401  (registers every table)

    Base.metadata.create_all(engine)
    return Session(engine)


def test_publish_writes_outbox_row_with_version_and_payload() -> None:
    s = session()
    bus = EventBus(outbox=True, clock=lambda: NOW)
    seen: list[Event] = []
    bus.subscribe(SetDeleted, lambda _s, e: seen.append(e))
    bus.publish(s, SetDeleted(set_id=4, workout_id=2, exercise_id=7))
    row = s.scalars(select(OutboxEvent)).one()
    assert row.type == "SetDeleted" and row.version == 1
    assert json.loads(row.payload) == {"set_id": 4, "workout_id": 2, "exercise_id": 7}
    assert row.created_at == NOW.replace(microsecond=0)
    assert row.dispatched_at is None and row.attempts == 0
    assert len(seen) == 1  # inline handlers still run


def test_bus_without_outbox_writes_nothing() -> None:
    s = session()
    EventBus().publish(s, SetDeleted(set_id=1, workout_id=1, exercise_id=1))
    assert s.scalars(select(OutboxEvent)).all() == []


@dataclass(frozen=True)
class Renamed(Event):
    VERSION = 3
    old: str
    new: str


def test_after_returns_newer_events_in_order() -> None:
    s = session()
    for i in range(5):
        outbox.record(s, Renamed(old=str(i), new=str(i + 1)), NOW)
    rows = outbox.after(s, last_id=2, limit=2)
    assert [r.id for r in rows] == [3, 4]
    d = outbox.as_dict(rows[0])
    assert d["type"] == "Renamed" and d["version"] == 3 and d["payload"] == {"old": "2", "new": "3"}
