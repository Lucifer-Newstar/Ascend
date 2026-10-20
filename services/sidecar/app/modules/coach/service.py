"""Coach: rules always produce a tip; the local LLM may rephrase / answer questions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.coach import ollama
from app.modules.coach.rules import CoachContext, Tip, rule_tip
from app.modules.gamification import service as game
from app.modules.nutrition import service as nutrition
from app.modules.progress import service as progress
from app.modules.workouts.models import Workout, WorkoutSet


@dataclass(frozen=True)
class CoachReply:
    source: str  # "rules" | "ollama"
    text: str
    tip_code: str
    model: str | None
    fallback_reason: str | None


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
                f"{m.label}: {m.status}, {m.es_7d} effective sets this week "
                f"(target {m.weekly_low:g}-{m.weekly_high:g}), "
                f"readiness {round(m.readiness * 100)}%"
            )
    return "\n".join(lines)


def reply(db: Session, settings: Settings, now: datetime, question: str | None) -> CoachReply:
    ctx = build_context(db, now)
    tip = rule_tip(ctx)
    if not progress.ai_enabled(db):
        return CoachReply("rules", tip.text, tip.code, None, "ai_disabled")
    if not ollama.is_available(settings.ollama_host, settings.coach_model):
        return CoachReply("rules", tip.text, tip.code, None, "ollama_unavailable")
    q = question or "Give me today's single most useful tip, based on the facts."
    try:
        text = ollama.chat(
            settings.ollama_host,
            settings.coach_model,
            facts_text(ctx, tip),
            q,
            timeout=settings.coach_timeout_s,
        )
    except ollama.OllamaUnavailable as e:
        return CoachReply("rules", tip.text, tip.code, None, f"ollama_error: {e}"[:120])
    return CoachReply("ollama", text, tip.code, settings.coach_model, None)


def status(db: Session, settings: Settings) -> dict[str, object]:
    return {
        "ai_enabled": progress.ai_enabled(db),
        "ollama_available": ollama.is_available(settings.ollama_host, settings.coach_model),
        "model": settings.coach_model,
    }
