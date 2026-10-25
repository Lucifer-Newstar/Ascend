"""What the trainer knows for building your plan (planbuilder-v1).

Facts come from free chat ("I have an 8 kg dumbbell and two 5 kg", "I want to train muay
thai", "I can't eat much but I can drink") or from the optional "Build my plan" interview.
They are saved only when you confirm a card (R3), in one setting row as JSON, so nothing
here needs a migration. The profile keeps the coarse equipment checklist; the details the
checklist can't hold (dumbbell weights, a bag, a gripper, other sports) live here.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

ALGO_VERSION = "planbuilder-v1"
SETTING_KEY = "planbuilder.facts"

Goal = Literal["gain_weight", "gain_muscle", "lose_fat", "strength", "skill"]
Kit = Literal["punching_bag", "gripper", "hand_wraps", "gloves", "jump_rope"]
Sport = Literal["kickboxing", "muay_thai", "boxing", "taekwondo", "karate", "mma"]

GOAL_LABEL: dict[str, str] = {
    "gain_weight": "gain weight",
    "gain_muscle": "build muscle",
    "lose_fat": "lose fat",
    "strength": "get stronger",
    "skill": "learn a skill",
}
KIT_LABEL: dict[str, str] = {
    "punching_bag": "punching bag",
    "gripper": "hand gripper",
    "hand_wraps": "hand wraps",
    "gloves": "gloves",
    "jump_rope": "jump rope",
}
SPORT_LABEL: dict[str, str] = {
    "kickboxing": "kickboxing",
    "muay_thai": "Muay Thai",
    "boxing": "boxing",
    "taekwondo": "taekwondo",
    "karate": "karate",
    "mma": "MMA",
}


class PlanFacts(BaseModel):
    goal: Goal | None = None
    weight_kg: float | None = Field(default=None, ge=25, le=250)
    target_weight_kg: float | None = Field(default=None, ge=25, le=250)
    # The time frame asked for ("in a month"), in weeks.
    weeks: int | None = Field(default=None, ge=1, le=104)
    dumbbells_kg: list[float] = Field(default_factory=list, max_length=8)
    kit: list[Kit] = Field(default_factory=list, max_length=5)
    sports: list[Sport] = Field(default_factory=list, max_length=6)
    # How long ago the sport was trained (0 = trains now), for "start as a beginner".
    sports_years_ago: int | None = Field(default=None, ge=0, le=40)
    days_per_week: int | None = Field(default=None, ge=2, le=6)
    session_minutes: int | None = Field(default=None, ge=10, le=120)
    # "Can't eat much but can drink": liquid calories (shakes) carry the surplus.
    liquid_calories: bool | None = None

    def is_empty(self) -> bool:
        return self == PlanFacts()


def load(db: Session) -> PlanFacts:
    from app.modules.progress import service as progress

    raw = progress.get_setting(db, SETTING_KEY, "")
    if not raw:
        return PlanFacts()
    try:
        return PlanFacts.model_validate(json.loads(raw))
    except (ValueError, ValidationError):
        return PlanFacts()  # a damaged row never blocks the chat; the next save rewrites it


def save(db: Session, facts: PlanFacts) -> None:
    from app.modules.progress import service as progress

    progress.set_setting(db, SETTING_KEY, facts.model_dump_json(exclude_defaults=True))


def merge(old: PlanFacts, patch: PlanFacts) -> PlanFacts:
    """New scalar values win; lists keep what was there and add what is new (dumbbells
    are replaced, since "I have an 8 kg and two 5 kg" describes the whole set)."""
    data: dict[str, Any] = old.model_dump()
    for name, value in patch.model_dump(exclude_defaults=True).items():
        if name in ("kit", "sports"):
            data[name] = list(dict.fromkeys([*data[name], *value]))
        else:
            data[name] = value
    return PlanFacts.model_validate(data)


def _kg(x: float) -> str:
    return f"{x:g} kg"


def dumbbell_label(weights: list[float]) -> str:
    """[8, 5, 5] -> "8 kg and 2 × 5 kg"."""
    counts: dict[float, int] = {}
    for w in sorted(weights, reverse=True):
        counts[w] = counts.get(w, 0) + 1
    parts = [_kg(w) if n == 1 else f"{n} × {_kg(w)}" for w, n in counts.items()]
    return " and ".join(parts) if len(parts) <= 2 else ", ".join(parts)


def lines(f: PlanFacts) -> list[str]:
    """One plain line per fact, for the card ("Remember: ...")."""
    out: list[str] = []
    if f.goal:
        out.append(f"Your goal: {GOAL_LABEL[f.goal]}.")
    if f.target_weight_kg is not None:
        frame = f" in {f.weeks} weeks" if f.weeks else ""
        out.append(f"Target weight: {_kg(f.target_weight_kg)}{frame}.")
    if f.dumbbells_kg:
        out.append(f"Dumbbells: {dumbbell_label(f.dumbbells_kg)}.")
    if f.kit:
        out.append("Also at home: " + ", ".join(KIT_LABEL[k] for k in f.kit) + ".")
    if f.sports:
        when = ""
        if f.sports_years_ago:
            n = f.sports_years_ago
            when = f", last trained {n} year{'s' if n != 1 else ''} ago"
        elif f.sports_years_ago == 0:
            when = ", training now"
        out.append("Other training: " + ", ".join(SPORT_LABEL[s] for s in f.sports) + when + ".")
    elif f.sports_years_ago:
        out.append(f"Last trained martial arts {f.sports_years_ago} years ago.")
    if f.days_per_week:
        out.append(f"Days a week: {f.days_per_week}.")
    if f.session_minutes:
        out.append(f"Session length: about {f.session_minutes} minutes.")
    if f.liquid_calories:
        out.append("Eating: big meals are hard, drinks are easy (shakes help).")
    return out
