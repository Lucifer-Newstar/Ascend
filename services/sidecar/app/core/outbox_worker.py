"""Background loop that drains the outbox while the sidecar runs.

Started from the app lifespan: every `interval` seconds it delivers due events to the
registered consumers (app.state.outbox_consumers) and once an hour prunes old rows.
Each pass uses its own session and commits, so a slow consumer never holds a request.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime

from sqlalchemy.orm import Session, sessionmaker

from app.core import outbox

log = logging.getLogger("ascend.outbox")

PRUNE_EVERY_S = 3600.0


def run_once(
    factory: sessionmaker[Session], consumers: dict[str, outbox.Consumer], now: datetime
) -> dict[str, int]:
    with factory() as session:
        stats = outbox.dispatch_pending(session, consumers, now)
        session.commit()
    return stats


def prune_once(factory: sessionmaker[Session], now: datetime) -> int:
    with factory() as session:
        n = outbox.prune(session, now)
        session.commit()
    if n:
        log.info("pruned %d dispatched outbox events", n)
    return n


async def loop(
    factory: sessionmaker[Session],
    consumers: Callable[[], dict[str, outbox.Consumer]],
    clock: Callable[[], datetime],
    interval: float,
) -> None:
    since_prune = PRUNE_EVERY_S  # prune on the first pass
    while True:
        try:
            if since_prune >= PRUNE_EVERY_S:
                await asyncio.to_thread(prune_once, factory, clock())
                since_prune = 0.0
            await asyncio.to_thread(run_once, factory, consumers(), clock())
        except Exception:  # keep the loop alive; the next pass retries
            log.exception("outbox pass failed")
        await asyncio.sleep(interval)
        since_prune += interval
