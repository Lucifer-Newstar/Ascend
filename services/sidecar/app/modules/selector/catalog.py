"""content-catalog-v1: everything the trainer may say on its own, as data with rules.

Each item lists the conditions that make it relevant (each with the sentence that explains
it), the experience levels and readiness range it is for, a cooldown and a priority. Two
safety tags are enforced by the engine, never by the item: `hard` items (a demanding
session) are not eligible when readiness is low, and `deficit` items (eating less) are not
eligible when intake is already low or the user is under 18.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from app.modules.selector.state import Level, PlayerState

CATALOG_VERSION = "content-catalog-v1"

Kind = Literal["message", "alert", "quest", "tip", "tour"]
Mood = Literal["neutral", "proud", "warning", "hyped"]


@dataclass(frozen=True)
class Cond:
    id: str
    test: Callable[[PlayerState], bool]
    why: str  # formatted with PlayerState.facts()


@dataclass(frozen=True)
class Item:
    id: str
    kind: Kind
    text: str
    conds: tuple[Cond, ...] = ()
    min_level: Level = "beginner"
    max_level: Level = "expert"
    readiness: tuple[int, int] = (0, 100)
    category: str | None = None
    hard: bool = False
    deficit: bool = False
    cooldown_days: int = 3
    priority: int = 50
    mood: Mood = "neutral"
    action: tuple[str, str] | None = None  # (kind, target) for the UI


def _under(cat: str) -> Cond:
    return Cond(
        f"{cat}_under",
        lambda s: s.load.get(cat, 1.0) < 0.6 and s.sessions_14d >= 2,
        f"your {cat} volume is {{{cat}_under_pct}}% under this week's target",
    )


LEGS_UNDER = _under("legs")
PUSH_UNDER = _under("push")
PULL_UNDER = _under("pull")
CORE_UNDER = _under("core")
CARDIO_UNDER = Cond(
    "cardio_under",
    lambda s: s.load.get("cardio", 1.0) < 0.5 and s.sessions_14d >= 2,
    "you have done {cardio_pct}% of 150 cardio minutes this week",
)
NO_CALISTHENICS = Cond(
    "no_calisthenics",
    lambda s: s.load.get("calisthenics", 0.0) == 0 and s.sessions_14d >= 2,
    "you train regularly but haven't logged any calisthenics",
)
READY_HIGH = Cond("ready_high", lambda s: s.readiness >= 75, "your readiness is {readiness}")
READY_LOW = Cond("ready_low", lambda s: s.readiness < 50, "your readiness is {readiness}")
NEW_USER = Cond(
    "new_user", lambda s: s.training_weeks < 3, "you are in your first weeks of training"
)
STREAK = Cond("streak", lambda s: s.streak >= 3, "you are on a {streak}-day streak")
PROTEIN_LOW = Cond(
    "protein_low",
    lambda s: s.protein_ratio is not None and s.protein_ratio < 0.8 and s.meal_days_7d >= 3,
    "your protein averaged {protein_pct}% of target over the last 7 days",
)
KCAL_LOW = Cond(
    "kcal_low",
    lambda s: s.intake_low and s.meal_days_7d >= 3,
    "your intake averaged {kcal_pct}% of your calorie target",
)
OVER_ON_CUT = Cond(
    "over_on_cut",
    lambda s: s.goal == "cut" and s.kcal_ratio is not None and s.kcal_ratio > 1.15,
    "on a cut, your intake averaged {kcal_pct}% of target",
)
NOT_LOGGING_FOOD = Cond(
    "not_logging_food",
    lambda s: s.meal_days_7d <= 1 and s.sessions_14d > 0,
    "you logged meals on at most one of the last 7 days",
)
TREND_OFF = Cond(
    "trend_off",
    lambda s: s.trend_matches_goal is False,
    "your weight is moving {trend_kg_week} kg a week, against your goal",
)
BELOW_PLAN = Cond(
    "below_plan",
    lambda s: s.sessions_14d < s.planned_per_week and s.training_weeks >= 2,
    "you trained {sessions_14d} times in 14 days against {planned_per_week} planned a week",
)


ITEMS: tuple[Item, ...] = (
    # --- safety first ---
    Item("rest_low_readiness", "alert",
         "Readiness is {readiness} today. Keep it light: technique, a walk or mobility. "
         "The hard session can wait a day.",
         (READY_LOW,), priority=95, cooldown_days=1, mood="warning",
         action=("navigate", "workout")),
    # --- training balance ---
    Item("legs_under", "tip", "Legs are at {legs_pct}% of this week's target. Add a squat or "
         "lunge session before Sunday.", (LEGS_UNDER,), category="legs", priority=70,
         action=("navigate", "workout")),
    Item("push_under", "tip", "Pushing is at {push_pct}% of the week's target. Bench, "
         "push-ups or dips will close it.", (PUSH_UNDER,), category="push", priority=65,
         action=("navigate", "workout")),
    Item("pull_under", "tip", "Pulling is at {pull_pct}% of the week's target. Rows or "
         "pull-ups keep your shoulders balanced.", (PULL_UNDER,), category="pull", priority=68,
         action=("navigate", "workout")),
    Item("core_under", "tip", "Core is at {core_pct}% of the week's target. Two plank or "
         "dead-bug sets at the end of a session is enough.", (CORE_UNDER,), category="core",
         priority=55),
    Item("cardio_walk", "quest", "Cardio is at {cardio_pct}% of 150 minutes this week. A "
         "20-minute brisk walk today counts.", (CARDIO_UNDER,), category="cardio",
         priority=50, cooldown_days=4),
    Item("top_set_day", "message", "Readiness {readiness}: a good day to push your top set. "
         "Warm up well and go for the target.", (READY_HIGH,), min_level="intermediate",
         hard=True, priority=45, cooldown_days=5, mood="hyped",
         action=("navigate", "workout")),
    Item("hard_boss_push", "message", "You're fresh (readiness {readiness}). Hit the boss "
         "with a full session today.", (READY_HIGH,), min_level="advanced", hard=True,
         priority=40, cooldown_days=7, mood="hyped", action=("navigate", "dashboard")),
    Item("plan_deloads", "tip", "At your level progress comes in blocks: plan a lighter week "
         "every 4-6 weeks, not only when you feel beaten up.", min_level="advanced",
         priority=20, cooldown_days=28),
    Item("expert_peaking", "tip", "Try a 3-week peak before testing a max: fewer sets, "
         "heavier singles, extra rest.", min_level="expert", hard=True, priority=15,
         cooldown_days=42),
    Item("form_first", "tip", "First weeks: choose weights you could lift for two more reps "
         "and learn the movement. The numbers follow.", (NEW_USER,), max_level="beginner",
         priority=60, cooldown_days=7),
    Item("below_plan", "message", "You trained {sessions_14d} times in 14 days. Even a "
         "20-minute session counts; want me to open today's plan?", (BELOW_PLAN,),
         priority=62, cooldown_days=5, action=("navigate", "workout")),
    Item("streak_keep", "message", "Day {streak}. Keep the chain going: any session or "
         "logged meal counts today.", (STREAK,), priority=30, cooldown_days=4, mood="proud"),
    # --- nutrition ---
    Item("protein_nudge", "tip", "Protein averaged {protein_pct}% of target this week. Add "
         "dal, paneer, curd, eggs or chicken to one meal a day.", (PROTEIN_LOW,),
         priority=66, cooldown_days=4, action=("navigate", "diet")),
    Item("eat_enough", "alert", "You're eating about {kcal_pct}% of your calorie target. "
         "Training needs fuel; add a snack or a bigger lunch.", (KCAL_LOW,), priority=80,
         cooldown_days=3, mood="warning", action=("navigate", "diet")),
    Item("trim_portions", "tip", "On your cut, intake averaged {kcal_pct}% of target. A "
         "smaller rice or roti portion at dinner closes most of the gap.", (OVER_ON_CUT,),
         deficit=True, priority=58, cooldown_days=5, action=("navigate", "diet")),
    Item("log_meals", "tip", "Log a meal or two today. Your calorie target adapts to what "
         "you really eat.", (NOT_LOGGING_FOOD,), priority=45, cooldown_days=5,
         action=("navigate", "diet")),
    Item("trend_check", "message", "Your weight is moving {trend_kg_week} kg a week, "
         "against your goal. Let's look at Fuel together.", (TREND_OFF,), priority=64,
         cooldown_days=7, mood="warning", action=("navigate", "diet")),
    # --- discovery ---
    Item("try_skills", "tour", "You train regularly. Want a tour of the skill trees? "
         "Calisthenics skills unlock from sets you already log.", (NO_CALISTHENICS,),
         priority=25, cooldown_days=14, action=("tour", "skills")),
)  # fmt: skip

ITEM_BY_ID: dict[str, Item] = {i.id: i for i in ITEMS}
