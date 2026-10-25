"""The learned intent router in front of the trainer's rules (intent-v1, ml/intent).

Policy, in order:
1. Rules that are SURE keep the message: a log line the grammar parses, "why?", erase,
   goal checks with numbers, greetings, tours, plans... (every rule kind except "faq" and
   "unknown"). Those carry numbers and safety checks the model does not.
2. When the rules found nothing ("unknown") or only a weak help-note match ("faq" with a
   keyword score under 2, the class of "safe" -> backups collisions), the model decides,
   but only at or above its confidence threshold (assets/intent-manifest.json).
3. Below the threshold, or with the model file missing, the rules' answer stands.

Knowledge intents answer from the local knowledge base with a citation; app intents reuse
the existing rule answers; out-of-scope messages keep the rules' path and never get a
knowledge-base passage.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.coach import service as coach
from app.modules.ml import intent as intent_model
from app.modules.ml import knowledge
from app.modules.trainer import kb
from app.modules.trainer.intents import Intent
from app.modules.trainer.schemas import ChatAction, ChatCitation, ChatOut

ActionParser = Callable[[Session, Settings, datetime, str, str], ChatOut | None]

KNOWLEDGE = {"exercise_howto", "training_question", "nutrition_question", "injury_pain"}
ACTIONS = {
    "log_set",
    "log_hold",
    "log_weight",
    "log_meal",
    "add_food",
    "plan_edit",
    "undo_cancel",
    "settings_change",
    "profile_change",
}
# Model label -> the rule kind whose answer already exists.
RULE_KIND = {
    "greeting": "greeting",
    "thanks": "thanks",
    "help": "help",
    "ask_workout_today": "train_today",
    "motivation": "feeling",
    "erase_data": "erase",
}
NAVIGATE = {
    "ask_progress": ("progress", "Your streak, sessions, PRs and today's food are on Progress."),
    "settings_change": ("settings", "You can change that in Settings."),
    "profile_change": ("profile", "You can update that on your Profile."),
}
SAFETY = (
    "If it hurts, stop that exercise and get it checked by a doctor or physiotherapist; I "
    "can't diagnose pain. "
)


def _weak_rules(intent: Intent, text: str) -> bool:
    if intent.kind == "unknown":
        return True
    return intent.kind == "faq" and intent.entry is not None and kb.score(intent.entry, text) < 2


def model_says_out_of_scope(text: str) -> bool:
    p = intent_model.predict(text)
    return p is not None and p.intent == "out_of_scope" and p.confidence >= intent_model.threshold()


def knowledge_answer(
    db: Session, settings: Settings, now: datetime, text: str, label: str | None
) -> ChatOut | None:
    """A cited answer from the knowledge base, worded by the local AI when it is on."""
    hits = knowledge.retrieve(text, 3, intent=label)
    if not hits or not hits[0].confident:
        return None
    used = [h for h in hits if h.confident][:2]
    cites = [ChatCitation(**knowledge.citation(h)) for h in used]
    prefix = SAFETY if label == "injury_pain" else ""
    context = "\n\n".join(f"[{h.title}] {h.text}" for h in used)
    ai = coach.answer(db, settings, now, text, context=context)
    if ai.source == "ollama" and ai.text:
        return ChatOut(
            reply=prefix + ai.text,
            mood="neutral",
            intent=label or "knowledge",
            source="ollama",
            citations=cites,
        )
    best = used[0]
    body = best.text if len(best.text) <= 600 else best.text[:600].rsplit(" ", 1)[0] + "..."
    return ChatOut(
        reply=f"{prefix}Here's what I have on that ({best.title}): {body}",
        mood="warning" if label == "injury_pain" else "neutral",
        intent=label or "knowledge",
        source="knowledge",
        citations=cites,
        fallback_reason=ai.fallback_reason,
    )


def route(
    db: Session,
    settings: Settings,
    now: datetime,
    text: str,
    intent: Intent,
    action_parser: ActionParser | None,
) -> ChatOut | Intent:
    """A finished reply, or the Intent the rule switch in chat.respond should answer."""
    if not _weak_rules(intent, text):
        return intent
    p = intent_model.predict(text)
    if p is None or p.confidence < intent_model.threshold():
        return intent
    label = p.intent
    if label in KNOWLEDGE:
        out = knowledge_answer(db, settings, now, text, label)
        return out if out is not None else intent
    if label in ACTIONS and action_parser is not None:
        out = action_parser(db, settings, now, text, "action")
        if out is not None and out.proposal is not None:
            return out
    if label in NAVIGATE:
        target, line = NAVIGATE[label]
        return ChatOut(
            reply=line,
            mood="neutral",
            intent=label,
            source="rules",
            actions=[ChatAction(kind="navigate", target=target, label=f"Open {target.title()}")],
        )
    if label in RULE_KIND:
        return Intent(RULE_KIND[label])  # type: ignore[arg-type]
    if label == "plan_request":
        return Intent("program_pick")
    # out_of_scope (and anything else) keeps the rules' path: the local AI when it is on,
    # otherwise the usual "no note on that" reply. It never reaches the knowledge base.
    return intent
