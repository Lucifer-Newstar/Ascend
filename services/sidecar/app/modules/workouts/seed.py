"""Seeded exercise library: 40 common lifts and bodyweight moves.

Muscle weights: 1.0 = primary mover, 0.5 = secondary, 0.25 = stabiliser /
minor contribution. Weights are estimates chosen to match common coaching
references and the plan v2 mapping table; tune them as the team learns.
"""

from __future__ import annotations

# (name, equipment, {muscle_key: weight})
EXERCISES: list[tuple[str, str, dict[str, float]]] = [
    # --- Chest ---
    ("Barbell Bench Press", "barbell", {"lower_chest": 1.0, "upper_chest": 0.5, "front_delts": 0.5, "triceps": 0.5}),
    ("Incline Barbell Bench Press", "barbell", {"upper_chest": 1.0, "lower_chest": 0.5, "front_delts": 0.5, "triceps": 0.5}),
    ("Dumbbell Bench Press", "dumbbell", {"lower_chest": 1.0, "upper_chest": 0.5, "front_delts": 0.5, "triceps": 0.5}),
    ("Incline Dumbbell Press", "dumbbell", {"upper_chest": 1.0, "front_delts": 0.5, "triceps": 0.5}),
    ("Cable Fly", "cable", {"lower_chest": 1.0, "upper_chest": 0.5}),
    ("Push-up", "bodyweight", {"lower_chest": 1.0, "front_delts": 0.5, "triceps": 0.5, "abs": 0.25}),
    ("Chest Dip", "bodyweight", {"lower_chest": 1.0, "triceps": 0.5, "front_delts": 0.5}),
    # --- Shoulders ---
    ("Overhead Press", "barbell", {"front_delts": 1.0, "side_delts": 0.5, "triceps": 0.5, "upper_chest": 0.25}),
    ("Seated Dumbbell Shoulder Press", "dumbbell", {"front_delts": 1.0, "side_delts": 0.5, "triceps": 0.5}),
    ("Lateral Raise", "dumbbell", {"side_delts": 1.0, "traps": 0.25}),
    ("Rear Delt Fly", "dumbbell", {"rear_delts": 1.0, "rhomboids": 0.5}),
    ("Face Pull", "cable", {"rear_delts": 1.0, "rhomboids": 0.5, "traps": 0.5}),
    # --- Back ---
    ("Pull-up", "bodyweight", {"lats": 1.0, "biceps": 0.5, "rhomboids": 0.5, "forearms": 0.25}),
    ("Chin-up", "bodyweight", {"lats": 1.0, "biceps": 1.0, "rhomboids": 0.5}),
    ("Lat Pulldown", "cable", {"lats": 1.0, "biceps": 0.5, "rhomboids": 0.5}),
    ("Barbell Row", "barbell", {"lats": 1.0, "rhomboids": 1.0, "rear_delts": 0.5, "biceps": 0.5, "lower_back": 0.25}),
    ("Seated Cable Row", "cable", {"rhomboids": 1.0, "lats": 1.0, "biceps": 0.5, "rear_delts": 0.5}),
    ("One-arm Dumbbell Row", "dumbbell", {"lats": 1.0, "rhomboids": 0.5, "biceps": 0.5}),
    ("Barbell Shrug", "barbell", {"traps": 1.0, "forearms": 0.25}),
    ("Deadlift", "barbell", {"hamstrings": 1.0, "glutes": 1.0, "lower_back": 1.0, "traps": 0.5, "forearms": 0.5, "quads": 0.5}),
    ("Back Extension", "bodyweight", {"lower_back": 1.0, "glutes": 0.5, "hamstrings": 0.5}),
    # --- Arms ---
    ("Barbell Curl", "barbell", {"biceps": 1.0, "forearms": 0.5}),
    ("Dumbbell Curl", "dumbbell", {"biceps": 1.0, "forearms": 0.5}),
    ("Hammer Curl", "dumbbell", {"biceps": 1.0, "forearms": 1.0}),
    ("Triceps Pushdown", "cable", {"triceps": 1.0}),
    ("Overhead Triceps Extension", "dumbbell", {"triceps": 1.0}),
    ("Close-grip Bench Press", "barbell", {"triceps": 1.0, "lower_chest": 0.5, "front_delts": 0.5}),
    ("Wrist Curl", "dumbbell", {"forearms": 1.0}),
    # --- Legs ---
    ("Back Squat", "barbell", {"quads": 1.0, "glutes": 1.0, "adductors": 0.5, "lower_back": 0.25}),
    ("Front Squat", "barbell", {"quads": 1.0, "glutes": 0.5, "abs": 0.25}),
    ("Leg Press", "machine", {"quads": 1.0, "glutes": 0.5, "adductors": 0.25}),
    ("Romanian Deadlift", "barbell", {"hamstrings": 1.0, "glutes": 1.0, "lower_back": 0.5}),
    ("Walking Lunge", "dumbbell", {"quads": 1.0, "glutes": 1.0, "adductors": 0.25}),
    ("Bulgarian Split Squat", "dumbbell", {"quads": 1.0, "glutes": 1.0, "adductors": 0.25}),
    ("Leg Curl", "machine", {"hamstrings": 1.0}),
    ("Leg Extension", "machine", {"quads": 1.0}),
    ("Hip Thrust", "barbell", {"glutes": 1.0, "hamstrings": 0.5}),
    ("Standing Calf Raise", "machine", {"calves": 1.0}),
    # --- Core ---
    ("Plank (60 s = 1 set)", "bodyweight", {"abs": 1.0, "obliques": 0.5}),
    ("Hanging Leg Raise", "bodyweight", {"abs": 1.0, "obliques": 0.5, "forearms": 0.25}),
    ("Russian Twist", "bodyweight", {"obliques": 1.0, "abs": 0.5}),
]
