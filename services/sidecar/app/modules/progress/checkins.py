"""Check-in use-cases. Publishes CheckinRecorded so gamification can resize
today's quest; this module never touches quests itself."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.events import CheckinRecorded, EventBus
from app.modules.progress import readiness as engine
from app.modules.progress.models import Checkin
from app.modules.progress.schemas import CheckinIn, CheckinOut


def _out(row: Checkin) -> CheckinOut:
    return CheckinOut(
        day=row.day,
        sleep=row.sleep,
        energy=row.energy,
        soreness=row.soreness,
        mood=row.mood,
        readiness=row.readiness,
        band=row.band,  # type: ignore[arg-type]
        quest_adjustment=row.quest_note or engine.ADJUSTMENT[row.band],
        algo_version=row.algo_version,
    )


# Shown instead of the band's note when training had already started: the quest is
# only resized while untouched, so promising "one set shorter" would be wrong.
QUEST_ALREADY_STARTED = (
    "Training was already under way, so today's quest stays as it is. Take it easy."
)


def record(
    db: Session, bus: EventBus, data: CheckinIn, now: datetime, *, quest_started: bool = False
) -> CheckinOut:
    """Store today's check-in and announce it. `quest_started` (from the caller, which
    may read gamification state) says whether the training quest can still be resized."""
    r = engine.readiness(data.sleep, data.energy, data.soreness, data.mood)
    row = db.scalars(select(Checkin).where(Checkin.day == now.date())).first()
    if row is None:
        row = Checkin(day=now.date(), created_at=now)
        db.add(row)
    row.sleep, row.energy, row.soreness, row.mood = (
        data.sleep,
        data.energy,
        data.soreness,
        data.mood,
    )
    row.readiness, row.band, row.algo_version = r.score, r.band, engine.FORMULA_VERSION
    row.quest_note = QUEST_ALREADY_STARTED if quest_started and r.band != "green" else None
    db.flush()
    bus.publish(db, CheckinRecorded(day=row.day, at=now, readiness=r.score, band=r.band))
    return _out(row)


def for_day(db: Session, day: date) -> CheckinOut | None:
    row = db.scalars(select(Checkin).where(Checkin.day == day)).first()
    return _out(row) if row else None


def recent(db: Session, today: date, days: int) -> list[CheckinOut]:
    since = today - timedelta(days=days - 1)
    rows = db.scalars(select(Checkin).where(Checkin.day >= since).order_by(Checkin.day)).all()
    return [_out(r) for r in rows]
