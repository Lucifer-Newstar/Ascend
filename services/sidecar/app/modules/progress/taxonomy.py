"""The 19 muscle regions ASCEND tracks (plan v2, section "Taxonomy").

half_life_h and weekly targets (effective sets per week, intermediate lifter)
are ESTIMATES for a fatigue model, not physiology measurements.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Muscle:
    key: str
    label: str
    group: str
    half_life_h: float
    weekly_low: float
    weekly_high: float
    capacity_es: float  # C_m: fatigue at which readiness hits 0 (10 large, 8 small)
    map_slug: str  # region in the react-muscle-highlighter figure


MUSCLES: tuple[Muscle, ...] = (
    Muscle("upper_chest", "Upper chest", "Push", 36, 4, 10, 8, "chest"),
    Muscle("lower_chest", "Lower chest", "Push", 36, 10, 18, 10, "chest"),
    Muscle("front_delts", "Front delts", "Push", 36, 6, 16, 8, "deltoids"),
    Muscle("side_delts", "Side delts", "Shoulders", 24, 8, 16, 8, "deltoids"),
    Muscle("rear_delts", "Rear delts", "Pull", 24, 8, 14, 8, "deltoids"),
    Muscle("biceps", "Biceps", "Arms", 24, 8, 16, 8, "biceps"),
    Muscle("triceps", "Triceps", "Arms", 24, 8, 16, 8, "triceps"),
    Muscle("forearms", "Forearms", "Arms", 24, 4, 10, 8, "forearm"),
    Muscle("traps", "Trapezius", "Pull", 36, 4, 12, 10, "trapezius"),
    Muscle("lats", "Lats", "Pull", 36, 10, 18, 10, "upper-back"),
    Muscle("rhomboids", "Rhomboids / mid-back", "Pull", 36, 6, 12, 10, "upper-back"),
    Muscle("lower_back", "Lower back", "Core", 48, 3, 8, 10, "lower-back"),
    Muscle("abs", "Abs", "Core", 24, 6, 12, 8, "abs"),
    Muscle("obliques", "Obliques", "Core", 24, 4, 10, 8, "obliques"),
    Muscle("glutes", "Glutes", "Legs", 36, 6, 14, 10, "gluteal"),
    Muscle("quads", "Quads", "Legs", 48, 10, 18, 10, "quadriceps"),
    Muscle("hamstrings", "Hamstrings", "Legs", 36, 10, 16, 10, "hamstring"),
    Muscle("adductors", "Adductors", "Legs", 48, 4, 10, 8, "adductors"),
    Muscle("calves", "Calves", "Legs", 24, 8, 12, 8, "calves"),
)

MUSCLE_BY_KEY: dict[str, Muscle] = {m.key: m for m in MUSCLES}
