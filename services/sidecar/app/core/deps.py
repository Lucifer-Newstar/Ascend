"""FastAPI dependencies shared by every module router."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import datetime

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.db import session_scope
from app.core.events import EventBus

Clock = Callable[[], datetime]


def get_db(request: Request) -> Iterator[Session]:
    yield from session_scope(request.app.state.session_factory)


def get_bus(request: Request) -> EventBus:
    bus: EventBus = request.app.state.bus
    return bus


def get_now(request: Request) -> datetime:
    """Local wall-clock time. Tests swap app.state.clock for a fixed clock."""
    clock: Clock = request.app.state.clock
    return clock().replace(microsecond=0)
