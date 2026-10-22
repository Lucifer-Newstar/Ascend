"""Workout programs (programs-v1, ADR-0020): a small built-in catalog of training splits and
the rules that say which session is next.

A program is an ordered rotation of days; each day lists exercise slots (sets x a rep zone
at a target RPE). Two rules keep it honest with real life:

- **Rotation, not calendar.** The next session is the day after the last program day you
  actually trained, so a missed day shifts the plan instead of skipping a session. The
  weekday schedule is a suggestion shown beside it.
- **Read from the log.** A finished gym workout counts as a program day when it trained at
  least half of that day's exercises (the day with the largest overlap wins; ties go to the
  day that was due). Sessions logged by hand, imported or started from the program all
  count the same way, and nothing has to be "started" for the plan to advance.

Loads and reps come from prog-v1 per exercise (ADR-0015) and deload weeks from deload-v2,
so the program decides *what* to train and the engines decide *how much*.

Pure: no I/O. The service reads workouts and passes names in.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

ALGO_VERSION = "programs-v1"
MATCH_SHARE = 0.5


@dataclass(frozen=True)
class Slot:
    exercise: str
    sets: int
    rep_low: int
    rep_high: int
    target_rpe: float = 8.0
    rest_s: int = 120


@dataclass(frozen=True)
class Day:
    key: str
    name: str
    focus: str
    weekday: int  # suggested weekday, 0 = Monday
    slots: tuple[Slot, ...]


@dataclass(frozen=True)
class Program:
    key: str
    name: str
    summary: str
    level: str
    equipment: str  # "gym" | "dumbbells" (+ a pull-up bar)
    days: tuple[Day, ...]

    @property
    def days_per_week(self) -> int:
        return len(self.days)


def _s(ex: str, sets: int, lo: int, hi: int, rpe: float = 8.0, rest: int = 120) -> Slot:
    return Slot(ex, sets, lo, hi, rpe, rest)


PROGRAMS: dict[str, Program] = {
    p.key: p
    for p in (
        Program(
            "full_body_3",
            "Full body, 3 days",
            "Three whole-body sessions a week on alternating A and B days. A good first program.",
            "beginner",
            "gym",
            (
                Day(
                    "a1",
                    "Full body A",
                    "Squat, press, row",
                    0,
                    (
                        _s("Back Squat", 3, 5, 8, rest=180),
                        _s("Barbell Bench Press", 3, 5, 8, rest=180),
                        _s("Barbell Row", 3, 6, 10),
                        _s("Lateral Raise", 2, 10, 15, rest=60),
                        _s("Plank (60 s = 1 set)", 2, 1, 1, 7.0, 60),
                    ),
                ),  # fmt: skip
                Day(
                    "b1",
                    "Full body B",
                    "Hinge, overhead, pull",
                    2,
                    (
                        _s("Romanian Deadlift", 3, 6, 10, rest=180),
                        _s("Overhead Press", 3, 5, 8, rest=150),
                        _s("Lat Pulldown", 3, 8, 12),
                        _s("Walking Lunge", 2, 8, 12),
                        _s("Hanging Leg Raise", 2, 8, 12, rest=60),
                    ),
                ),  # fmt: skip
                Day(
                    "a2",
                    "Full body A",
                    "Squat, press, row",
                    4,
                    (
                        _s("Back Squat", 3, 5, 8, rest=180),
                        _s("Barbell Bench Press", 3, 5, 8, rest=180),
                        _s("Barbell Row", 3, 6, 10),
                        _s("Lateral Raise", 2, 10, 15, rest=60),
                        _s("Plank (60 s = 1 set)", 2, 1, 1, 7.0, 60),
                    ),
                ),  # fmt: skip
            ),
        ),
        Program(
            "upper_lower_4",
            "Upper / lower, 4 days",
            "Each muscle twice a week with one heavier and one lighter day per half.",
            "intermediate",
            "gym",
            (
                Day(
                    "upper_a",
                    "Upper A",
                    "Heavy press and row",
                    0,
                    (
                        _s("Barbell Bench Press", 4, 5, 8, rest=180),
                        _s("Barbell Row", 4, 6, 10, rest=150),
                        _s("Overhead Press", 3, 6, 10),
                        _s("Lat Pulldown", 3, 8, 12),
                        _s("Barbell Curl", 2, 8, 12, rest=60),
                        _s("Triceps Pushdown", 2, 10, 15, rest=60),
                    ),
                ),  # fmt: skip
                Day(
                    "lower_a",
                    "Lower A",
                    "Squat focus",
                    1,
                    (
                        _s("Back Squat", 4, 5, 8, rest=180),
                        _s("Romanian Deadlift", 3, 6, 10, rest=150),
                        _s("Leg Press", 3, 10, 15),
                        _s("Leg Curl", 3, 10, 15, rest=60),
                        _s("Standing Calf Raise", 3, 10, 15, rest=60),
                    ),
                ),  # fmt: skip
                Day(
                    "upper_b",
                    "Upper B",
                    "Volume and shoulders",
                    3,
                    (
                        _s("Incline Dumbbell Press", 3, 8, 12),
                        _s("Seated Cable Row", 3, 8, 12),
                        _s("Seated Dumbbell Shoulder Press", 3, 8, 12),
                        _s("Pull-up", 3, 5, 10),
                        _s("Lateral Raise", 3, 12, 20, rest=60),
                        _s("Face Pull", 2, 12, 20, rest=60),
                    ),
                ),  # fmt: skip
                Day(
                    "lower_b",
                    "Lower B",
                    "Hinge focus",
                    4,
                    (
                        _s("Deadlift", 3, 3, 6, rest=210),
                        _s("Front Squat", 3, 6, 10, rest=150),
                        _s("Bulgarian Split Squat", 3, 8, 12),
                        _s("Hip Thrust", 3, 8, 12),
                        _s("Hanging Leg Raise", 3, 8, 15, rest=60),
                    ),
                ),  # fmt: skip
            ),
        ),
        Program(
            "ppl_6",
            "Push / pull / legs, 6 days",
            "The classic split run twice a week. High volume; needs good recovery.",
            "advanced",
            "gym",
            tuple(
                Day(f"{k}{n}", name, focus, wd, slots)
                for n, offset in ((1, 0), (2, 3))
                for k, name, focus, wd, slots in (
                    (
                        "push",
                        "Push",
                        "Chest, shoulders, triceps",
                        0 + offset,
                        (
                            _s("Barbell Bench Press", 4, 5, 8, rest=180),
                            _s("Overhead Press", 3, 6, 10, rest=150),
                            _s("Incline Dumbbell Press", 3, 8, 12),
                            _s("Lateral Raise", 3, 12, 20, rest=60),
                            _s("Triceps Pushdown", 3, 10, 15, rest=60),
                        ),
                    ),
                    (
                        "pull",
                        "Pull",
                        "Back, rear delts, biceps",
                        1 + offset,
                        (
                            _s("Barbell Row", 4, 6, 10, rest=150),
                            _s("Lat Pulldown", 3, 8, 12),
                            _s("Seated Cable Row", 3, 8, 12),
                            _s("Face Pull", 3, 12, 20, rest=60),
                            _s("Dumbbell Curl", 3, 8, 12, rest=60),
                        ),
                    ),
                    (
                        "legs",
                        "Legs",
                        "Quads, hamstrings, calves",
                        2 + offset,
                        (
                            _s("Back Squat", 4, 5, 8, rest=180),
                            _s("Romanian Deadlift", 3, 6, 10, rest=150),
                            _s("Leg Press", 3, 10, 15),
                            _s("Leg Curl", 3, 10, 15, rest=60),
                            _s("Standing Calf Raise", 4, 10, 15, rest=60),
                        ),
                    ),
                )
            ),  # fmt: skip
        ),
        Program(
            "home_full_body_3",
            "Home full body, 3 days",
            "Dumbbells and a pull-up bar: three whole-body sessions a week.",
            "beginner",
            "dumbbells",
            (
                Day(
                    "home_a",
                    "Home A",
                    "Legs, push, pull",
                    0,
                    (
                        _s("Bulgarian Split Squat", 3, 8, 12),
                        _s("Dumbbell Bench Press", 3, 8, 12),
                        _s("One-arm Dumbbell Row", 3, 8, 12),
                        _s("Lateral Raise", 2, 12, 20, rest=60),
                        _s("Plank (60 s = 1 set)", 2, 1, 1, 7.0, 60),
                    ),
                ),  # fmt: skip
                Day(
                    "home_b",
                    "Home B",
                    "Hinge, overhead, pull-ups",
                    2,
                    (
                        _s("Walking Lunge", 3, 10, 14),
                        _s("Seated Dumbbell Shoulder Press", 3, 8, 12),
                        _s("Pull-up", 3, 4, 10, rest=150),
                        _s("Push-up", 2, 8, 20, rest=90),
                        _s("Hammer Curl", 2, 10, 15, rest=60),
                    ),
                ),  # fmt: skip
                Day(
                    "home_c",
                    "Home C",
                    "Volume day",
                    4,
                    (
                        _s("Bulgarian Split Squat", 3, 10, 15),
                        _s("Incline Dumbbell Press", 3, 8, 12),
                        _s("Chin-up", 3, 4, 10, rest=150),
                        _s("Rear Delt Fly", 2, 12, 20, rest=60),
                        _s("Russian Twist", 2, 12, 20, rest=60),
                    ),
                ),  # fmt: skip
            ),
        ),
    )
}


def exercise_names(program: Program) -> set[str]:
    return {s.exercise for d in program.days for s in d.slots}


def match_day(program: Program, trained: set[str], due: int) -> int | None:
    """Index of the program day a finished workout was, or None. A day matches when the
    workout trained at least MATCH_SHARE of its exercises; the largest overlap wins, and a
    tie goes to the day that was due."""
    best: tuple[float, int] | None = None
    n = len(program.days)
    for step in range(n):  # start at the due day so it wins ties
        i = (due + step) % n
        day = program.days[i]
        names = {s.exercise for s in day.slots}
        share = len(names & trained) / len(names)
        if share >= MATCH_SHARE and (best is None or share > best[0]):
            best = (share, i)
    return best[1] if best else None


@dataclass(frozen=True)
class Done:
    day: date
    index: int


@dataclass(frozen=True)
class PlanState:
    next_index: int
    sessions_done: int
    this_week_done: int
    week_start: date
    done: tuple[Done, ...]
    last_trained: date | None
    reason: str


def plan_state(
    program: Program, started: date, workouts: Sequence[tuple[date, set[str]]], today: date
) -> PlanState:
    """Walk the finished gym workouts since the start (oldest first) and say which day is
    next. Workouts that match no program day (an extra arm session) are ignored."""
    due = 0
    done: list[Done] = []
    for day, trained in sorted(workouts, key=lambda w: w[0]):
        if day < started or day > today:
            continue
        i = match_day(program, trained, due)
        if i is None:
            continue
        done.append(Done(day, i))
        due = (i + 1) % len(program.days)
    week_start = today - timedelta(days=today.weekday())
    this_week = sum(1 for d in done if d.day >= week_start)
    last = done[-1].day if done else None
    nxt = program.days[due]
    if not done:
        reason = f"first session of the program: {nxt.name}"
    else:
        prev = program.days[done[-1].index]
        reason = (
            f"you last trained {prev.name} on {done[-1].day.isoformat()}, so {nxt.name} is next"
        )
    return PlanState(due, len(done), this_week, week_start, tuple(done), last, reason)
