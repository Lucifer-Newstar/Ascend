"""Trainer endpoints: chat, the watcher's feed and the first-run state."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_now
from app.modules.trainer import chat, kb, service
from app.modules.trainer.schemas import (
    ChatIn,
    ChatOut,
    FeedOut,
    FeedReadIn,
    KbEntryOut,
    TrainerState,
    TrainerStateIn,
)

router = APIRouter(prefix="/trainer", tags=["trainer"])


@router.post("/chat", response_model=ChatOut)
def post_chat(
    body: ChatIn, request: Request, db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> ChatOut:
    """One chat turn. Rules route the message first; only an unknown question reaches the
    local model (and its reply passes the number guard)."""
    return chat.respond(db, request.app.state.settings, now, body.text)


@router.get("/feed", response_model=FeedOut)
def get_feed(db: Session = Depends(get_db), now: datetime = Depends(get_now)) -> FeedOut:
    """The watcher's messages (newest first). Reading it runs the watcher (watch-v1)."""
    return service.feed(db, now)


@router.post("/feed/read", status_code=204)
def read_feed(
    body: FeedReadIn, db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> Response:
    service.mark_read(db, body.ids, now)
    return Response(status_code=204)


@router.get("/state", response_model=TrainerState)
def get_state(db: Session = Depends(get_db)) -> TrainerState:
    """First-run state: onboarded, whether data exists, demo data, chosen trainer, tours."""
    return service.state(db)


@router.put("/state", response_model=TrainerState)
def put_state(body: TrainerStateIn, db: Session = Depends(get_db)) -> TrainerState:
    return service.update_state(db, body.onboarded, body.tour_done)


@router.get("/kb", response_model=list[KbEntryOut])
def get_kb() -> list[KbEntryOut]:
    """The trainer's help notes (questions it answers without any AI)."""
    return [KbEntryOut(id=e.id, question=e.question, section=e.section) for e in kb.ENTRIES]
