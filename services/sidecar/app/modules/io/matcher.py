"""Map exercise names from other apps onto the ASCEND library.

Strong and Hevy name exercises "Movement (Equipment)", e.g. "Bench Press (Barbell)",
while ASCEND uses "Barbell Bench Press". Matching runs in three steps and stops at
the first hit:

1. an explicit alias (names that differ in more than word order or spelling);
2. "Equipment Movement" built from the parenthesis, compared after normalising
   case, hyphens and plurals ("Pull Up" == "Pull-up", "Curls" == "Curl");
3. a close fuzzy match (difflib ratio >= 0.88) on the normalised names.

Anything else is reported as unmatched; its sets are skipped rather than guessed.
"""

from __future__ import annotations

import difflib
import re
from collections.abc import Iterable

# Normalised source name -> exact ASCEND library name.
ALIASES: dict[str, str] = {
    "bench press barbell": "Barbell Bench Press",
    "incline bench press barbell": "Incline Barbell Bench Press",
    "bench press dumbbell": "Dumbbell Bench Press",
    "incline bench press dumbbell": "Incline Dumbbell Press",
    "chest fly cable": "Cable Fly",
    "cable crossover": "Cable Fly",
    "push up": "Push-up",
    "chest dip": "Chest Dip",
    "triceps dip": "Chest Dip",
    "overhead press barbell": "Overhead Press",
    "strict military press barbell": "Overhead Press",
    "shoulder press dumbbell": "Seated Dumbbell Shoulder Press",
    "seated overhead press dumbbell": "Seated Dumbbell Shoulder Press",
    "lateral raise dumbbell": "Lateral Raise",
    "reverse fly dumbbell": "Rear Delt Fly",
    "rear delt reverse fly dumbbell": "Rear Delt Fly",
    "face pull cable": "Face Pull",
    "pull up": "Pull-up",
    "chin up": "Chin-up",
    "lat pulldown cable": "Lat Pulldown",
    "bent over row barbell": "Barbell Row",
    "seated row cable": "Seated Cable Row",
    "seated cable row v grip cable": "Seated Cable Row",
    "bent over one arm row dumbbell": "One-arm Dumbbell Row",
    "dumbbell row": "One-arm Dumbbell Row",
    "shrug barbell": "Barbell Shrug",
    "deadlift barbell": "Deadlift",
    "back extension": "Back Extension",
    "back extension hyperextension": "Back Extension",
    "bicep curl barbell": "Barbell Curl",
    "bicep curl dumbbell": "Dumbbell Curl",
    "hammer curl dumbbell": "Hammer Curl",
    "triceps pushdown cable straight bar": "Triceps Pushdown",
    "triceps pushdown cable rope": "Triceps Pushdown",
    "triceps pushdown": "Triceps Pushdown",
    "triceps extension dumbbell": "Overhead Triceps Extension",
    "overhead triceps extension cable": "Overhead Triceps Extension",
    "bench press close grip barbell": "Close-grip Bench Press",
    "wrist curl barbell": "Wrist Curl",
    "squat barbell": "Back Squat",
    "full squat": "Back Squat",
    "front squat barbell": "Front Squat",
    "leg press": "Leg Press",
    "leg press machine": "Leg Press",
    "romanian deadlift barbell": "Romanian Deadlift",
    "romanian deadlift dumbbell": "Romanian Deadlift",
    "lunge dumbbell": "Walking Lunge",
    "walking lunge dumbbell": "Walking Lunge",
    "bulgarian split squat": "Bulgarian Split Squat",
    "lying leg curl machine": "Leg Curl",
    "seated leg curl machine": "Leg Curl",
    "leg extension machine": "Leg Extension",
    "hip thrust barbell": "Hip Thrust",
    "standing calf raise machine": "Standing Calf Raise",
    "calf raise standing": "Standing Calf Raise",
    "plank": "Plank",
    "hanging leg raise": "Hanging Leg Raise",
    "russian twist": "Russian Twist",
    "running": "Running",
    "treadmill": "Running",
    "outdoor run": "Running",
    "cycling": "Cycling",
    "bike": "Stationary Bike",
    "stationary bike": "Stationary Bike",
    "rowing machine": "Rowing Machine",
    "rowing": "Rowing Machine",
    "walking": "Brisk Walking",
    "jump rope": "Jump Rope",
    "skipping": "Jump Rope",
    "swimming": "Swimming (freestyle)",
    "stair machine": "Stair Climbing",
    "stair climber": "Stair Climbing",
}

FUZZY_CUTOFF = 0.88


def normalise(name: str) -> str:
    """Lower-case, punctuation to spaces, simple plurals dropped: "Pull-Ups" -> "pull up"."""
    words = re.sub(r"[^a-z0-9]+", " ", name.lower()).split()
    out = []
    for w in words:
        if len(w) >= 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.append(w)
    return " ".join(out)


# Keys go through the same normaliser as the source names ("triceps" -> "tricep").
_ALIASES_NORM = {normalise(k): v for k, v in ALIASES.items()}


def _equipment_first(name: str) -> str | None:
    """'Bench Press (Barbell)' -> 'Barbell Bench Press'."""
    m = re.fullmatch(r"\s*(.+?)\s*\(([^)]+)\)\s*", name)
    if not m:
        return None
    movement, equipment = m.groups()
    return f"{equipment} {movement}"


class ExerciseMatcher:
    """Built once per import from the library names; caches every lookup."""

    def __init__(self, library: Iterable[str]) -> None:
        self._by_norm: dict[str, str] = {}
        for name in library:
            self._by_norm.setdefault(normalise(name), name)
        self._cache: dict[str, str | None] = {}

    def match(self, source: str) -> str | None:
        if source in self._cache:
            return self._cache[source]
        result = self._match(source)
        self._cache[source] = result
        return result

    def _match(self, source: str) -> str | None:
        norm = normalise(source)
        if not norm:
            return None
        alias = _ALIASES_NORM.get(norm)
        if alias and normalise(alias) in self._by_norm:
            return self._by_norm[normalise(alias)]
        if norm in self._by_norm:
            return self._by_norm[norm]
        flipped = _equipment_first(source)
        if flipped and normalise(flipped) in self._by_norm:
            return self._by_norm[normalise(flipped)]
        candidates = [norm] + ([normalise(flipped)] if flipped else [])
        for candidate in candidates:
            close = difflib.get_close_matches(candidate, self._by_norm, n=1, cutoff=FUZZY_CUTOFF)
            if close:
                return self._by_norm[close[0]]
        return None
