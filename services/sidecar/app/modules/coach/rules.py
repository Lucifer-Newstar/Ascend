"""Rule-based coach tips: the always-available fallback when AI is off or absent.

Rules are checked in priority order and the first match wins, so the same
state always produces the same tip (deterministic, testable).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from app.modules.progress.muscle_load import MuscleState

RULES_VERSION = "coach-rules-v1"


@dataclass(frozen=True)
class CoachContext:
    now: datetime
    has_profile: bool
    muscles: Sequence[MuscleState]
    kcal_eaten: float
    kcal_target: int | None
    protein_g: float
    protein_target_g: int | None
    streak: int
    active_today: bool
    sets_today: int


@dataclass(frozen=True)
class Tip:
    code: str
    text: str


def _names(states: Sequence[MuscleState], limit: int = 3) -> str:
    labels = [s.label.lower() for s in states[:limit]]
    return labels[0] if len(labels) == 1 else ", ".join(labels[:-1]) + " and " + labels[-1]


def rule_tip(ctx: CoachContext) -> Tip:
    if not ctx.has_profile:
        return Tip(
            "onboard", "Finish your profile first so calorie and protein targets can be estimated."
        )

    over = [m for m in ctx.muscles if m.status == "over"]
    if over:
        return Tip(
            "over",
            f"Your {_names(over)} volume is above the weekly range. "
            "Train something else today and let it come back down.",
        )

    recovering = sorted(
        (m for m in ctx.muscles if m.status == "recovering"), key=lambda m: m.readiness
    )
    under = sorted(
        (m for m in ctx.muscles if m.status == "under"), key=lambda m: m.es_7d - m.weekly_low
    )

    if ctx.sets_today == 0 and under:
        extra = (
            f" {_names(recovering, 2).capitalize()} still recovering, so skip those."
            if recovering
            else ""
        )
        return Tip(
            "under",
            f"{_names(under).capitalize()} are below this week's target. "
            f"A few hard sets there today would help.{extra}",
        )

    if ctx.protein_target_g and ctx.now.hour >= 17 and ctx.protein_g < 0.6 * ctx.protein_target_g:
        gap = round(ctx.protein_target_g - ctx.protein_g)
        return Tip(
            "protein",
            f"You're about {gap} g short on protein today. "
            "Curd, eggs, paneer or a dal katori would close most of it.",
        )

    if ctx.kcal_target and ctx.kcal_eaten > ctx.kcal_target * 1.15:
        return Tip(
            "kcal_high",
            "You're over today's calorie estimate. No stress: one day doesn't "
            "change a trend. Keep dinner light if you're still hungry.",
        )

    if ctx.streak >= 3 and not ctx.active_today and ctx.now.hour >= 18:
        return Tip(
            "streak",
            f"Your {ctx.streak}-day streak is still open for today. "
            "Even the recovery quest item keeps it alive.",
        )

    if recovering and ctx.sets_today == 0:
        return Tip(
            "recovering",
            f"{_names(recovering, 2).capitalize()} need more time. "
            "Pick a different muscle group or do mobility today.",
        )

    if ctx.sets_today > 0:
        return Tip(
            "good_session",
            "Nice work today. Get protein in and sleep well; that's when the gains land.",
        )

    return Tip("default", "Log a workout or a meal and I'll tailor tips to your data.")
