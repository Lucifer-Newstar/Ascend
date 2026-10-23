"""Programs v2 (v1.2): more built-in programs, so every section has one at each level.

Each is tagged Beginner, Intermediate or Expert and with its section (gym, calisthenics,
cardio, martial arts, flexibility, meditation). The rules are the same as programs-v1
(rotation, read from the log). Time-based moves (cardio, martial arts, mobility,
meditation) are dosed in minutes per set, holds in seconds, everything else in reps.
"""

from __future__ import annotations

from app.modules.workouts.programs import Day, Program, Slot


def _s(ex: str, sets: int, lo: int, hi: int, rpe: float = 7.5, rest: int = 90) -> Slot:
    return Slot(ex, sets, lo, hi, rpe, rest)


def _rotation(
    days: list[tuple[str, str, tuple[Slot, ...]]], weekdays: tuple[int, ...]
) -> tuple[Day, ...]:
    out = []
    for i, (name, focus, slots) in enumerate(days):
        out.append(Day(f"d{i + 1}", name, focus, weekdays[i], slots))
    return tuple(out)


# --- calisthenics -------------------------------------------------------------------------

_RINGS_A = (
    _s("Ring Support Hold", 3, 15, 30, 7.5, 90),
    _s("Ring Dip", 3, 4, 8, 8.0, 120),
    _s("Inverted Row", 3, 6, 10, 8.0, 90),
    _s("Bodyweight Squat", 3, 12, 20, 7.5, 60),
    _s("Hollow Body Hold", 3, 20, 40, 7.5, 60),
)
_RINGS_B = (
    _s("Skin the Cat", 3, 2, 5, 7.5, 120),
    _s("German Hang", 2, 10, 20, 7.0, 90),
    _s("Push-up", 3, 8, 15, 8.0, 90),
    _s("Tuck L-sit", 3, 10, 20, 7.5, 90),
    _s("Tuck Back Lever", 3, 8, 15, 8.0, 120),
)

_BAR_PULL = (
    _s("Pull-up", 4, 4, 8, 8.0, 150),
    _s("Scapular Pull-up", 2, 8, 12, 7.0, 60),
    _s("Tuck Front Lever", 3, 8, 15, 8.0, 120),
    _s("Hanging Leg Raise", 3, 6, 12, 8.0, 90),
)
_BAR_PUSH = (
    _s("Pike Push-up", 4, 5, 10, 8.0, 120),
    _s("Diamond Push-up", 3, 6, 12, 8.0, 90),
    _s("Assisted Pistol Squat", 3, 5, 8, 8.0, 120),
    _s("Tuck L-sit", 3, 10, 20, 7.5, 90),
)

_EXP_PULL = (
    _s("Muscle-up", 4, 2, 5, 8.5, 180),
    _s("Chest-to-bar Pull-up", 3, 5, 8, 8.5, 150),
    _s("Advanced Tuck Front Lever", 4, 8, 15, 8.5, 150),
    _s("Dragon Flag Negative", 3, 3, 6, 8.5, 120),
)
_EXP_PUSH = (
    _s("Wall Handstand Push-up", 4, 3, 6, 8.5, 180),
    _s("Straight Bar Dip", 3, 6, 10, 8.5, 120),
    _s("Tuck Planche", 4, 8, 15, 8.5, 150),
    _s("Pistol Squat", 3, 4, 8, 8.5, 120),
    _s("Nordic Curl Negative", 3, 3, 6, 8.5, 120),
)

# --- gym ----------------------------------------------------------------------------------

_DB_UPPER = (
    _s("Dumbbell Bench Press", 4, 6, 10, 8.0, 120),
    _s("One-arm Dumbbell Row", 4, 8, 12, 8.0, 90),
    _s("Seated Dumbbell Shoulder Press", 3, 8, 12, 8.0, 90),
    _s("Hammer Curl", 2, 10, 15, 8.0, 60),
    _s("Overhead Triceps Extension", 2, 10, 15, 8.0, 60),
)
_DB_LOWER = (
    _s("Bulgarian Split Squat", 4, 8, 12, 8.0, 120),
    _s("Stiff-Legged Dumbbell Deadlift", 4, 8, 12, 8.0, 120),
    _s("Walking Lunge", 3, 10, 14, 8.0, 90),
    _s("Plank", 3, 30, 45, 7.5, 60),
)

