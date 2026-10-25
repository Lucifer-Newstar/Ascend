"""The unlock log (v1.4): what you have unlocked and when it first appeared.

The desktop knows the catalog (cosmetics, ranks, boss titles, skill steps) and reports what
is unlocked now; this keeps the date each one first appeared. The first report ever is
recorded quietly (seeded), so updating the app does not replay old unlocks at once.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.gamification.models import UnlockEvent
from app.modules.gamification.schemas import UnlockIn


def list_unlocks(db: Session) -> list[UnlockEvent]:
    return list(
        db.scalars(select(UnlockEvent).order_by(UnlockEvent.at.desc(), UnlockEvent.id.desc()))
    )


def sync(db: Session, now: datetime, items: list[UnlockIn]) -> tuple[list[UnlockEvent], int]:
    """Record the unlocks not seen before; return them (empty on the first sync) and the total."""
    first = (db.scalar(select(func.count(UnlockEvent.id))) or 0) == 0
    known = set(db.scalars(select(UnlockEvent.key)))
    new: list[UnlockEvent] = []
    for it in items:
        if it.key in known:
            continue
        known.add(it.key)
        row = UnlockEvent(
            key=it.key, kind=it.kind, title=it.title, detail=it.detail, at=now, seeded=first
        )
        db.add(row)
        new.append(row)
    db.commit()
    total = db.scalar(select(func.count(UnlockEvent.id))) or 0
    return ([] if first else new), total
