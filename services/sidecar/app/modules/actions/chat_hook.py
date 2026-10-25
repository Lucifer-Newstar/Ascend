"""Lets the trainer chat turn "log 3x10 bench at 60" or "start fresh" into an action card."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.actions import service, text_actions
from app.modules.actions.registry import ActionError, AmbiguousName, UnknownFood
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
        if kind in ("bare", "bare_exact"):  # v1.3: a line that only names a food
            bare = service.bare_food(db, text, now, exact_only=kind == "bare_exact")
            if bare is None:
                return None
            row = service.propose(db, bare[0], bare[1], "chat", text, now)
            return _proposal_reply(db, row.id, row.source)
        hit = text_actions.parse_add_food(text)
        if hit is None:
            hit = service.parse_text(db, settings, text, now, rules_only=kind == "rules")
        if hit is None:
            return None
        k, params, how = hit
        row = service.propose(db, k, params, "ai" if how == "ai" else "chat", text, now)
    except AmbiguousName as e:
        # v1.3: two different dishes fit ("biryani"): ask, with one tap per answer.
        return ChatOut(
            reply=str(e),
            mood="neutral",
            intent="action",
            source="rules",
            suggestions=[_swap_name(text, e.query, o) for o in e.options],
        )
    except UnknownFood as e:
        return ChatOut(
            reply=str(e),
            mood="neutral",
            intent="action",
            source="rules",
            actions=[ChatAction(kind="navigate", target="diet", label="Add your own food")],
        )
    except ActionError as e:
        if kind == "rules":
            return None  # not clearly a log line: let the help note or the coach answer
        return ChatOut(reply=str(e), mood="neutral", intent="action", source="rules")
    return _proposal_reply(db, row.id, row.source)


def _swap_name(text: str, query: str, option: str) -> str:
    """ "1 biryani for lunch" + "Chicken biryani" -> "1 chicken biryani for lunch"."""
    low = text.lower()
    i = low.find(query.lower())
    if i < 0:
        return option.lower()
    return (text[:i] + option.lower() + text[i + len(query) :]).strip()


def _proposal_reply(db: Session, row_id: int, source: str) -> ChatOut:
    return ChatOut(
        reply="Here's what I'll do. Confirm and it's done; you can undo it after.",
        mood="neutral",
        intent="action",
        source="ollama" if source == "ai" else "rules",
        proposal=_card(db, row_id),
        actions=[ChatAction(kind="proposal", target=str(row_id), label="Review")],
    )


def from_text_reply(db: Session, now: datetime, text: str, bus: object) -> ChatOut | None:
    """v1.3: "yes" / "no" / "undo" typed after a card act on that card."""
    return text_actions.reply(db, now, text, bus)


chat.register_action_parser(from_chat)
chat.register_text_reply(from_text_reply)
