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
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, TypeVar

from sqlalchemy.orm import Session

log = logging.getLogger("ascend.events")


@dataclass(frozen=True)
class Event:
    """Base class. Subclasses are plain frozen dataclasses."""


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
class QuestCompleted(Event):
    quest_item_id: int
    day: date
    xp: int


E = TypeVar("E", bound=Event)
Handler = Callable[[Session, Any], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type[Event], list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type[E], handler: Callable[[Session, E], None]) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, session: Session, event: Event) -> None:
        for handler in self._handlers.get(type(event), []):
            log.debug("dispatch %s -> %s", type(event).__name__, handler.__qualname__)
            handler(session, event)

    def handler_count(self, event_type: type[Event]) -> int:
        return len(self._handlers.get(event_type, []))
