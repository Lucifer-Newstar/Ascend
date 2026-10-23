"""In-app actions (actions-v1): propose, confirm, cancel, undo and the audit log."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_bus, get_db, get_now
from app.core.events import EventBus
from app.core.schemas import StrictIn
from app.modules.actions import chat_hook, service  # noqa: F401  (registers the chat hook)
from app.modules.actions.models import ActionLog
from app.modules.actions.registry import SPECS, ActionError

router = APIRouter(prefix="/actions", tags=["actions"])

Kind = Literal["log_set", "log_hold", "log_weight", "log_meal", "follow_program", "erase_data"]


class ActionOut(BaseModel):
    id: int
    kind: str
    label: str
    risk: str
    params: dict[str, Any]
    summary: list[str]
    status: str
    source: str
    origin_text: str | None
    confirm_word: str | None
    undoable: bool
    auto_ok: bool
    result: dict[str, Any] | None
    error: str | None
    created_at: datetime
    executed_at: datetime | None
    undone_at: datetime | None


class ParseIn(StrictIn):
    text: str = Field(min_length=1, max_length=400)
    source: Literal["chat", "command", "trainer"] = "chat"


class ParseOut(BaseModel):
    proposal: ActionOut | None
    error: str | None = None


class ProposeIn(StrictIn):
    kind: Kind
    params: dict[str, Any] = {}
    source: Literal["chat", "command", "trainer"] = "command"
    text: str | None = Field(default=None, max_length=400)


class ConfirmIn(StrictIn):
    typed: str | None = Field(default=None, max_length=20)


class KindOut(BaseModel):
    kind: str
    label: str
    risk: str
    undoable: bool
    confirm_word: str | None
    auto_ok: bool


class AutoIn(StrictIn):
    kind: Kind
    allow: bool


def out(db: Session, row: ActionLog) -> ActionOut:
    spec = SPECS[row.kind]
    return ActionOut(
        id=row.id, kind=row.kind, label=spec.label, risk=spec.risk, params=row.params,
        summary=row.summary, status=row.status, source=row.source, origin_text=row.origin_text,
        confirm_word=spec.confirm_word,
        undoable=row.status == "executed" and spec.undo is not None and bool(row.undo_json),
        auto_ok=service.auto_allowed(db, row.kind), result=row.result, error=row.error,
        created_at=row.created_at, executed_at=row.executed_at, undone_at=row.undone_at,
    )  # fmt: skip


def _eraser(request: Request, db: Session, now: datetime) -> Callable[[bool], dict[str, Any]]:
    from app.modules.io.api import do_erase

    return lambda keep: do_erase(request, db, keep, now)


@router.get("/kinds", response_model=list[KindOut])
def kinds(db: Session = Depends(get_db)) -> list[KindOut]:
    """The allowlist: every action the app can take for you (nothing else exists)."""
    return [
        KindOut(kind=s.kind, label=s.label, risk=s.risk, undoable=s.undo is not None,
                confirm_word=s.confirm_word, auto_ok=service.auto_allowed(db, s.kind))
        for s in SPECS.values()
    ]  # fmt: skip


@router.put("/auto", response_model=list[KindOut])
def put_auto(body: AutoIn, db: Session = Depends(get_db)) -> list[KindOut]:
    """Let a low-risk action run without the confirm card ("always allow")."""
    try:
        service.set_auto(db, body.kind, body.allow)
    except service.Refused as e:
        raise HTTPException(409, str(e)) from e
    return kinds(db)


@router.post("/parse", response_model=ParseOut)
def parse(
    body: ParseIn, request: Request, db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> ParseOut:
    """Turn a sentence into a proposed action (rules first, the local model if on).
    Nothing changes until /actions/{id}/confirm."""
    hit = service.parse_text(db, request.app.state.settings, body.text, now)
    if hit is None:
        return ParseOut(proposal=None)
    kind, params, how = hit
    try:
        row = service.propose(
            db, kind, params, "ai" if how == "ai" else body.source, body.text, now
        )
    except ActionError as e:
        return ParseOut(proposal=None, error=str(e))
    return ParseOut(proposal=out(db, row))


@router.post("", response_model=ActionOut, status_code=201)
def propose(
    body: ProposeIn, db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> ActionOut:
    try:
        row = service.propose(db, body.kind, body.params, body.source, body.text, now)
    except ActionError as e:
        raise HTTPException(422, str(e)) from e
    return out(db, row)


@router.post("/{action_id}/confirm", response_model=ActionOut)
def confirm(
    action_id: int,
    body: ConfirmIn,
    request: Request,
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_bus),
    now: datetime = Depends(get_now),
) -> ActionOut:
    """Run a proposed action (destructive ones need their word typed)."""
    try:
        row = service.confirm(db, bus, now, action_id, body.typed, _eraser(request, db, now))
    except service.NotFound as e:
        raise HTTPException(404, str(e)) from e
    except service.Refused as e:
        raise HTTPException(409, str(e)) from e
    return out(db, row)


@router.post("/{action_id}/cancel", response_model=ActionOut)
def cancel(action_id: int, db: Session = Depends(get_db)) -> ActionOut:
    try:
        return out(db, service.cancel(db, action_id))
    except service.NotFound as e:
        raise HTTPException(404, str(e)) from e
    except service.Refused as e:
        raise HTTPException(409, str(e)) from e


@router.post("/{action_id}/undo", response_model=ActionOut)
def undo(
    action_id: int,
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_bus),
    now: datetime = Depends(get_now),
) -> ActionOut:
    try:
        return out(db, service.undo(db, bus, now, action_id))
    except service.NotFound as e:
        raise HTTPException(404, str(e)) from e
    except service.Refused as e:
        raise HTTPException(409, str(e)) from e


@router.get("/log", response_model=list[ActionOut])
def audit_log(db: Session = Depends(get_db)) -> list[ActionOut]:
    """The last 50 actions with their outcome (the audit log)."""
    return [out(db, r) for r in service.recent(db)]
