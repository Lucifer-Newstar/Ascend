"""Exercise library v2: map the bundled free-exercise-db onto ASCEND's model.

free-exercise-db (https://github.com/yuhonas/free-exercise-db) is released under the
Unlicense (a public-domain dedication; checked in the repository's LICENSE.md on
2026-10-20). A trimmed copy of its exercises.json ships in `library_data/` and its
first image per exercise ships as a small webp thumbnail in apps/desktop/public/exercises.

Everything here is pure: no database, no I/O beyond reading the bundled JSON.

Muscle mapping (free-exercise-db names 17 muscles; ASCEND tracks 19 regions):
  primary muscle -> weight 1.0, secondary -> 0.5, using MUSCLE_MAP below. Where one
  source muscle covers several ASCEND regions (shoulders, chest) the exercise name picks
  the head: "lateral"/"side" -> side delts, "rear"/"reverse fly"/"face pull" -> rear
  delts, otherwise front delts with side delts at half weight; "incline" -> upper chest
  first, "decline" -> lower chest only. These weights are rule-of-thumb ESTIMATES, like
  the rest of the library (see workouts/seed.py), not EMG measurements.
Stretches load no muscles (the same rule as the hand-made flexibility list).
"""

from __future__ import annotations

import difflib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_FILE = Path(__file__).with_name("library_data") / "free_exercise_db.json"
FEDB_SOURCE = "free-exercise-db"
IMAGE_DIR = "exercises"  # relative to the renderer's index.html

MEASURES = ("reps", "hold", "time")
DIFFICULTIES = ("beginner", "intermediate", "expert")
PATTERNS = (
    "push",
    "pull",
    "squat",
    "hinge",
    "lunge",
    "core",
    "isometric",
    "carry",
    "olympic",
    "locomotion",
    "mobility",
    "other",
)
# Gallery "type" filter -> logger sections.
TYPES: dict[str, tuple[str, ...]] = {
    "strength": ("gym",),
    "calisthenics": ("calisthenics",),
    "cardio": ("cardio",),
    "mobility": ("flexibility",),
    "martial_arts": ("martial_arts",),
    "mind": ("meditation",),
}

EQUIPMENT_MAP: dict[str | None, str] = {
    "body only": "bodyweight",
    "barbell": "barbell",
    "dumbbell": "dumbbell",
    "cable": "cable",
    "machine": "machine",
    "kettlebells": "kettlebell",
    "bands": "band",
    "medicine ball": "medicine_ball",
    "exercise ball": "exercise_ball",
    "foam roll": "foam_roller",
    "e-z curl bar": "ez_bar",
    "other": "other",
    None: "none",
}

# Source muscle -> ASCEND region (shoulders and chest are resolved by name below).
MUSCLE_MAP: dict[str, dict[str, float]] = {
    "abdominals": {"abs": 1.0},
    "abductors": {"glutes": 0.5},
    "adductors": {"adductors": 1.0},
    "biceps": {"biceps": 1.0},
    "calves": {"calves": 1.0},
    "forearms": {"forearms": 1.0},
    "glutes": {"glutes": 1.0},
    "hamstrings": {"hamstrings": 1.0},
    "lats": {"lats": 1.0},
    "lower back": {"lower_back": 1.0},
    "middle back": {"rhomboids": 1.0},
    "neck": {"traps": 0.25},
    "quadriceps": {"quads": 1.0},
    "traps": {"traps": 1.0},
    "triceps": {"triceps": 1.0},
}

