"""Coach: rules always produce a tip; the local LLM may rephrase / answer questions."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.coach import ollama, runtime, validate
from app.modules.coach.rules import CoachContext, Tip, rule_tip
from app.modules.gamification import service as game
from app.modules.nutrition import service as nutrition
from app.modules.progress import service as progress
from app.modules.workouts.models import Workout, WorkoutSet

log = logging.getLogger("ascend.coach")


@dataclass(frozen=True)
class CoachReply:
    source: str  # "rules" | "ollama"
    text: str
    tip_code: str
    model: str | None
    fallback_reason: str | None
    # Validator results for a model reply ({"numbers": "pass", ...}); None on the rules path.
    checks: dict[str, str] | None = None


def build_context(db: Session, now: datetime) -> CoachContext:
    profile = progress.get_profile(db)
    energy = progress.energy_for(profile) if profile else None
    totals = nutrition.day_totals(db, now.date())
    s = game.streak(db, now.date())
    sets_today = (
        db.scalar(select(func.count(WorkoutSet.id)).join(Workout).where(Workout.day == now.date()))
        or 0
    )
    return CoachContext(
        now=now,
        has_profile=profile is not None,
        muscles=progress.muscle_states(db, now),
        kcal_eaten=totals.kcal,
        kcal_target=energy.kcal_target if energy else None,
        protein_g=totals.protein_g,
        protein_target_g=energy.protein_target_g if energy else None,
        streak=s.current,
        active_today=s.active_today,
        sets_today=int(sets_today),
    )


def facts_text(ctx: CoachContext, tip: Tip) -> str:
    lines = [
        f"Rule-based tip: {tip.text}",
        f"Calories eaten today: {round(ctx.kcal_eaten)} of an estimated {ctx.kcal_target} kcal",
        f"Protein today: {round(ctx.protein_g)} g of {ctx.protein_target_g} g",
        f"Streak: {ctx.streak} days; sets logged today: {ctx.sets_today}",
    ]
    for m in ctx.muscles:
        if m.status != "no_data":
            lines.append(
                f"{m.label}: {m.status}, {round(m.es_7d, 1):g} effective sets this week "
                f"(target {m.weekly_low:g}-{m.weekly_high:g}), "
                f"readiness {round(m.readiness * 100)}%"
            )
    return "\n".join(lines)


FALLBACK_SENTENCES: dict[str, str] = {
    "ai_disabled": "The AI is switched off in Settings, so this is a rule-based answer.",
    "ollama_unavailable": "The local AI isn't running (Settings > AI setup), so this is a "
    "rule-based answer.",
    "timeout": "The local AI took too long (it may still be loading), so this is a rule-based "
    "answer.",
    "model_error": "The local AI returned an error, so this is a rule-based answer.",
    "guard_rejected": "The AI reply didn't pass the safety check, so here's a rule-based answer.",
}


def fallback_sentence(reason: str | None) -> str:
    """What the user is told when a rule-based answer stands in for the model's."""
    return FALLBACK_SENTENCES.get(reason or "", "")


def _ask_checked(
    db: Session, settings: Settings, facts: str, question: str, user_question: str | None
) -> tuple[str | None, str | None, str, dict[str, str] | None]:
    """(text, fallback reason, model, checks). The user never sees an unchecked model reply
    (coach-llm.md section 5.2)."""
    r = runtime.ask(db, settings, facts, question)
    if r.text is None:
        return None, r.reason, r.model, None
    checks = validate.check_reply(r.text, facts, user_question)
    if not checks.ok:
        failed = "numbers" if not checks.numbers.ok else "banned"
        log.info("coach reply replaced: %s check failed (%s)", failed, checks.summary())
        return None, "guard_rejected", r.model, checks.summary()
    return r.text, None, r.model, checks.summary()


def reply(db: Session, settings: Settings, now: datetime, question: str | None) -> CoachReply:
    """Today's tip (worded by the model when it can), or an answer to `question`.

    A question that is not about today's training is routed by the trainer's rules first
    (greetings, app how-to, "start fresh", tours...), so it never gets the muscle tip as
    its answer; the tip is only the reply to "what should I train?"-type questions."""
    ctx = build_context(db, now)
    tip = rule_tip(ctx)
    if question:
        routed = _routed(db, settings, now, question)
        if routed is not None:
            return routed
    q = question or "Give me today's single most useful tip, based on the facts."
    facts = facts_text(ctx, tip)
    text, reason, model, checks = _ask_checked(db, settings, facts, q, question)
    if text is None:
        used = model if reason in ("guard_rejected", "timeout", "model_error") else None
        return CoachReply("rules", tip.text, tip.code, used, reason, checks)
    return CoachReply("ollama", text, tip.code, model, None, checks)


def _routed(db: Session, settings: Settings, now: datetime, question: str) -> CoachReply | None:
    """Hook for the trainer's intent router (registered by the trainer module)."""
    for fn in _routers:
        out = fn(db, settings, now, question)
        if out is not None:
            return out
    return None


_routers: list[Callable[[Session, Settings, datetime, str], CoachReply | None]] = []


def register_router(fn: Callable[[Session, Settings, datetime, str], CoachReply | None]) -> None:
    _routers[:] = [fn]


def answer(
    db: Session, settings: Settings, now: datetime, question: str, context: str | None = None
) -> CoachReply:
    """A free-form question for the model, with no rule tip standing in: on any failure the
    reply is empty and fallback_reason says why (the caller words the fallback). `context`
    adds knowledge-base passages to the facts, so the guard also accepts their numbers."""
    ctx = build_context(db, now)
    tip = rule_tip(ctx)
    facts = facts_text(ctx, tip)
    if context:
        facts += "\nReference passages (answer from these, do not invent numbers):\n" + context
    text, reason, model, checks = _ask_checked(db, settings, facts, question, question)
    if text is None:
        return CoachReply("rules", "", tip.code, model, reason, checks)
    return CoachReply("ollama", text, tip.code, model, None, checks)


def status(db: Session, settings: Settings) -> dict[str, object]:
    model = runtime.model_for(db, settings)
    return {
        "ai_enabled": progress.ai_enabled(db),
        "ollama_available": ollama.is_available(settings.ollama_host, model),
        "model": model,
    }