# --- cardio (minutes) ----------------------------------------------------------------------

_WALK = (_s("Brisk Walking", 1, 15, 20, 6.0, 0), _s("Running", 1, 3, 8, 7.0, 0))
_BASE_RUN = (_s("Running", 1, 25, 35, 7.0, 0),)
_BASE_ROPE = (_s("Jump Rope", 4, 3, 3, 7.5, 60), _s("Stair Climbing", 1, 10, 15, 7.0, 0))
_BASE_LONG = (_s("Brisk Walking", 1, 40, 60, 6.0, 0),)
_COND_INT = (
    _s("Running", 6, 2, 3, 8.5, 90),
    _s("Sprawl Drill", 4, 1, 1, 8.5, 60),
    _s("Fighter Core Circuit", 1, 8, 12, 8.0, 0),
)
_COND_ROPE = (
    _s("Fighter Jump Rope Rounds", 5, 3, 3, 8.0, 60),
    _s("Stair Climbing", 1, 15, 20, 8.0, 0),
)

# --- martial arts (minutes per round) -----------------------------------------------------

_BOX_A = (
    _s("Boxing Stance and Guard Drill", 2, 2, 3, 6.0, 60),
    _s("Jab-Cross Shadow Drill", 3, 3, 3, 7.0, 60),
    _s("Boxing Footwork Drill", 2, 3, 3, 7.0, 60),
    _s("Fighter Core Circuit", 1, 6, 10, 7.0, 0),
)
_BOX_B = (
    _s("Shadowboxing", 3, 3, 3, 7.0, 60),
    _s("Slip and Roll Drill", 2, 2, 3, 7.0, 60),
    _s("Horse Stance Hold", 2, 1, 2, 7.0, 60),
)
_KICK_A = (
    _s("Teep Push Kick Drill", 3, 2, 3, 7.5, 60),
    _s("Roundhouse Kick Drill", 3, 2, 3, 7.5, 60),
    _s("Front Kick Drill", 2, 2, 3, 7.0, 60),
    _s("Stance Walk Drill", 1, 3, 5, 6.5, 0),
)
_KICK_B = (
    _s("Knee Strike Drill", 3, 2, 3, 8.0, 60),
    _s("Kickboxing Shadow Rounds", 3, 3, 3, 8.0, 60),
    _s("Side Kick Drill", 2, 2, 3, 7.5, 60),
)
_FIGHT_A = (
    _s("Kickboxing Shadow Rounds", 5, 3, 3, 8.5, 60),
    _s("Sprawl Drill", 4, 1, 2, 8.5, 60),
    _s("Fighter Core Circuit", 1, 10, 12, 8.0, 0),
)
_FIGHT_B = (
    _s("Fighter Jump Rope Rounds", 4, 3, 3, 8.0, 60),
    _s("Jab-Cross Shadow Drill", 4, 3, 3, 8.5, 60),
    _s("Slip and Roll Drill", 3, 2, 3, 8.0, 60),
    _s("Horse Stance Hold", 3, 1, 2, 8.0, 60),
)

# --- flexibility and meditation (minutes) ---------------------------------------------------

_MOB_A = (
    _s("World's Greatest Stretch", 2, 1, 2, 5.0, 0),
    _s("Deep Squat Hold", 2, 1, 2, 5.0, 0),
    _s("Kneeling Hip Flexor Stretch", 2, 1, 1, 5.0, 0),
    _s("Doorway Chest Stretch", 2, 1, 1, 5.0, 0),
)
_MOB_B = (
    _s("Cat Stretch", 2, 1, 1, 5.0, 0),
    _s("Pigeon Pose", 2, 1, 2, 5.0, 0),
    _s("Standing Hamstring Stretch", 2, 1, 1, 5.0, 0),
    _s("Child's Pose", 1, 1, 2, 5.0, 0),
)
_CALM = (_s("Box Breathing", 1, 3, 5, 3.0, 0), _s("Mindfulness Meditation", 1, 5, 10, 3.0, 0))
_SCAN = (_s("Body Scan", 1, 8, 12, 3.0, 0),)