# free-exercise-db id -> the ASCEND exercise it duplicates. The ASCEND row keeps its
# hand-tuned muscle weights and gains the instructions, image and level.
FEDB_DUPLICATES: dict[str, str] = {
    "Barbell_Bench_Press_-_Medium_Grip": "Barbell Bench Press",
    "Barbell_Incline_Bench_Press_-_Medium_Grip": "Incline Barbell Bench Press",
    "Dumbbell_Bench_Press": "Dumbbell Bench Press",
    "Incline_Dumbbell_Press": "Incline Dumbbell Press",
    "Cable_Crossover": "Cable Fly",
    "Pushups": "Push-up",
    "Dips_-_Chest_Version": "Chest Dip",
    "Parallel_Bar_Dip": "Chest Dip",
    "Standing_Military_Press": "Overhead Press",
    "Seated_Dumbbell_Press": "Seated Dumbbell Shoulder Press",
    "Side_Lateral_Raise": "Lateral Raise",
    "Reverse_Flyes": "Rear Delt Fly",
    "Face_Pull": "Face Pull",
    "Pullups": "Pull-up",
    "Chin-Up": "Chin-up",
    "Wide-Grip_Lat_Pulldown": "Lat Pulldown",
    "Bent_Over_Barbell_Row": "Barbell Row",
    "Seated_Cable_Rows": "Seated Cable Row",
    "One-Arm_Dumbbell_Row": "One-arm Dumbbell Row",
    "Barbell_Shrug": "Barbell Shrug",
    "Barbell_Deadlift": "Deadlift",
    "Hyperextensions_Back_Extensions": "Back Extension",
    "Barbell_Curl": "Barbell Curl",
    "Dumbbell_Bicep_Curl": "Dumbbell Curl",
    "Hammer_Curls": "Hammer Curl",
    "Triceps_Pushdown": "Triceps Pushdown",
    "Standing_Dumbbell_Triceps_Extension": "Overhead Triceps Extension",
    "Close-Grip_Barbell_Bench_Press": "Close-grip Bench Press",
    "Seated_Dumbbell_Palms-Up_Wrist_Curl": "Wrist Curl",
    "Barbell_Full_Squat": "Back Squat",
    "Front_Barbell_Squat": "Front Squat",
    "Leg_Press": "Leg Press",
    "Romanian_Deadlift": "Romanian Deadlift",
    "Lying_Leg_Curls": "Leg Curl",
    "Leg_Extensions": "Leg Extension",
    "Barbell_Hip_Thrust": "Hip Thrust",
    "Standing_Calf_Raises": "Standing Calf Raise",
    "Plank": "Plank",
    "Hanging_Leg_Raise": "Hanging Leg Raise",
    "Russian_Twist": "Russian Twist",
    "Running_Treadmill": "Running",
    "Bicycling": "Cycling",
    "Bicycling_Stationary": "Stationary Bike",
    "Rowing_Stationary": "Rowing Machine",
    "Rope_Jumping": "Jump Rope",
    "Stairmaster": "Stair Climbing",
    "Walking_Treadmill": "Brisk Walking",
    "Kneeling_Hip_Flexor": "Kneeling Hip Flexor Stretch",
    "Hamstring_Stretch": "Standing Hamstring Stretch",
    # calisthenics progressions defined in calisthenics_seed.py
    "Scapular_Pull-Up": "Scapular Pull-up",
    "Muscle_Up": "Muscle-up",
    "Single-Arm_Push-Up": "One-arm Push-up",
    "Handstand_Push-Ups": "Wall Handstand Push-up",
    "Ring_Dips": "Ring Dip",
    "Incline_Push-Up": "Incline Push-up",
    "Push-Ups_-_Close_Triceps_Position": "Diamond Push-up",
    "Bodyweight_Squat": "Bodyweight Squat",
    "Inverted_Row": "Inverted Row",
    "Side_Bridge": "Side Plank",
    "Single_Leg_Glute_Bridge": "Single-leg Glute Bridge",
    "Natural_Glute_Ham_Raise": "Nordic Curl",
    "Flat_Bench_Lying_Leg_Raise": "Lying Leg Raise",
}


