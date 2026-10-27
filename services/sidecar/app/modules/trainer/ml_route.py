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

trainer-answers-v1 (2026-10-27): a help note that only shares a word or two with the question
("Should I stretch after exercise?" matched the after-workout food note) gives way to a
knowledge passage that covers the question clearly better (`FAQ_MARGIN`). Answers are built by
trainer/compose.py (direct answer, steps, one personal line) when the local AI is off; a
passage the retrieval is not sure about is offered as "the closest note I have" with one
clarifying question, and a question too vague to answer gets one clarifying question.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.coach import service as coach
from app.modules.ml import intent as intent_model
from app.modules.ml import knowledge
from app.modules.trainer import compose, kb
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
# A help note keeps a question unless a confident passage covers this much more of it.
FAQ_MARGIN = 0.2
SAFETY = (
    "If it hurts, stop that exercise and get it checked by a doctor or physiotherapist; I "
    "can't diagnose pain. "
)


def is_pain(text: str, label: str | None) -> bool:
    """A pain question keeps the doctor/physio line whatever answers it."""
    return label == "injury_pain" or bool(compose.PAIN.search(text))


def _weak_rules(intent: Intent, text: str) -> bool:
    if intent.kind == "unknown":
        return True
    return intent.kind == "faq" and intent.entry is not None and kb.score(intent.entry, text) < 2


def knowledge_label(text: str) -> str | None:
    """The model's label when it is a knowledge one (any confidence): it weights the sources."""
    p = intent_model.predict(text)
    return p.intent if p is not None and p.intent in KNOWLEDGE else None


def model_says_out_of_scope(text: str) -> bool:
    p = intent_model.predict(text)
    return p is not None and p.intent == "out_of_scope" and p.confidence >= intent_model.threshold()


def knowledge_answer(
    db: Session, settings: Settings, now: datetime, text: str, label: str | None
) -> ChatOut | None:
    """A cited answer from the knowledge base: worded by the local AI when it is on, else
    composed from the passage like a coach (trainer/compose.py)."""
    hits = knowledge.retrieve(text, 3, intent=label)
    if not hits or not hits[0].confident:
        return None
    used = [h for h in hits if h.confident][:2]
    cites = [ChatCitation(**knowledge.citation(h)) for h in used]
    pain = is_pain(text, label)
    prefix = SAFETY if pain else ""
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
    body = compose.compose(text, used[0], compose.personal(db), label)
    return ChatOut(
        reply=SAFETY.strip() + "\n" + body if pain else body,
        mood="warning" if pain else "neutral",
        intent=label or "knowledge",
        source="knowledge",
        citations=cites[:1],
        fallback_reason=ai.fallback_reason,
    )


_QUESTION = re.compile(
    r"\?\s*$|^\s*(how|what|why|when|which|where|who|is|are|can|could|should|do|does|did|"
    r"will|would|any|tips?)\b",
    re.I,
)


def unsure_answer(db: Session, text: str, label: str | None) -> ChatOut | None:
    """The nearest passage, labelled as the closest note, with one clarifying question,
    when retrieval found something near but not sure enough to be the answer. Only for a
    question: a statement ("I have no bench") is not offered a neighbouring note."""
    if not _QUESTION.search(text):
        return None
    hits = knowledge.retrieve(text, 1, intent=label)
    if not hits or hits[0].confident or not hits[0].close:
        return None
    reply, chips = compose.closest(text, hits[0])
    pain = is_pain(text, label)
    return ChatOut(
        reply=SAFETY.strip() + "\n" + reply if pain else reply,
        mood="warning" if pain else "neutral",
        intent=label or "knowledge",
        source="knowledge",
        citations=[ChatCitation(**knowledge.citation(hits[0]))],
        suggestions=chips,
    )


def clarify_answer(db: Session, text: str) -> ChatOut | None:
    """One clarifying question for a message that names no topic at all."""
    if not compose.vague(text):
        return None
    reply, chips = compose.clarify(text, compose.personal(db))
    return ChatOut(reply=reply, mood="neutral", intent="clarify", source="rules", suggestions=chips)


def _faq_loses(text: str, intent: Intent, label: str | None) -> bool:
    """A help note matched on a word or two while a passage answers the question itself:
    the passage covers clearly more of the question AND its title names something the
    question asks about that the note does not ("stretch" against the after-workout food
    note). A curated note that names the same thing keeps the question."""
    e = intent.entry
    if intent.kind != "faq" or e is None:
        return False
    hits = knowledge.retrieve(text, 1, intent=label)
    if not hits or not hits[0].confident:
        return False
    note_text = " ".join([e.question, *e.keys])
    if hits[0].coverage < knowledge.share(text, note_text) + FAQ_MARGIN:
        return False
    asked = set(knowledge.tokens(text)) - knowledge.GENERIC
    named = asked & set(knowledge.tokens(hits[0].title))
    return bool(named - set(knowledge.tokens(note_text)))


def route(
    db: Session,
    settings: Settings,
    now: datetime,
    text: str,
    intent: Intent,
    action_parser: ActionParser | None,
) -> ChatOut | Intent:
    """A finished reply, or the Intent the rule switch in chat.respond should answer."""
    p = intent_model.predict(text)
    if intent.kind == "faq":
        # A help note that only shares a word with the question gives way to a passage
        # that answers it (the model's top label must be a knowledge one, at any confidence).
        top = p.intent if p is not None and p.intent in KNOWLEDGE else None
        if top is not None and _faq_loses(text, intent, top):
            out = knowledge_answer(db, settings, now, text, top)
            if out is not None:
                return out
    if not _weak_rules(intent, text):
        return intent
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
