"""The trainer chat: rules first, the local model only for what the rules can't answer.

Routing (trainer-intents-v1) decides what a message is. App questions, tours, greetings,
"start fresh", goal checks and plan requests are answered deterministically, offline, on
any PC. "What should I train today?" gets the coach's rule tip (worded by the model when
it is on). Only an unknown question goes to the model, and its reply passes the number
guard; when it can't be used, the reply says why (fallback_reason) instead of answering
something else.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.coach import service as coach
from app.modules.planner import validate as goalcheck
from app.modules.progress import service as progress
from app.modules.trainer import kb
from app.modules.trainer.intents import Intent, classify
from app.modules.trainer.schemas import ChatAction, ChatOut

START_SUGGESTIONS = [
    "Give me a tour",
    "What should I train today?",
    "Make me a workout plan",
    "Can I lose 5 kg in 2 months?",
]

# An optional hook the actions module registers: text -> (reply, proposal) or None.
ActionParser = Callable[[Session, Settings, datetime, str, str], ChatOut | None]
_action_parser: list[ActionParser] = []


def register_action_parser(fn: ActionParser) -> None:
    _action_parser[:] = [fn]


def _name(db: Session) -> str:
    p = progress.get_profile(db)
    return p.name if p is not None and p.name else ""


def _faq(intent: Intent) -> ChatOut:
    e = intent.entry
    assert e is not None
    actions = (
        [ChatAction(kind="tour", target=e.section, label=f"Show me {kb.SECTION_TITLES[e.section]}")]
        if e.section
        else []
    )
    return ChatOut(
        reply=e.answer, mood="neutral", intent="faq", source="faq", faq_id=e.id, actions=actions
    )


def _goal(db: Session, intent: Intent) -> ChatOut:
    change = intent.numbers["change_kg"]
    weeks = intent.numbers["weeks"]
    p = progress.get_profile(db)
    if p is None:
        return ChatOut(
            reply="Tell me your weight first (we'll set up your profile), then I can check that "
            "goal properly.",
            mood="neutral",
            intent="goal_check",
            source="rules",
        )
    target = round(p.weight_kg + change, 1)
    flags = goalcheck.check_weight_goal(p.weight_kg, target, weeks, p.height_cm)
    if flags:
        worst = goalcheck.worst(flags)
        return ChatOut(
            reply=" ".join(f.message for f in flags),
            mood="warning" if worst in ("warn", "block") else "neutral",
            intent="goal_check",
            source="rules",
            actions=[ChatAction(kind="planner", target="workout", label="Plan it properly")],
        )
    rate = abs(change) / weeks
    return ChatOut(
        reply=f"{abs(change):g} kg in {weeks:g} weeks is {rate:.2f} kg a week. That is a pace "
        f"you can hold. Want the planner to build around it?",
        mood="proud",
        intent="goal_check",
        source="rules",
        actions=[ChatAction(kind="planner", target="diet", label="Build a meal plan")],
    )


def _ai_or_fallback(db: Session, settings: Settings, now: datetime, text: str) -> ChatOut:
    r = coach.answer(db, settings, now, text)
    if r.source == "ollama":
        return ChatOut(reply=r.text, mood="neutral", intent="unknown", source="ollama")
    best = [e.question for e in kb.ENTRIES if kb.score(e, text) > 0][:3] or START_SUGGESTIONS[:3]
    return ChatOut(
        reply="That one isn't in my notes. " + coach.fallback_sentence(r.fallback_reason),
        mood="neutral",
        intent="unknown",
        source="rules",
        fallback_reason=r.fallback_reason,
        suggestions=best,
    )


def respond(db: Session, settings: Settings, now: datetime, text: str) -> ChatOut:
    intent = classify(text)
    k = intent.kind
    if k == "action" and _action_parser:
        out = _action_parser[0](db, settings, now, text, k)
        if out is not None:
            return out
    if k == "erase" and _action_parser:
        out = _action_parser[0](db, settings, now, text, k)
        if out is not None:
            return out
    if k == "greeting":
        name = _name(db)
        return ChatOut(
            reply=f'Hey{", " + name if name else ""}. Ask me anything about ASCEND, say "tour" '
            f"for a walkthrough, or ask for a plan.",
            mood="hyped",
            intent=k,
            source="rules",
            suggestions=START_SUGGESTIONS,
        )
    if k == "help":
        return ChatOut(
            reply="I answer questions about the app, give a tour of any section, watch your log "
            "(PRs, missed sessions, overtraining, weigh-in trends) and tell you when a goal is "
            "unrealistic. The planner builds workout and meal plans.",
            mood="neutral",
            intent=k,
            source="rules",
            suggestions=START_SUGGESTIONS,
        )
    if k == "thanks":
        return ChatOut(
            reply="Any time. Keep logging; I'm watching.", mood="proud", intent=k, source="rules"
        )
    if k == "identity":
        return ChatOut(
            reply="I'm your trainer in ASCEND: I watch your log and guide you, and the planner "
            "does the planning. I'm software running on this PC, not a person.",
            mood="neutral",
            intent=k,
            source="rules",
        )
    if k == "erase":
        return ChatOut(
            reply="I can wipe your logs and keep the exercise library and food table. I make a "
            "backup first. Do it from Settings > Start fresh.",
            mood="warning",
            intent=k,
            source="rules",
            actions=[ChatAction(kind="navigate", target="settings", label="Open Settings")],
        )
    if k == "tour":
        target = intent.section or "app"
        label = "Start the tour" if target == "app" else f"Tour {kb.SECTION_TITLES[target]}"
        return ChatOut(
            reply="Let's go. I'll highlight each part; Next to continue, Esc to stop.",
            mood="hyped",
            intent=k,
            source="rules",
            actions=[ChatAction(kind="tour", target=target, label=label)],
        )
    if k == "navigate" and intent.section:
        title = kb.SECTION_TITLES[intent.section]
        return ChatOut(
            reply=f"Opening {title}.",
            mood="neutral",
            intent=k,
            source="rules",
            actions=[ChatAction(kind="navigate", target=intent.section, label=f"Open {title}")],
        )
    if k in ("plan_workout", "plan_diet"):
        kind = "workout" if k == "plan_workout" else "diet"
        return ChatOut(
            reply=f"The planner builds the {kind} plan from your profile; I check it against your "
            f"goal before you save it.",
            mood="hyped",
            intent=k,
            source="rules",
            actions=[ChatAction(kind="planner", target=kind, label=f"Open the {kind} planner")],
        )
    if k == "goal_check":
        return _goal(db, intent)
    if k == "change_trainer":
        return ChatOut(
            reply="Pick whoever you like. We all read the same numbers; only the voice changes.",
            mood="neutral",
            intent=k,
            source="rules",
            actions=[ChatAction(kind="trainer_picker", label="Choose a trainer")],
        )
    if k == "train_today":
        r = coach.reply(db, settings, now, None)
        return ChatOut(
            reply=r.text,
            mood="neutral",
            intent=k,
            source="ollama" if r.source == "ollama" else "rules",
            fallback_reason=r.fallback_reason,
        )
    if k == "faq":
        return _faq(intent)
    return _ai_or_fallback(db, settings, now, text)


def _route_coach_question(
    db: Session, settings: Settings, now: datetime, question: str
) -> coach.CoachReply | None:
    """The Coach page's "Ask" box goes through the same routing: an app question gets the
    trainer's answer, never the muscle tip. Training questions stay with the coach."""
    intent = classify(question)
    if intent.kind in ("unknown", "train_today"):
        return None
    # A weak help-note match ("I did 80 kg for 5 reps" mentions reps) is a training
    # question: the coach answers it. Only a clear app question is routed.
    if intent.kind == "faq" and intent.entry and kb.score(intent.entry, question) < 2:
        return None
    out = respond(db, settings, now, question)
    return coach.CoachReply("rules", out.reply, f"trainer:{out.intent}", None, None)


coach.register_router(_route_coach_question)