# MET for the free-exercise-db cardio entries that are not merged into an ASCEND
# activity. Approximate values from the Compendium of Physical Activities (Ainsworth et
# al., 2011), the same source as activity_seed.py; they feed the calorie ESTIMATE only.
FEDB_MET: dict[str, float] = {
    "Elliptical_Trainer": 5.0,
    "Jogging_Treadmill": 7.0,
    "Recumbent_Bike": 6.8,
    "Skating": 7.0,
    "Step_Mill": 9.0,
    "Trail_Running_Walking": 9.0,
}
# free-exercise-db ids whose category we override (a sled sprint is logged as sets).
FEDB_SECTION_OVERRIDE: dict[str, str] = {"Prowler_Sprint": "gym"}


def slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


_PLURAL_ES = re.compile(r"(?<=[a-z]{2})(ch|sh|x)es\b")
_PLURAL = re.compile(r"(?<=[a-z]{3})(?<!s)s\b")


def normalize(name: str) -> str:
    """Comparison key: lower case, no punctuation, no plurals, sorted words.

    "Pull-Ups", "pullup" and "Pull up" all become "pull up"; word order is ignored so
    "Curl Barbell" == "Barbell Curl"."""
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    text = re.sub(r"\(.*?\)", " ", text)
    text = text.replace("pullup", "pull up").replace("pushup", "push up")
    text = text.replace("chinup", "chin up").replace("situp", "sit up")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\bups\b", "up", text)
    text = _PLURAL_ES.sub(r"\1", text)
    text = _PLURAL.sub("", text)
    return " ".join(sorted(text.split()))


@dataclass
class LibraryEntry:
    """One exercise as the library proposes it, before it reaches the database."""

    name: str
    slug: str
    section: str
    equipment: str
    measure: str
    difficulty: str | None
    pattern: str
    mechanic: str | None
    muscles: dict[str, float]
    instructions: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    image: str | None = None
    met: float | None = None
    source: str = FEDB_SOURCE
    source_id: str | None = None
    rep_low: int | None = None
    rep_high: int | None = None


def map_muscles(name: str, primary: list[str], secondary: list[str]) -> dict[str, float]:
    lower = name.lower()
    out: dict[str, float] = {}

    def put(region: str, weight: float) -> None:
        out[region] = max(out.get(region, 0.0), weight)

    for muscles, scale in ((primary, 1.0), (secondary, 0.5)):
        for m in muscles:
            if m == "shoulders":
                if re.search(r"lateral|side raise|\bside\b|upright", lower):
                    put("side_delts", scale)
                elif re.search(r"rear|reverse fl|face pull|bent.over.*raise", lower):
                    put("rear_delts", scale)
                else:
                    put("front_delts", scale)
                    put("side_delts", scale * 0.5)
            elif m == "chest":
                if "incline" in lower:
                    put("upper_chest", scale)
                    put("lower_chest", scale * 0.5)
                elif "decline" in lower:
                    put("lower_chest", scale)
                else:
                    put("lower_chest", scale)
                    put("upper_chest", scale * 0.5)
            else:
                for region, w in MUSCLE_MAP.get(m, {}).items():
                    put(region, w * scale)
    return out


def map_section(category: str | None, equipment: str | None) -> str:
    if category == "stretching":
        return "flexibility"
    if category == "cardio":
        return "cardio"
    if equipment == "body only" and category in ("strength", "plyometrics"):
        return "calisthenics"
    return "gym"


def map_pattern(name: str, category: str | None, force: str | None, primary: list[str]) -> str:
    lower = name.lower()
    if category == "stretching":
        return "mobility"
    if category == "cardio":
        return "locomotion"
    if re.search(r"\bclean|snatch|jerk", lower):
        return "olympic"
    if re.search(r"carry|farmer|yoke|walk", lower) and category == "strongman":
        return "carry"
    if re.search(r"lunge|split squat|step.?up", lower):
        return "lunge"
    if "squat" in lower or "leg press" in lower:
        return "squat"
    if re.search(r"deadlift|good morning|hip thrust|swing|glute|bridge|pull.?through", lower):
        return "hinge"
    if primary and primary[0] in ("abdominals",):
        return "core"
    if force == "static":
        return "isometric"
    if force == "push":
        return "push"
    if force == "pull":
        return "pull"
    return "other"


