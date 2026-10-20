from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import outbox, outbox_worker
from app.core.db import Base
from app.core.events import SetDeleted
from app.core.outbox_models import OutboxEvent, ProcessedEvent

T0 = datetime(2026, 10, 20, 8, 0, 0)


def factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    import app.models  # noqa: F401

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def add(f: sessionmaker[Session], at: datetime, n: int = 1) -> None:
    with f() as s:
        for i in range(n):
            outbox.record(s, SetDeleted(set_id=i, workout_id=1, exercise_id=1), at)
        s.commit()


def test_prune_removes_only_old_dispatched_events() -> None:
    f = factory()
    add(f, T0 - timedelta(days=40), 2)
    add(f, T0 - timedelta(days=1))
    with f() as s:
        outbox.dispatch_pending(s, {"c": lambda _e: None}, T0)
        outbox.record(s, SetDeleted(set_id=9, workout_id=1, exercise_id=1), T0 - timedelta(days=50))
        s.commit()  # an old but undispatched event must survive
    assert outbox_worker.prune_once(f, T0) == 2
    with f() as s:
        left = s.scalars(select(OutboxEvent)).all()
        assert len(left) == 2
        assert {p.event_id for p in s.scalars(select(ProcessedEvent))} == {3}


def test_loop_delivers_events_in_the_background() -> None:
    f = factory()
    add(f, T0, 3)
    got: list[dict[str, Any]] = []

    async def run() -> None:
        task = asyncio.create_task(
            outbox_worker.loop(f, lambda: {"c": got.append}, lambda: T0, 0.01)
        )
        for _ in range(100):
            await asyncio.sleep(0.01)
            if len(got) == 3:
                break
        task.cancel()

    asyncio.run(run())
    assert len(got) == 3
    with f() as s:
        assert all(r.dispatched_at == T0 for r in s.scalars(select(OutboxEvent)))
