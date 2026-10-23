"""Lets the trainer chat turn "log 3x10 bench at 60" or "start fresh" into an action card."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.actions import service
from app.modules.actions.registry import ActionError
from app.modules.trainer import chat
from app.modules.trainer.schemas import ChatAction, ChatOut


def _card(db: Session, row_id: int) -> dict[str, object]:
    from app.modules.actions.api import out

    return out(db, service.get(db, row_id)).model_dump(mode="json")


def from_chat(
    db: Session, settings: Settings, now: datetime, text: str, kind: str
) -> ChatOut | None:
    try:
        if kind == "erase":
            row = service.propose(db, "erase_data", {}, "chat", text, now)
            return ChatOut(
                reply="I can wipe your logs and start you fresh. I back everything up first and "
                "keep the exercise library and food table. Check the card and type ERASE to "
                "confirm.",
                mood="warning",
                intent="erase",
                source="rules",
                proposal=_card(db, row.id),
                actions=[ChatAction(kind="proposal", target=str(row.id), label="Review")],
            )
        # "rules" is a line the intent router did not take as an action ("weight 81.4",
        # "bench 80x5"): only the shared grammar may claim it, never the model.
        hit = service.parse_text(db, settings, text, now, rules_only=kind == "rules")
        if hit is None:
            return None
        k, params, how = hit
        row = service.propose(db, k, params, "ai" if how == "ai" else "chat", text, now)
    except ActionError as e:
        if kind == "rules":
            return None  # not clearly a log line: let the help note or the coach answer
        return ChatOut(reply=str(e), mood="neutral", intent="action", source="rules")
    return ChatOut(
        reply="Here's what I'll do. Confirm and it's done; you can undo it after.",
        mood="neutral",
        intent="action",
        source="ollama" if row.source == "ai" else "rules",
        proposal=_card(db, row.id),
        actions=[ChatAction(kind="proposal", target=str(row.id), label="Review")],
    )


chat.register_action_parser(from_chat)