def map_measure(section: str, force: str | None, name: str) -> str:
    if section in ("cardio", "martial_arts", "flexibility", "meditation"):
        return "time"
    if force == "static" or re.search(r"\bhold\b|\bplank\b|\bhang\b", name.lower()):
        return "hold"
    return "reps"


def default_range(measure: str) -> tuple[int | None, int | None]:
    """Default target range: reps per set, or seconds per hold. Starting points only."""
    if measure == "reps":
        return 6, 12
    if measure == "hold":
        return 10, 30
    return None, None


@lru_cache(maxsize=1)
def load_fedb() -> dict[str, Any]:
    with DATA_FILE.open(encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)
    return data


def fedb_entry(raw: dict[str, Any]) -> LibraryEntry:
    name = str(raw["name"]).strip()
    source_id = str(raw["id"])
    section = FEDB_SECTION_OVERRIDE.get(source_id) or map_section(
        raw.get("category"), raw.get("equipment")
    )
    measure = map_measure(section, raw.get("force"), name)
    muscles = (
        {}
        if section == "flexibility"
        else map_muscles(name, list(raw.get("primary") or []), list(raw.get("secondary") or []))
    )
    low, high = default_range(measure)
    level = raw.get("level")
    return LibraryEntry(
        name=name,
        slug=slugify(str(raw["id"])),
        section=section,
        equipment=EQUIPMENT_MAP.get(raw.get("equipment"), "other"),
        measure=measure,
        difficulty=level if level in DIFFICULTIES else None,
        pattern=map_pattern(
            name, raw.get("category"), raw.get("force"), list(raw.get("primary") or [])
        ),
        mechanic=raw.get("mechanic"),
        muscles=muscles,
        instructions=list(raw.get("instructions") or []),
        aliases=[],
        image=f"{IMAGE_DIR}/{raw['image']}" if raw.get("image") else None,
        met=FEDB_MET.get(source_id) if section == "cardio" else None,
        source=FEDB_SOURCE,
        source_id=source_id,
        rep_low=low,
        rep_high=high,
    )


def fedb_entries() -> list[LibraryEntry]:
    return [fedb_entry(raw) for raw in load_fedb()["exercises"]]


# --- search and fuzzy matching ---------------------------------------------------------


def matches_query(query: str, name: str, aliases: list[str]) -> bool:
    """Search-box match: every word of the query starts a word of the name or an alias,
    after normalising ("pullups" finds "Pull-up", "db row" does not guess)."""
    q_words = normalize(query).split()
    if not q_words:
        return True
    raw = query.strip().lower()
    for text in (name, *aliases):
        if raw in text.lower():
            return True
        words = normalize(text).split()
        if all(any(w.startswith(q) for w in words) for q in q_words):
            return True
    return False


@dataclass(frozen=True)
class Match:
    exercise_id: int
    name: str
    score: float  # 0..1
    via: str  # "exact" | "alias" | "fuzzy"


def best_matches(
    query: str,
    candidates: list[tuple[int, str, list[str]]],
    limit: int = 5,
    cutoff: float = 0.6,
) -> list[Match]:
    """Rank library exercises against a typed name.

    candidates: (id, name, aliases). Exact or alias matches on the normalised key score 1.0;
    otherwise difflib's ratio on the normalised strings, kept when >= cutoff."""
    key = normalize(query)
    if not key:
        return []
    found: dict[int, Match] = {}
    for ex_id, name, aliases in candidates:
        if normalize(name) == key:
            found[ex_id] = Match(ex_id, name, 1.0, "exact")
            continue
        if any(normalize(a) == key for a in aliases):
            found[ex_id] = Match(ex_id, name, 1.0, "alias")
            continue
        best = max(
            [difflib.SequenceMatcher(None, key, normalize(n)).ratio() for n in [name, *aliases]]
        )
        if best >= cutoff:
            found[ex_id] = Match(ex_id, name, round(best, 3), "fuzzy")
    return sorted(found.values(), key=lambda m: (-m.score, m.name))[:limit]
