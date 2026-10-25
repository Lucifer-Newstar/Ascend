"""Everyday bodyweight moves people log by name that the imported library lacks (v1.3):
burpees, jumping jacks and the wall sit. The trainer test found "15 burpees", "30 jumping
jacks" and "wall sit 45s" had nothing to log against.

MET values are approximate, from the Compendium of Physical Activities (calisthenics,
vigorous effort 8.0; light or moderate effort 3.8); they feed the calorie ESTIMATE only.
Muscle weights use the library's scale (1.0 primary, 0.5 secondary, 0.25 minor) and are
rule-of-thumb estimates.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Move:
    name: str
    measure: str  # reps | hold
    pattern: str
    met: float
    difficulty: str
    muscles: dict[str, float]
    instructions: tuple[str, ...]
    aliases: tuple[str, ...] = field(default_factory=tuple)


_LEGS = {
    "vastus_lateralis": 1.0,
    "vastus_medialis": 1.0,
    "vastus_intermedius": 1.0,
    "rectus_femoris": 0.75,
    "gluteus_maximus": 0.5,
}

MOVES: tuple[Move, ...] = (
    Move(
        "Burpee",
        "reps",
        "squat",
        8.0,
        "beginner",
        {
            **_LEGS,
            "pec_major_sternal": 0.5,
            "triceps_lateral": 0.25,
            "deltoid_anterior": 0.25,
            "rectus_abdominis": 0.25,
        },  # fmt: skip
        (
            "Stand, then squat and put your hands on the floor.",
            "Jump or step your feet back to a push-up position.",
            "Jump or step your feet back in, then stand and jump with arms overhead.",
            "Easier: step instead of jumping and skip the push-up.",
        ),
        ("burpees", "burpy"),
    ),
    Move(
        "Jumping Jack",
        "reps",
        "other",
        7.7,
        "beginner",
        {"gastrocnemius": 0.5, "soleus": 0.25, "deltoid_lateral": 0.5, "gluteus_medius": 0.25},
        (
            "Stand tall, feet together, arms at your sides.",
            "Jump the feet apart while the arms swing out and up overhead.",
            "Jump back to the start; keep a steady rhythm and land softly.",
        ),
        ("jumping jacks", "star jumps"),
    ),
    Move(
        "Wall Sit",
        "hold",
        "isometric",
        3.8,
        "beginner",
        _LEGS,
        (
            "Lean your back flat against a wall and walk your feet forward.",
            "Slide down until your knees are about at a right angle, knees over ankles.",
            "Hold, breathing steadily; stand up if a knee hurts.",
        ),
        ("wall squat", "wall sits"),
    ),
)
