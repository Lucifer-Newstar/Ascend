"""v1.3: short replies typed after a card act on it, and "add food ..." lines.

"yes" / "confirm" runs the newest card still waiting (never one that needs a typed word,
like ERASE), "no" / "cancel" drops it, and "undo" / "that was wrong" / "delete the last
set" takes back the newest action that can be undone. Nothing here is guessed: with no
card waiting, these words fall through to the normal chat.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.events import EventBus
from app.modules.actions import service
from app.modules.actions.models import ActionLog
from app.modules.actions.registry import SPECS, ActionError
from app.modules.trainer.schemas import ChatOut

WAITING = timedelta(minutes=30)
UNDO_WINDOW = timedelta(hours=24)

_YES = re.compile(
    r"^(yes|yep|yeah|ya|yup|y|ok do it|do it|go ahead|sure|confirm|confirmed|yes do it|"
    r"yes please|log it|save it|add it|haan|aama|aamam|seri)$"
)
_NO = re.compile(
    r"^(no|nope|nah|n|cancel|cancel it|stop|don'?t|dont|leave it|skip it|illa|"
    r"venam|vendam|nahi|mat karo|not that)$"
)
_UNDO = re.compile(
    r"^(undo|undo (it|that|last|the last one|this)|that was wrong|wrong|revert|take it back|"
    r"(delete|remove) (the |my )?(last|that) (set|meal|weigh-?in|entry|log)|"
    r"(delete|remove) (that|it))$"
)
_ADD_FOOD = re.compile(
    r"^(?:add|create|save) (?:a |my |my own |own |custom |new )?food:? (?P<name>.+?)"
    r"(?: (?P<kcal>\d+(?:\.\d+)?) ?(?:kcal|cal|calories))"
    r"(?P<rest>.*)$"
)
_N = r"(\d+(?:\.\d+)?)"


def _macro(words: str) -> re.Pattern[str]:
    """ "3g protein", "3 grams of protein" or "protein 3"."""
    return re.compile(_N + r" ?g?(?:rams?)? (?:of )?(?:" + words + r")\b|(?:" + words + r") " + _N)


_MACRO = {
    "protein_g": _macro("protein|p"),
    "carbs_g": _macro("carbs?|c"),
    "fat_g": _macro("fat|f"),
}
_SERVING = re.compile(
    r"\b(?:per|for|a|an|1) (piece|cup|katori|bowl|plate|glass|serving|slice|scoop)"
)
_GRAMS = re.compile(r"\b(\d+(?:\.\d+)?) ?g\b(?! ?(?:of )?(?:protein|carbs?|fat|p|c|f)\b)")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower()).rstrip(".!? ")


def parse_add_food(text: str) -> tuple[str, dict[str, Any], str] | None:
    """ "add food kozhukattai 120 kcal 3g protein 22g carbs 2g fat per piece" -> add_food."""
    t = _clean(text)
    if not re.match(r"^(?:add|create|save) (?:a |my |my own |own |custom |new )?food\b", t):
        return None
    m = _ADD_FOOD.match(t)
    if not m:
        raise ActionError(
            "Tell me the calories too, like: add food kozhukattai 120 kcal 3g protein 22g carbs "
            "2g fat per piece. Or use Fuel > Add your own food."
        )
    name = re.sub(r"^(?:called|named|name) ", "", m.group("name").strip(" ,:-"))
    rest = m.group("rest")
    params: dict[str, Any] = {"name": name[:1].upper() + name[1:], "kcal": float(m.group("kcal"))}
    for key, rx in _MACRO.items():
        mm = rx.search(rest)
        if mm:
            params[key] = float(mm.group(1) or mm.group(2))
    s = _SERVING.search(rest)
    if s:
        params["portion_label"] = f"1 {s.group(1)}"
    g = _GRAMS.search(rest)
    if g:
        params["portion_g"] = float(g.group(1))
    return "add_food", params, "rules"


def _latest(db: Session, now: datetime, status: str, since: timedelta) -> ActionLog | None:
    return db.scalars(
        select(ActionLog)
        .where(ActionLog.status == status, ActionLog.created_at >= now - since)
        .order_by(ActionLog.id.desc())
    ).first()


def _card(db: Session, row: ActionLog) -> dict[str, object]:
    from app.modules.actions.api import out

    return out(db, row).model_dump(mode="json")


def reply(db: Session, now: datetime, text: str, bus: object) -> ChatOut | None:
    t = _clean(text)
    if not t or len(t) > 40:
        return None
    if _YES.match(t) or _NO.match(t):
        row = _latest(db, now, "proposed", WAITING)
        if row is None:
            return None
        spec = SPECS.get(row.kind)
        if spec is None or spec.confirm_word:
            if _NO.match(t):
                service.cancel(db, row.id)
                return ChatOut(
                    reply="Cancelled. Nothing changed.",
                    mood="neutral",
                    intent="action",
                    source="rules",
                    proposal=_card(db, row),
                )
            return None  # an erase needs its word typed on the card
        if _NO.match(t):
            service.cancel(db, row.id)
            return ChatOut(
                reply="Okay, cancelled. Nothing changed.",
                mood="neutral",
                intent="action",
                source="rules",
                proposal=_card(db, row),
            )
        assert isinstance(bus, EventBus)
        done = service.confirm(db, bus, now, row.id, None)
        if done.status != "executed":
            return ChatOut(
                reply=f"That didn't go through: {done.error}",
                mood="warning",
                intent="action",
                source="rules",
                proposal=_card(db, done),
            )
        return ChatOut(
            reply="Done. Say undo if that was wrong.",
            mood="proud",
            intent="action",
            source="rules",
            proposal=_card(db, done),
        )
    if _UNDO.match(t):
        want = next(
            (
                k
                for w, k in (("set", "log_"), ("meal", "log_meal"), ("weigh", "log_weight"))
                if w in t
            ),
            None,
        )
        rows = db.scalars(
            select(ActionLog)
            .where(ActionLog.status == "executed", ActionLog.executed_at >= now - UNDO_WINDOW)
            .order_by(ActionLog.id.desc())
            .limit(20)
        ).all()
        for row in rows:
            spec = SPECS.get(row.kind)
            if spec is None or spec.undo is None or not row.undo_json:
                continue
            if want == "log_" and row.kind not in ("log_set", "log_hold"):
                continue
            if want and want != "log_" and row.kind != want:
                continue
            assert isinstance(bus, EventBus)
            try:
                service.undo(db, bus, now, row.id)
            except (service.Refused, ActionError) as e:
                return ChatOut(
                    reply=f"I can't undo that one: {e}",
                    mood="neutral",
                    intent="action",
                    source="rules",
                )
            return ChatOut(
                reply="Undone. It's back to how it was.",
                mood="neutral",
                intent="action",
                source="rules",
                proposal=_card(db, row),
            )
        return ChatOut(
            reply="There's nothing from the last day I can undo here. To fix an older entry, "
            "open Train or Fuel and edit it there.",
            mood="neutral",
            intent="action",
            source="rules",
        )
    return None
