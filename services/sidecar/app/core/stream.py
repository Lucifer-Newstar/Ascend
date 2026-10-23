"""GET /events: the outbox as a server-sent event stream.

Each outbox row becomes one SSE message whose `event:` is the UI-facing name from
docs/contracts/system.yaml (ServerEvent) and whose `id:` is the outbox id, so a client
that reconnects with Last-Event-ID resumes exactly where it stopped.

Status (v1.1.0): wired but unused. No consumer is registered (app.state.outbox_consumers
is empty) and the desktop app does not subscribe to /events yet; it refreshes by request.
Kept for the planned live updates (docs/contracts/ipc-contract.md §3, events:subscribe).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.core import outbox

POLL_S = 1.0
HEARTBEAT_S = 15.0

# Domain event -> UI event names. A set that is a PR also announces pr.achieved.
UI_EVENTS: dict[str, str] = {
    "SetLogged": "dashboard.changed",
    "SetUpdated": "dashboard.changed",
    "SetDeleted": "dashboard.changed",
    "WorkoutLogged": "dashboard.changed",
    "MealLogged": "dashboard.changed",
    "CheckinRecorded": "dashboard.changed",
    "QuestCompleted": "quest.completed",
    # One refresh per import; the per-set SetImported rows stay off the stream.
    "WorkoutsImported": "dashboard.changed",
}


def ui_messages(row: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    name = UI_EVENTS.get(row["type"])
    if name is None:
        return []
    data = {
        "type": row["type"],
        "version": row["version"],
        "at": row["at"],
        "payload": row["payload"],
    }
    out = [(name, data)]
    if row["type"] == "SetLogged" and row["payload"].get("is_pr"):
        out.append(("pr.achieved", data))
    return out


def format_sse(event_id: int, name: str, data: dict[str, Any]) -> str:
    return f"id: {event_id}\nevent: {name}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


def parse_last_id(value: str | None) -> int:
    try:
        return max(0, int(value)) if value else 0
    except ValueError:
        return 0


async def stream(
    factory: sessionmaker[Session],
    last_id: int,
    once: bool,
    disconnected: Callable[[], Any],
) -> AsyncIterator[str]:
    """Backlog after last_id first, then new events as they are committed.
    With once=True the stream ends after the backlog (used by tests and tooling)."""
    yield "retry: 3000\n\n"
    idle = 0.0
    while True:
        with factory() as session:
            rows = [outbox.as_dict(r) for r in outbox.after(session, last_id, limit=200)]
        for row in rows:
            last_id = row["id"]
            for name, data in ui_messages(row):
                yield format_sse(row["id"], name, data)
        if once:
            return
        if rows:
            idle = 0.0
        else:
            idle += POLL_S
            if idle >= HEARTBEAT_S:
                idle = 0.0
                yield ": keep-alive\n\n"
        if await disconnected():
            return
        await asyncio.sleep(POLL_S)
