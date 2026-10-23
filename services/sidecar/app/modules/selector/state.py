"""player-state-v1: one deterministic summary of the player, recomputed from the log.

Everything the selector decides is read from this state, and every field is a plain number
or label, so the "why" behind a pick can quote it.

Experience level (from training age, weekly volume and strength relative to body weight,
loosely following common strength-standard tables; ASCEND's thresholds, not norms):
  expert:       >= 104 weeks; squat >= 2.0 x BW, bench >= 1.5 x or deadlift >= 2.5 x
  advanced:     >= 52 weeks; squat >= 1.5 x, bench >= 1.15 x, deadlift >= 1.9 x,
                or >= 60 sets a week
  intermediate: >= 12 weeks; squat >= 1.0 x, bench >= 0.8 x, deadlift >= 1.25 x,
                or >= 30 sets a week
  beginner:     everything else (or the profile's own answer when there is no log yet)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

STATE_VERSION = "player-state-v1"

Level = Literal["beginner", "intermediate", "advanced", "expert"]
LEVELS: tuple[Level, ...] = ("beginner", "intermediate", "advanced", "expert")
Category = Literal["push", "pull", "legs", "core", "cardio", "calisthenics"]
CATEGORIES: tuple[Category, ...] = ("push", "pull", "legs", "core", "cardio", "calisthenics")

# Weekly targets per category: hard sets (cardio: minutes, the WHO 150-minute guideline).
WEEKLY_TARGET: dict[str, float] = {
    "push": 10,
    "pull": 10,
    "legs": 12,
    "core": 6,
    "cardio": 150,
    "calisthenics": 6,
}

PATTERN_CATEGORY: dict[str, Category] = {
    "push": "push",
    "pull": "pull",
    "squat": "legs",
    "hinge": "legs",
    "lunge": "legs",
    "core": "core",
    "isometric": "core",
}


def level_rank(level: str) -> int:
    return LEVELS.index(level) if level in LEVELS else 0


@dataclass(frozen=True)
class StrengthRatios:
    squat: float | None = None
    bench: float | None = None
    deadlift: float | None = None


def experience_level(
    training_weeks: float,
    sets_per_week: float,
    ratios: StrengthRatios,
    self_reported: str | None = None,
    has_log: bool = True,
) -> Level:
    if not has_log:
        return self_reported if self_reported in LEVELS else "beginner"
    sq, be, dl = ratios.squat or 0, ratios.bench or 0, ratios.deadlift or 0
    if training_weeks >= 104 and (sq >= 2.0 or be >= 1.5 or dl >= 2.5):
        return "expert"
    if training_weeks >= 52 and (sq >= 1.5 or be >= 1.15 or dl >= 1.9 or sets_per_week >= 60):
        return "advanced"
    if training_weeks >= 12 and (sq >= 1.0 or be >= 0.8 or dl >= 1.25 or sets_per_week >= 30):
        return "intermediate"
    return "beginner"


@dataclass(frozen=True)
class PlayerState:
    level: Level
    game_level: int
    age: int | None
    training_weeks: float
    sets_per_week: float
    ratios: StrengthRatios
    # Category -> fraction of the weekly target done in the last 7 days (1.0 = on target).
    load: dict[str, float]
    # 0-100: today's check-in when there is one, else estimated from muscle recovery.
    readiness: int
    readiness_source: Literal["checkin", "recovery", "unknown"]
    streak: int
    days_since_workout: int | None
    sessions_14d: int
    planned_per_week: int
    # Diet adherence over the last 7 days (None without meals logged).
    kcal_ratio: float | None
    protein_ratio: float | None
    meal_days_7d: int
    goal: str | None
    # Weigh-in trend, kg per week over ~14 days (negative = losing), None if too few points.
    weight_trend_kg_week: float | None
    trend_matches_goal: bool | None
    hide_calories: bool = False
    flags: list[str] = field(default_factory=list)

    @property
    def under_18(self) -> bool:
        return self.age is not None and self.age < 18

    @property
    def low_readiness(self) -> bool:
        return self.readiness < 50

    @property
    def intake_low(self) -> bool:
        return self.kcal_ratio is not None and self.kcal_ratio < 0.85

    def most_under(self) -> str | None:
        """The trained category furthest under its weekly target (None if all >= 60%)."""
        under = sorted(
            ((v, k) for k, v in self.load.items() if k not in ("cardio",)), key=lambda t: t[0]
        )
        return under[0][1] if under and under[0][0] < 0.6 else None

    def facts(self) -> dict[str, object]:
        """The numbers a "why" may quote (percentages rounded)."""
        out: dict[str, object] = {
            "level": self.level,
            "readiness": self.readiness,
            "streak": self.streak,
            "days_since_workout": self.days_since_workout,
            "sessions_14d": self.sessions_14d,
            "planned_per_week": self.planned_per_week,
        }
        for k, v in self.load.items():
            out[f"{k}_pct"] = round(v * 100)
            out[f"{k}_under_pct"] = max(0, round((1 - v) * 100))
        if self.kcal_ratio is not None:
            out["kcal_pct"] = round(self.kcal_ratio * 100)
        if self.protein_ratio is not None:
            out["protein_pct"] = round(self.protein_ratio * 100)
        if self.weight_trend_kg_week is not None:
            out["trend_kg_week"] = round(self.weight_trend_kg_week, 2)
        return out

    def as_dict(self) -> dict[str, object]:
        d = asdict(self)
        d["under_18"] = self.under_18
        d["most_under"] = self.most_under()
        d["algo_version"] = STATE_VERSION
        return d
