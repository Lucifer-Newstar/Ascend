"""Rule-based daily quest generator (deterministic for a given day + state).

One training item (or mobility on a recovery day), one nutrition item, one
recovery/mind item, plus a short Recovery item if yesterday's quest was
missed. Difficulty scales x0.9 / x1.1 with the last 7 days' completion rate.
A seeded RNG keyed on the date keeps the quest stable all day.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from app.modules.progress.muscle_load import MuscleState

GENERATOR_VERSION = "quest-v1"

TRAINING_XP = 40
NUTRITION_XP = 25
RECOVERY_XP = 15
MISSED_DAY_XP = 10

MIND_ITEMS = [
    ("walk_10", "Take a 10-minute walk", "Easy pace, outdoors if you can."),
    ("water_8", "Drink 8 glasses of water", "About 2 litres across the day."),
    ("breathe_5", "5 minutes of box breathing", "4 s in, 4 s hold, 4 s out, 4 s hold."),
    ("stretch_10", "10 minutes of stretching", "Hips, hamstrings and shoulders."),
    ("sleep_23", "Lights out by 11 PM", "Recovery happens while you sleep."),
]


@dataclass(frozen=True)
class ExerciseRef:
    id: int
    name: str
    muscles: dict[str, float]


@dataclass(frozen=True)
class QuestItemSpec:
    kind: str  # training | nutrition | recovery
    code: str
    title: str
    detail: str
    metric: str  # "sets:<muscle_key>" | "meals" | "protein_g" | "manual"
    target: int
    xp: int


def difficulty_multiplier(completion_rate_7d: float | None) -> float:
    if completion_rate_7d is None:
        return 1.0
    if completion_rate_7d < 0.6:
        return 0.9
    if completion_rate_7d > 0.9:
        return 1.1
    return 1.0


def _training_item(
    states: Sequence[MuscleState], exercises: Sequence[ExerciseRef], mult: float, rng: random.Random
) -> QuestItemSpec:
    ready = [s for s in states if s.status in ("under", "no_data", "optimal")]
    # Prefer muscles furthest below their weekly band, then never-trained ones.
    ready.sort(key=lambda s: (s.status != "under", s.es_7d - s.weekly_low, s.key))
    for target in ready[:4] if ready else []:
        options = [e for e in exercises if e.muscles.get(target.key, 0) >= 1.0]
        if options:
            ex = rng.choice(sorted(options, key=lambda e: e.id))
            sets = max(2, min(5, round(3 * mult)))
            return QuestItemSpec(
                kind="training",
                code=f"train_{target.key}",
                title=f"{sets} hard sets for {target.label.lower()}",
                detail=f"Suggested: {ex.name}. Any exercise that works {target.label.lower()} counts.",
                metric=f"sets:{target.key}",
                target=sets,
                xp=TRAINING_XP,
            )
    return QuestItemSpec(
        kind="training",
        code="mobility_15",
        title="15 minutes of mobility",
        detail="Most muscles are still recovering, so today is a light day.",
        metric="manual",
        target=1,
        xp=TRAINING_XP // 2,
    )


def generate_daily_quest(
    day: date,
    states: Sequence[MuscleState],
    exercises: Sequence[ExerciseRef],
    protein_target_g: int | None,
    completion_rate_7d: float | None = None,
    missed_yesterday: bool = False,
) -> list[QuestItemSpec]:
    rng = random.Random(day.toordinal())
    mult = difficulty_multiplier(completion_rate_7d)
    items = [_training_item(states, exercises, mult, rng)]

    if protein_target_g and rng.random() < 0.5:
        items.append(
            QuestItemSpec("nutrition", "protein", f"Reach {protein_target_g} g protein",
                          "Counted from the meals you log today.", "protein_g",
                          protein_target_g, NUTRITION_XP)
        )
    else:
        meals = 3
        items.append(
            QuestItemSpec("nutrition", "log_meals", f"Log {meals} meals",
                          "Breakfast, lunch and dinner all count.", "meals", meals, NUTRITION_XP)
        )

    code, title, detail = rng.choice(MIND_ITEMS)
    items.append(QuestItemSpec("recovery", code, title, detail, "manual", 1, RECOVERY_XP))

    if missed_yesterday:
        items.append(
            QuestItemSpec("recovery", "comeback", "Comeback: 10 easy minutes",
                          "Missed yesterday? No penalty. Any light movement clears this.",
                          "manual", 1, MISSED_DAY_XP)
        )
    return items
