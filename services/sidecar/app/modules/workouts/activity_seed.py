"""Time-based activities for the cardio, martial arts, flexibility and
meditation sections of the shared logger.

MET values are approximate, taken from the Compendium of Physical Activities
(Ainsworth et al.). They feed the calorie estimate only (kcal = MET x kg x h)
and are labelled as estimates in the UI.

Muscle weights follow the lifting library's scale (1.0 primary, 0.5
secondary, 0.25 minor). They are deliberately modest: time-based load is
converted to effective sets by `muscle_load.time_effective_sets`. Stretching
and meditation load no muscles.
"""

from __future__ import annotations

# (name, section, equipment, MET, {muscle_key: weight})
ACTIVITIES: list[tuple[str, str, str, float, dict[str, float]]] = [
    # --- Cardio ---
    (
        "Running",
        "cardio",
        "none",
        9.8,
        {"calves": 1.0, "quads": 0.5, "hamstrings": 0.5, "glutes": 0.5},
    ),
    (
        "Cycling",
        "cardio",
        "bike",
        8.0,
        {"quads": 1.0, "glutes": 0.5, "calves": 0.5, "hamstrings": 0.25},
    ),
    ("Stationary Bike", "cardio", "machine", 6.8, {"quads": 1.0, "glutes": 0.5, "calves": 0.25}),
    (
        "Rowing Machine",
        "cardio",
        "machine",
        7.0,
        {"lats": 0.5, "rhomboids": 0.5, "quads": 0.5, "hamstrings": 0.25, "biceps": 0.25},
    ),
    ("Brisk Walking", "cardio", "none", 4.3, {"calves": 0.25, "glutes": 0.25}),
    ("Jump Rope", "cardio", "rope", 11.8, {"calves": 1.0, "quads": 0.25, "forearms": 0.25}),
    (
        "Swimming (freestyle)",
        "cardio",
        "pool",
        5.8,
        {"lats": 0.5, "front_delts": 0.5, "triceps": 0.25},
    ),
    ("Stair Climbing", "cardio", "none", 8.8, {"quads": 0.5, "glutes": 0.5, "calves": 0.5}),
    # --- Martial arts ---
    (
        "Heavy Bag Rounds",
        "martial_arts",
        "bag",
        5.5,
        {"front_delts": 0.5, "obliques": 0.5, "triceps": 0.25, "abs": 0.25, "calves": 0.25},
    ),
    (
        "Shadowboxing",
        "martial_arts",
        "none",
        5.5,
        {"front_delts": 0.25, "side_delts": 0.25, "obliques": 0.25},
    ),
    (
        "Muay Thai Pad Work",
        "martial_arts",
        "pads",
        10.3,
        {"obliques": 0.5, "front_delts": 0.25, "quads": 0.25, "glutes": 0.25, "calves": 0.25},
    ),
    (
        "BJJ Rolling",
        "martial_arts",
        "mat",
        10.3,
        {"forearms": 0.5, "lats": 0.25, "abs": 0.25, "adductors": 0.25},
    ),
    (
        "Kicking Drills",
        "martial_arts",
        "none",
        10.3,
        {"quads": 0.5, "glutes": 0.5, "adductors": 0.5, "obliques": 0.25},
    ),
    ("Karate Kata", "martial_arts", "none", 5.0, {"quads": 0.25, "glutes": 0.25}),
    # --- Flexibility (holds; no muscle load) ---
    ("Standing Hamstring Stretch", "flexibility", "none", 2.3, {}),
    ("Kneeling Hip Flexor Stretch", "flexibility", "none", 2.3, {}),
    ("Pigeon Pose", "flexibility", "mat", 2.5, {}),
    ("Deep Squat Hold", "flexibility", "none", 2.5, {}),
    ("Doorway Chest Stretch", "flexibility", "none", 2.3, {}),
    ("Sun Salutation Flow", "flexibility", "mat", 2.5, {}),
    # --- Meditation ---
    ("Mindfulness Meditation", "meditation", "none", 1.0, {}),
    ("Box Breathing", "meditation", "none", 1.0, {}),
    ("Body Scan", "meditation", "none", 1.0, {}),
]

SECTIONS = ("gym", "calisthenics", "cardio", "martial_arts", "flexibility", "meditation")
TIME_BASED_SECTIONS = frozenset({"cardio", "martial_arts", "flexibility", "meditation"})
