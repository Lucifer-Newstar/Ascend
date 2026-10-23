"""personalize-v1: how the player state tunes what the app asks of you.

Deterministic and explainable: each rule reads one field of the player state and says
why. Used by the daily quest (set range, nutrition item) and exposed at
/selector/personalization so the UI and the trainer can show the same reasons. The
messages, alerts and bosses already go through the selector, which reads the same state
(level ranges, readiness, intake, under-18 gates).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.gamification.quests import Tuning
from app.modules.selector.state import PlayerState

PERSONALIZE_VERSION = "personalize-v1"

# Hard sets per quest item by experience level: fewer for a beginner (form first),
# more for someone whose weekly volume already supports it.
SETS_BY_LEVEL = {
    "beginner": (2, 3),
    "intermediate": (3, 4),
    "advanced": (3, 5),
    "expert": (3, 6),
}

CATEGORY_LABEL = {
    "push": "pushing",
    "pull": "pulling",
    "legs": "legs",
    "core": "core",
    "calisthenics": "skill work",
}


@dataclass(frozen=True)
class Personalization:
    tuning: Tuning
    focus: str | None
    tone: str  # "gentle" | "steady" | "push"
    reasons: list[str] = field(default_factory=list)
    version: str = PERSONALIZE_VERSION


def personalize(s: PlayerState) -> Personalization:
    reasons: list[str] = []
    lo, hi = SETS_BY_LEVEL.get(s.level, (2, 5))
    reasons.append(f"Quest sets {lo}-{hi} for your level ({s.level}).")
    if s.low_readiness:
        hi = max(lo, hi - 1)
        reasons.append(f"Readiness {s.readiness}/100 today, so one set fewer at most.")
    nutrition: str | None = None
    if s.meal_days_7d < 3:
        nutrition = "meals"
        reasons.append(f"Meals logged on {s.meal_days_7d} of the last 7 days: logging comes first.")
    elif s.protein_ratio is not None and s.protein_ratio < 0.8:
        nutrition = "protein"
        reasons.append(f"Protein at {round(s.protein_ratio * 100)}% of target this week.")
    focus = s.most_under()
    note = ""
    if focus is not None:
        pct = round(s.load.get(focus, 0) * 100)
        label = CATEGORY_LABEL.get(focus, focus)
        reasons.append(f"Most behind this week: {label} ({pct}% of target).")
    if s.under_18:
        reasons.append("Under 18: no eating-less items and no hard bosses on low days.")
    if s.days_since_workout is not None and s.days_since_workout >= 5:
        tone = "gentle"
        reasons.append(f"{s.days_since_workout} days since the last workout: easy comeback.")
        hi = max(lo, hi - 1)
    elif s.streak >= 7 and not s.low_readiness:
        tone = "push"
    else:
        tone = "steady"
    if s.level == "beginner":
        note = "Form first: stop each set with 2 reps in reserve."
    return Personalization(Tuning(lo, hi, nutrition, note), focus, tone, reasons)