PROGRAMS_V12: tuple[Program, ...] = (
    Program(
        "rings_basics_3",
        "Rings Basics, 3 days",
        "Rings and body weight. Support holds and ring dips build pressing strength; skin "
        "the cat, German hangs and tuck back levers build the shoulders for ring skills.",
        "intermediate",
        "rings",
        _rotation(
            [
                ("Rings A", "Support, dip, row", _RINGS_A),
                ("Rings B", "Shoulders, core", _RINGS_B),
                ("Rings A", "Support, dip, row", _RINGS_A),
            ],
            (0, 2, 4),
        ),
        section="calisthenics",
    ),
    Program(
        "bar_skills_4",
        "Bar Skills, 4 days",
        "A pull-up bar and the floor, for hunters past their first pull-ups: weighted "
        "volume, the tuck front lever, pike push-ups and the first pistol squats.",
        "intermediate",
        "bar",
        _rotation(
            [
                ("Pull + lever", "Pull, front lever", _BAR_PULL),
                ("Push + legs", "Pike, pistol", _BAR_PUSH),
                ("Pull + lever", "Pull, front lever", _BAR_PULL),
                ("Push + legs", "Pike, pistol", _BAR_PUSH),
            ],
            (0, 1, 3, 4),
        ),
        section="calisthenics",
    ),
    Program(
        "calisthenics_expert_4",
        "Calisthenics Expert, 4 days",
        "Muscle-ups, advanced tuck front lever, wall handstand push-ups, tuck planche and "
        "pistols. For hunters who already own clean pull-ups, dips and a wall handstand.",
        "expert",
        "bar",
        _rotation(
            [
                ("Expert pull", "Muscle-up, lever", _EXP_PULL),
                ("Expert push", "Handstand, planche", _EXP_PUSH),
                ("Expert pull", "Muscle-up, lever", _EXP_PULL),
                ("Expert push", "Handstand, planche", _EXP_PUSH),
            ],
            (0, 1, 3, 5),
        ),
        section="calisthenics",
    ),
    Program(
        "dumbbell_upper_lower_4",
        "Dumbbell Upper / Lower, 4 days",
        "Two upper and two lower days with only dumbbells: presses, rows, split squats "
        "and Romanian deadlifts, with double progression on every lift.",
        "intermediate",
        "dumbbells",
        _rotation(
            [
                ("Upper", "Press, row", _DB_UPPER),
                ("Lower", "Split squat, hinge", _DB_LOWER),
                ("Upper", "Press, row", _DB_UPPER),
                ("Lower", "Split squat, hinge", _DB_LOWER),
            ],
            (0, 1, 3, 4),
        ),
        section="gym",
    ),
    Program(
        "walk_to_run_3",
        "Walk to Run, 3 days",
        "Brisk walking with a few minutes of easy running. Add a minute of running when "
        "the top of the range feels easy; no kit needed.",
        "beginner",
        "bodyweight",
        _rotation([("Walk + run", "Easy cardio", _WALK)] * 3, (0, 2, 5)),
        section="cardio",
    ),
    Program(
        "cardio_base_4",
        "Cardio Base, 4 days",
        "An easy run, rope and stairs, and one long walk a week: the aerobic base that "
        "makes every other session easier.",
        "intermediate",
        "bodyweight",
        _rotation(
            [
                ("Easy run", "Steady", _BASE_RUN),
                ("Rope + stairs", "Intervals", _BASE_ROPE),
                ("Easy run", "Steady", _BASE_RUN),
                ("Long walk", "Long and easy", _BASE_LONG),
            ],
            (0, 2, 4, 6),
        ),
        section="cardio",
    ),
    Program(
        "conditioning_expert_4",
        "Fighter Conditioning, 4 days",
        "Run intervals, sprawls and rope rounds. Hard work: for hunters with a solid "
        "base who want fight-ready conditioning.",
        "expert",
        "bodyweight",
        _rotation(
            [
                ("Intervals", "Run, sprawl", _COND_INT),
                ("Rope rounds", "Rope, stairs", _COND_ROPE),
                ("Intervals", "Run, sprawl", _COND_INT),
                ("Rope rounds", "Rope, stairs", _COND_ROPE),
            ],
            (0, 1, 3, 5),
        ),
        section="cardio",
    ),
    Program(
        "boxing_basics_3",
        "Boxing Basics, 3 days",
        "Stance, guard, the jab-cross, footwork and head movement, all solo and in the "
        "air. Three-minute rounds with a minute of rest.",
        "beginner",
        "bodyweight",
        _rotation(
            [
                ("Boxing A", "Stance, jab-cross, feet", _BOX_A),
                ("Boxing B", "Shadow, slips", _BOX_B),
                ("Boxing A", "Stance, jab-cross, feet", _BOX_A),
            ],
            (0, 2, 4),
        ),
        section="martial_arts",
    ),
    Program(
        "kickboxing_solo_3",
        "Kickboxing Solo, 3 days",
        "Teeps, roundhouse and front kicks, knees and shadow rounds, done alone. Kicks "
        "stay at waist height or lower until the balance is solid.",
        "intermediate",
        "bodyweight",
        _rotation(
            [
                ("Kicks", "Teep, roundhouse, front", _KICK_A),
                ("Knees + shadow", "Knees, rounds", _KICK_B),
                ("Kicks", "Teep, roundhouse, front", _KICK_A),
            ],
            (0, 2, 4),
        ),
        section="martial_arts",
    ),
    Program(
        "fighter_rounds_4",
        "Fighter Rounds, 4 days",
        "Five-round shadow sessions, sprawls, rope and head movement. Solo, no partner; "
        "for hunters who already move well in the boxing and kick drills.",
        "expert",
        "bodyweight",
        _rotation(
            [
                ("Rounds", "Shadow, sprawl", _FIGHT_A),
                ("Speed", "Rope, combos, slips", _FIGHT_B),
                ("Rounds", "Shadow, sprawl", _FIGHT_A),
                ("Speed", "Rope, combos, slips", _FIGHT_B),
            ],
            (0, 1, 3, 5),
        ),
        section="martial_arts",
    ),
    Program(
        "daily_mobility_5",
        "Daily Mobility, 5 days",
        "Ten easy minutes of hips, hamstrings, chest and back. Good on rest days and "
        "after long hours at a desk.",
        "beginner",
        "bodyweight",
        _rotation(
            [
                ("Mobility A", "Hips, chest", _MOB_A),
                ("Mobility B", "Back, hamstrings", _MOB_B),
                ("Mobility A", "Hips, chest", _MOB_A),
                ("Mobility B", "Back, hamstrings", _MOB_B),
                ("Mobility A", "Hips, chest", _MOB_A),
            ],
            (0, 1, 2, 3, 4),
        ),
        section="flexibility",
    ),
    Program(
        "calm_mind_7",
        "Calm Mind, every day",
        "A few minutes of box breathing and a short meditation each day, with a body "
        "scan twice a week.",
        "beginner",
        "bodyweight",
        _rotation(
            [
                ("Breathe", "Box breathing, mindfulness", _CALM),
                ("Breathe", "Box breathing, mindfulness", _CALM),
                ("Body scan", "Body scan", _SCAN),
                ("Breathe", "Box breathing, mindfulness", _CALM),
                ("Breathe", "Box breathing, mindfulness", _CALM),
                ("Body scan", "Body scan", _SCAN),
                ("Breathe", "Box breathing, mindfulness", _CALM),
            ],
            (0, 1, 2, 3, 4, 5, 6),
        ),
        section="meditation",
    ),
)
