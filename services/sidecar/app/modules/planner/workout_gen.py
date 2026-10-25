"""plangen-v1: a custom workout program from goal, experience, equipment and schedule.

Rule-based and deterministic: the same answers give the same program. The split follows
the days per week (2-3 full body, 4 upper/lower, 5 push/pull/legs + upper/lower, 6 push/
pull/legs twice); each day is a list of movement slots filled with the first library
exercise the user's equipment allows; sets, reps and rest follow the focus. The local
model may reword the summary afterwards, never the numbers (planner/service.py).

Loads are not set here: once the program is followed, prog-v1 sets reps, load and RPE per
exercise from the user's own log, exactly as for the built-in programs.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

ALGO_VERSION = "plangen-v1"

Focus = Literal["strength", "muscle", "fat_loss", "skills", "general"]
Experience = Literal["beginner", "intermediate", "advanced"]
Tier = Literal["gym", "dumbbells", "bodyweight"]

MAX_DAYS = 6
MAX_MINUTES = 90

# Movement slot -> candidates per equipment tier, best first. Names are library names
# (tests check each exists); the first one the user's equipment allows is used, and a
# repeated day type takes the next one for variety.
SLOTS: dict[str, dict[Tier, tuple[str, ...]]] = {
    "squat": {
        "gym": ("Back Squat", "Front Squat", "Leg Press", "Goblet Squat"),
        "dumbbells": ("Goblet Squat", "Dumbbell Squat", "Bulgarian Split Squat"),
        "bodyweight": ("Bodyweight Squat", "Box Pistol Squat", "Assisted Pistol Squat"),
    },
    "hinge": {
        "gym": ("Romanian Deadlift", "Deadlift", "Hip Thrust", "Leg Curl"),
        "dumbbells": ("Stiff-Legged Dumbbell Deadlift", "Single-leg Glute Bridge"),
        "bodyweight": ("Single-leg Glute Bridge", "Nordic Curl Negative"),
    },
    "lunge": {
        "gym": ("Walking Lunge", "Bulgarian Split Squat", "Dumbbell Lunges"),
        "dumbbells": ("Walking Lunge", "Split Squat with Dumbbells", "Dumbbell Step Ups"),
        "bodyweight": ("Bodyweight Walking Lunge", "Box Pistol Squat"),
    },
    "hpush": {
        "gym": ("Barbell Bench Press", "Incline Dumbbell Press", "Dumbbell Bench Press"),
        "dumbbells": (
            "Dumbbell Bench Press",
            "Incline Dumbbell Press",
            "Dumbbell Floor Press",
            "Push-up",
        ),
        "bodyweight": ("Push-up", "Diamond Push-up", "Archer Push-up", "Incline Push-up"),
    },
    "vpush": {
        "gym": ("Overhead Press", "Seated Dumbbell Shoulder Press"),
        "dumbbells": ("Seated Dumbbell Shoulder Press",),
        "bodyweight": ("Pike Push-up", "Elevated Pike Push-up"),
    },
    "hpull": {
        "gym": ("Barbell Row", "Seated Cable Row", "One-arm Dumbbell Row"),
        "dumbbells": ("One-arm Dumbbell Row", "Bent Over Two-Dumbbell Row"),
        "bodyweight": ("Inverted Row", "Superman"),
    },
    "vpull": {
        "gym": ("Lat Pulldown", "Pull-up", "Chin-up"),
        "dumbbells": ("Pull-up", "Chin-up", "Negative Pull-up"),
        "bodyweight": ("Pull-up", "Negative Pull-up", "Chin-up"),
    },
    "biceps": {
        "gym": ("Barbell Curl", "Hammer Curl", "Dumbbell Curl"),
        "dumbbells": ("Hammer Curl", "Dumbbell Curl"),
        "bodyweight": ("Chin-up",),
    },
    "triceps": {
        "gym": ("Triceps Pushdown", "Overhead Triceps Extension"),
        "dumbbells": ("Overhead Triceps Extension",),
        "bodyweight": ("Diamond Push-up", "Bench Dips"),
    },
    "shoulders": {
        "gym": ("Lateral Raise", "Face Pull", "Rear Delt Fly"),
        "dumbbells": ("Lateral Raise", "Rear Delt Fly"),
        "bodyweight": ("Pike Push-up",),
    },
    # v1.3: the pull day's extra slot is a pulling shoulder move (rear delts), never a
    # lateral raise standing in for a missing pull-up.
    "rear_delts": {
        "gym": ("Face Pull", "Rear Delt Fly"),
        "dumbbells": ("Rear Delt Fly",),
        "bodyweight": ("Inverted Row",),
    },
    "core": {
        "gym": ("Hanging Leg Raise", "Plank", "Russian Twist"),
        "dumbbells": ("Hanging Leg Raise", "Plank", "Russian Twist"),
        "bodyweight": ("Hollow Body Hold", "Plank", "Lying Leg Raise", "Side Plank"),
    },
    "calves": {
        "gym": ("Standing Calf Raise", "Seated Calf Raise"),
        "dumbbells": ("Calf Raise On A Dumbbell",),
        "bodyweight": (),
    },
}

# Day types: name, focus line, slots in priority order (fewer minutes = fewer slots).
DAY_TYPES: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "full_a": (
        "Full body A",
        "Squat, push, pull",
        ("squat", "hpush", "hpull", "shoulders", "core", "biceps", "calves"),
    ),
    "full_b": (
        "Full body B",
        "Hinge, press, pull-up",
        ("hinge", "vpush", "vpull", "lunge", "core", "triceps", "calves"),
    ),
    "full_c": (
        "Full body C",
        "Legs, push, pull",
        ("lunge", "hpush", "vpull", "hinge", "shoulders", "biceps", "core"),
    ),
    "upper": (
        "Upper",
        "Press and pull",
        ("hpush", "hpull", "vpush", "vpull", "shoulders", "biceps", "triceps"),
    ),
    "lower": (
        "Lower",
        "Squat and hinge",
        ("squat", "hinge", "lunge", "calves", "core", "hinge", "squat"),
    ),
    "push": (
        "Push",
        "Chest, shoulders, triceps",
        ("hpush", "vpush", "hpush", "shoulders", "triceps", "core", "shoulders"),
    ),
    "pull": (
        "Pull",
        "Back and biceps",
        ("vpull", "hpull", "hpull", "rear_delts", "biceps", "core", "biceps"),
    ),
    "legs": (
        "Legs",
        "Quads, hamstrings, glutes",
        ("squat", "hinge", "lunge", "calves", "core", "squat", "hinge"),
    ),
}

SPLITS: dict[int, tuple[str, ...]] = {
    1: ("full_a",),
    2: ("full_a", "full_b"),
    3: ("full_a", "full_b", "full_c"),
    4: ("upper", "lower", "upper", "lower"),
    5: ("push", "pull", "legs", "upper", "lower"),
    6: ("push", "pull", "legs", "push", "pull", "legs"),
}
WEEKDAYS: dict[int, tuple[int, ...]] = {
    1: (0,),
    2: (0, 3),
    3: (0, 2, 4),
    4: (0, 1, 3, 4),
    5: (0, 1, 2, 4, 5),
    6: (0, 1, 2, 3, 4, 5),
}
LABELS: dict[str, str] = {
    "strength": "Strength",
    "muscle": "Muscle",
    "fat_loss": "Fat-loss",
    "skills": "Skills",
    "general": "General",
}
SPLIT_NAMES: dict[int, str] = {
    1: "full body",
    2: "full body",
    3: "full body",
    4: "upper/lower",
    5: "push/pull/legs + upper/lower",
    6: "push/pull/legs",
}
ISOLATION = {"biceps", "triceps", "shoulders", "rear_delts", "calves", "core"}


@dataclass(frozen=True)
class SlotOut:
    exercise: str
    sets: int
    rep_low: int
    rep_high: int
    target_rpe: float
    rest_s: int
    # v1.3: "hold" when rep_low / rep_high are seconds, so the planner shows "30-45 s"
    measure: str = "reps"


@dataclass(frozen=True)
class DayOut:
    key: str
    name: str
    focus: str
    weekday: int
    slots: tuple[SlotOut, ...]


@dataclass(frozen=True)
class GeneratedProgram:
    name: str
    summary: str
    level: Experience
    equipment: Tier
    days: tuple[DayOut, ...]
    notes: tuple[str, ...] = field(default=())
    algo_version: str = ALGO_VERSION


# v1.2: timed holds are dosed in seconds (rep_low/rep_high hold seconds for them).
HOLD_SECONDS: dict[str, tuple[int, int]] = {
    "beginner": (20, 30),
    "intermediate": (30, 45),
    "advanced": (45, 60),
}
# v1.2: moves whose reps a beginner may not have yet; capped by the baseline test.
BAR_PULLS = frozenset({"Pull-up", "Chin-up", "Chest-to-bar Pull-up"})
FLOOR_PUSHES = frozenset(
    {"Push-up", "Diamond Push-up", "Archer Push-up", "Pike Push-up", "Elevated Pike Push-up"}
)
EASIER_PULLS = ("Negative Pull-up", "Inverted Row", "Scapular Pull-up")
EASIER_PUSHES = ("Incline Push-up", "Incline Push-Up Medium")
MIN_PULLUPS = 3  # below this, bar pulls become negatives / rows
MIN_PUSHUPS = 5  # below this, floor push-ups become incline push-ups
# v1.3: a working set is about 60-80 % of the baseline max (15 push-ups -> 9-12 reps, not
# the generic 6-10), capped where the next harder variation is the better step.
WORK_LOW, WORK_HIGH = 0.6, 0.8
MAX_REP_TARGET = 25
# Holds with a baseline test (seconds): the hold dosed from it, in seconds.
HOLD_BASELINE = {"Plank": "plank_s", "Side Plank": "plank_s", "Dead Hang": "dead_hang_s"}
MAX_HOLD_TARGET = 120


def _fit_to_capacity(
    ex: str,
    lo: int,
    hi: int,
    capacity: Mapping[str, int | None],
    usable: Callable[[str], bool],
) -> tuple[str, int, int] | None:
    """Swap or cap a move the user cannot do for that many reps yet (baseline test).
    None means "leave this slot out"."""
    pulls, pushes = capacity.get("pullups"), capacity.get("pushups")
    if ex in BAR_PULLS and pulls is not None:
        if pulls < MIN_PULLUPS:
            easier = next((e for e in EASIER_PULLS if usable(e)), None)
            return (easier, 3, 5) if easier else None
        lo, hi = _from_max(pulls)
    elif ex in FLOOR_PUSHES and pushes is not None:
        if pushes < MIN_PUSHUPS:
            easier = next((e for e in EASIER_PUSHES if usable(e)), None)
            return (easier, 5, 8) if easier else None
        # Harder variations (diamond, archer, pike) are dosed lower than plain push-ups.
        lo, hi = _from_max(pushes if ex == "Push-up" else max(MIN_PUSHUPS, round(pushes * 0.6)))
    return ex, min(lo, hi), hi


def _from_max(best: int) -> tuple[int, int]:
    """(rep_low, rep_high) from a max-effort result: about 60-80 % of it."""
    hi = max(2, min(MAX_REP_TARGET, round(best * WORK_HIGH)))
    lo = max(1, min(hi, round(best * WORK_LOW)))
    return lo, hi


def hold_dose(
    ex: str, experience: Experience, capacity: Mapping[str, int | None]
) -> tuple[int, int]:
    """Seconds per hold: from the baseline test when there is one (60-80 % of the best
    hold, rounded to 5 s), else by experience."""
    key = HOLD_BASELINE.get(ex)
    best = capacity.get(key) if key else None
    if not best:
        return HOLD_SECONDS[experience]
    scale = 0.5 if ex == "Side Plank" else 1.0
    lo = max(10, min(MAX_HOLD_TARGET, 5 * round(best * scale * WORK_LOW / 5)))
    hi = max(lo, min(MAX_HOLD_TARGET, 5 * round(best * scale * WORK_HIGH / 5)))
    return lo, hi


def swap_for_kit(name: str, available: Callable[[str], bool]) -> str | None:
    """v1.3: a built-in program's move the user's kit can't do ("Barbell Bench Press" with
    only dumbbells) -> the first move of the same slot they can do, dumbbells before body
    weight. None when nothing fits."""
    if available(name):
        return name
    for tiers in SLOTS.values():
        if any(name in names for names in tiers.values()):
            order: tuple[Tier, ...] = ("dumbbells", "bodyweight", "gym")
            for tier in order:
                for cand in tiers[tier]:
                    if cand != name and available(cand):
                        return cand
    return None


def tier_for(choices: Sequence[str]) -> Tier:
    picked = set(choices)
    if not picked or "gym" in picked:
        return "gym"
    if "dumbbells" in picked:
        return "dumbbells"
    return "bodyweight"


def exercises_per_day(minutes: int) -> int:
    """About 9 minutes per exercise after a 10-minute warm-up; 3 to 7 exercises."""
    return max(3, min(7, round((min(minutes, MAX_MINUTES) - 10) / 9)))


def _dose(
    focus: Focus, slot: str, position: int, experience: Experience
) -> tuple[int, int, int, float, int]:
    """(sets, rep_low, rep_high, rpe, rest_s) for a slot."""
    iso = slot in ISOLATION
    if focus == "strength" and not iso:
        sets, lo, hi, rpe, rest = (4, 3, 6, 8.0, 180) if position < 2 else (3, 6, 10, 8.0, 120)
    elif focus == "fat_loss":
        sets, lo, hi, rpe, rest = (3, 8, 12, 8.0, 90) if not iso else (2, 12, 15, 8.0, 60)
    elif iso:
        sets, lo, hi, rpe, rest = 3, 10, 15, 8.0, 75
    else:
        sets, lo, hi, rpe, rest = 3, 6, 10, 8.0, 120
    if experience == "beginner":
        sets = max(2, sets - (1 if position >= 2 else 0))
        rpe = min(rpe, 7.5)
    elif experience == "advanced" and position == 0:
        sets += 1
    if slot == "core":
        lo, hi = (8, 15)
    return sets, lo, hi, rpe, rest


def generate(
    *,
    focus: Focus,
    experience: Experience,
    equipment: Sequence[str],
    days_per_week: int,
    minutes: int,
    available: Callable[[str], bool],
    is_hold: Callable[[str], bool] = lambda _n: False,
    capacity: Mapping[str, int | None] | None = None,
) -> GeneratedProgram:
    """Build a program. `available(name)` says whether the user can do an exercise (it is
    in the library and fits their equipment); `is_hold(name)` marks timed holds (dosed in
    seconds); `capacity` carries the baseline test (max push-ups / pull-ups), so nobody is
    asked for 10-15 chin-ups when they can do one."""
    cap = dict(capacity or {})
    days_per_week = max(1, min(MAX_DAYS, days_per_week))
    tier = tier_for(equipment)
    per_day = exercises_per_day(minutes)
    seen: dict[str, int] = {}  # day type -> how many times used (for variety)
    days: list[DayOut] = []
    for i, dtype in enumerate(SPLITS[days_per_week]):
        name, focus_line, slots = DAY_TYPES[dtype]
        repeat = seen.get(dtype, 0)
        seen[dtype] = repeat + 1
        used: set[str] = set()
        out: list[SlotOut] = []
        slot_use: dict[str, int] = {}
        for slot in slots:
            if len(out) >= per_day:
                break
            cands = [c for c in SLOTS[slot][tier] if available(c) and c not in used]
            if not cands and tier != "bodyweight":
                cands = [c for c in SLOTS[slot]["bodyweight"] if available(c) and c not in used]
            if not cands:
                continue
            k = slot_use.get(slot, 0) + repeat
            slot_use[slot] = slot_use.get(slot, 0) + 1
            ex = cands[k % len(cands)]
            sets, lo, hi, rpe, rest = _dose(focus, slot, len(out), experience)
            taken = frozenset(used)

            def usable(n: str, taken: frozenset[str] = taken) -> bool:
                return available(n) and n not in taken

            fitted = _fit_to_capacity(ex, lo, hi, cap, usable)
            if fitted is None:
                continue
            ex, lo, hi = fitted
            used.add(ex)
            measure = "reps"
            if is_hold(ex):
                lo, hi = hold_dose(ex, experience, cap)
                measure = "hold"
            out.append(SlotOut(ex, sets, lo, hi, rpe, rest, measure))
        suffix = f" {repeat + 1}" if SPLITS[days_per_week].count(dtype) > 1 else ""
        days.append(
            DayOut(
                f"d{i + 1}", f"{name}{suffix}", focus_line, WEEKDAYS[days_per_week][i], tuple(out)
            )
        )
    notes: list[str] = []
    if focus == "fat_loss":
        notes.append("Add 20-30 minutes of walking or easy cardio on rest days.")
    if focus == "skills":
        notes.append("Practise your skill-tree step at the start of each session while fresh.")
    if tier == "bodyweight":
        notes.append("Bodyweight program: make reps harder by moving to the next variation.")
    label = LABELS[focus]
    split = SPLIT_NAMES[days_per_week]
    summary = (
        f"{label} program, {days_per_week} day{'s' if days_per_week > 1 else ''} a week "
        f"({split}), about {min(minutes, MAX_MINUTES)} minutes a session, for a {experience} "
        f"with {'a full gym' if tier == 'gym' else tier}."
    )
    return GeneratedProgram(
        name=f"{label} {split} ({days_per_week}x)",
        summary=summary,
        level=experience,
        equipment=tier,
        days=tuple(days),
        notes=tuple(notes),
    )
