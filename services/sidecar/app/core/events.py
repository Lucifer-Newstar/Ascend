"""A tiny synchronous in-process event bus.

Modules never import each other's services directly for side effects. Instead,
the workouts module publishes `SetLogged` / `WorkoutLogged`, and gamification
and progress subscribe to them. Handlers run inline, inside the same DB
session/transaction as the request, so XP and muscle load can never drift out
of sync with the sets that caused them.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any, ClassVar, TypeVar

from sqlalchemy.orm import Session

log = logging.getLogger("ascend.events")


@dataclass(frozen=True)
class Event:
    """Base class. Subclasses are plain frozen dataclasses.

    VERSION is bumped when a subclass's fields change shape, so a stored event
    (outbox, export) can always be read back with the right schema.
    """

    VERSION: ClassVar[int] = 1

    @classmethod
    def event_name(cls) -> str:
        return cls.__name__

    def payload(self) -> dict[str, Any]:
        """JSON-ready dict: dates and datetimes as ISO strings."""
        out: dict[str, Any] = {}
        for key, value in asdict(self).items():
            out[key] = value.isoformat() if isinstance(value, date | datetime) else value
        return out


@dataclass(frozen=True)
class SetLogged(Event):
    set_id: int
    workout_id: int
    exercise_id: int
    weight_kg: float
    reps: int
    rpe: float | None
    performed_at: datetime
    is_pr: bool
    # Time-based sections (cardio, martial arts, flexibility, meditation).
    section: str = "gym"
    duration_s: int | None = None


@dataclass(frozen=True)
class SetUpdated(Event):
    """A logged set was edited. Handlers replace what they derived from the old values."""

    set_id: int
    workout_id: int
    exercise_id: int
    weight_kg: float
    reps: int
    rpe: float | None
    performed_at: datetime
    section: str = "gym"
    duration_s: int | None = None


@dataclass(frozen=True)
class SetDeleted(Event):
    set_id: int
    workout_id: int
    exercise_id: int


@dataclass(frozen=True)
class WorkoutLogged(Event):
    workout_id: int
    day: date
    hard_sets: int
    active_minutes: float


@dataclass(frozen=True)
class MealLogged(Event):
    meal_id: int
    day: date


@dataclass(frozen=True)
class CheckinRecorded(Event):
    day: date
    at: datetime
    readiness: int
    band: str


@dataclass(frozen=True)
class QuestCompleted(Event):
    quest_item_id: int
    day: date
    xp: int


E = TypeVar("E", bound=Event)
Handler = Callable[[Session, Any], None]


class EventBus:
    """Synchronous handlers run inline; with `outbox=True` every published event is also
    written to events_outbox in the same transaction, for consumers outside the request
    (the /events stream, background jobs) to read later."""

    def __init__(self, outbox: bool = False, clock: Callable[[], datetime] | None = None) -> None:
        self._handlers: dict[type[Event], list[Handler]] = defaultdict(list)
        self.outbox = outbox
        self.clock: Callable[[], datetime] = clock or datetime.now

    def subscribe(self, event_type: type[E], handler: Callable[[Session, E], None]) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, session: Session, event: Event) -> None:
        if self.outbox:
            from app.core.outbox import record

            record(session, event, self.clock())
        for handler in self._handlers.get(type(event), []):
            log.debug("dispatch %s -> %s", type(event).__name__, handler.__qualname__)
            handler(session, event)

    def handler_count(self, event_type: type[Event]) -> int:
        return len(self._handlers.get(event_type, []))
