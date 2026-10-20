"""Calisthenics skill trees: progression steps and the numbers that unlock them.

Sources for the ORDER of the progressions (see docs/architecture/skill-trees.md for the
full list with links):
  [RR]  r/bodyweightfitness Recommended Routine and wiki exercise pages
  [OG]  Steven Low, "Overcoming Gravity", 2nd ed. (2016), progression charts
  [GMB] GMB Fitness tutorials (L-sit, pistol squat, handstand)
  [NHE] Nordic hamstring exercise programmes (e.g. Mjolsnes et al., 2004)

The THRESHOLDS (3x8, 3x20 s...) are ASCEND's choices, informed by the common rules in
those sources (advance at the top of a 3x5-8 rep range; isometrics in the 10-30 s range
before moving on). They are design choices, not measurements; steps where the sources
disagree or where we found nothing firm are marked `uncertain=True` and shown that way.

Each step names the exercise practised at that step. Its `unlock` criteria are what you
must show (in logged sets) to start it: usually mastery of the step before, sometimes a
feeder lift too, and for the last step a first real rep/hold of the skill itself, so
"Skill acquired" means you actually did it. Exercises are referenced by library name
(unique); tests check every name exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Criterion:
    exercise: str
    sets: int
    reps: int | None = None
    hold_s: int | None = None
    added_kg: float = 0.0
    per_side: bool = False

    @property
    def target(self) -> int:
        return int(self.hold_s if self.hold_s is not None else (self.reps or 1))

    @property
    def is_hold(self) -> bool:
        return self.hold_s is not None

    def describe(self) -> str:
        amount = f"{self.hold_s} s" if self.is_hold else f"{self.reps}"
        text = f"{self.sets}\u00d7{amount} {self.exercise}"
        if self.added_kg:
            text += f" at +{self.added_kg:g} kg"
        if self.per_side:
            text += " (each side)"
        return text


@dataclass(frozen=True)
class Step:
    key: str
    name: str
    exercise: str
    unlock: tuple[Criterion, ...] = ()
    # Steps that must be unlocked first; None = the previous step in the list.
    requires: tuple[str, ...] | None = None
    xp: int = 0
    uncertain: bool = False
    note: str = ""


@dataclass(frozen=True)
class Skill:
    key: str
    name: str
    family: str  # pull | push | core | balance | legs | levers
    summary: str
    steps: tuple[Step, ...]
    feeders: tuple[str, ...]
    sources: tuple[str, ...]
    stretch: bool = False  # a long-term goal; shown as such
    tags: tuple[str, ...] = field(default=())

    def requires_of(self, step: Step) -> tuple[str, ...]:
        if step.requires is not None:
            return step.requires
        i = self.steps.index(step)
        return (self.steps[i - 1].key,) if i > 0 else ()


def C(exercise: str, sets: int, reps: int | None = None, *, hold: int | None = None,
      kg: float = 0.0, side: bool = False) -> Criterion:  # fmt: skip
    return Criterion(exercise, sets, reps, hold, kg, side)


SOURCES: dict[str, tuple[str, str]] = {
    "RR": (
        "r/bodyweightfitness Recommended Routine",
        "https://www.reddit.com/r/bodyweightfitness/wiki/kb/recommended_routine/",
    ),
    "BWF": (
        "r/bodyweightfitness wiki: exercise progressions (e.g. front lever, pull-up)",
        "https://www.reddit.com/r/bodyweightfitness/wiki/exercises/front-lever/",
    ),
    "OG": (
        "Steven Low, Overcoming Gravity, 2nd ed. (2016)",
        "https://stevenlow.org/overcoming-gravity/",
    ),
    "GMB": ("GMB Fitness tutorials (e.g. L-sit progression)", "https://gmb.io/l-sit/"),
    "NHE": (
        "Mjolsnes et al. (2004), 10-week Nordic hamstring training trial",
        "https://pubmed.ncbi.nlm.nih.gov/15387805/",
    ),
}

SKILLS: tuple[Skill, ...] = (
    Skill(
        "muscle_up",
        "Muscle-up",
        "pull",
        "Pull above the bar and press out: the classic bar skill.",
        (
            Step("dead_hang", "Dead hang", "Dead Hang"),
            Step(
                "scap_pull",
                "Scapular pull-up",
                "Scapular Pull-up",
                (C("Dead Hang", 3, hold=30),),
                xp=30,
            ),
            Step(
                "negatives",
                "Negative pull-up",
                "Negative Pull-up",
                (C("Scapular Pull-up", 3, 10),),
                xp=40,
            ),
            Step("pull_up", "Pull-up", "Pull-up", (C("Negative Pull-up", 3, 5),), xp=80),
            Step(
                "c2b", "Chest-to-bar pull-up", "Chest-to-bar Pull-up", (C("Pull-up", 3, 8),), xp=80
            ),
            Step(
                "mu_negative",
                "Muscle-up negative",
                "Muscle-up Negative",
                (C("Pull-up", 3, 8), C("Chest Dip", 3, 10), C("Chest-to-bar Pull-up", 3, 3)),
                xp=100,
            ),
            Step(
                "muscle_up",
                "Muscle-up",
                "Muscle-up",
                (C("Muscle-up Negative", 3, 3), C("Straight Bar Dip", 3, 8), C("Muscle-up", 1, 1)),
                xp=250,
                note="Counts strict reps; log kipping reps separately if you do them.",
            ),
        ),
        (
            "Pull-up",
            "Chin-up",
            "Chest-to-bar Pull-up",
            "Chest Dip",
            "Straight Bar Dip",
            "Inverted Row",
        ),
        ("RR", "BWF", "OG"),
    ),
    Skill(
        "one_arm_push_up",
        "One-arm push-up",
        "push",
        "Push-up strength all the way to one arm.",
        (
            Step("incline", "Incline push-up", "Incline Push-up"),
            Step("push_up", "Push-up", "Push-up", (C("Incline Push-up", 3, 12),), xp=30),
            Step("diamond", "Diamond push-up", "Diamond Push-up", (C("Push-up", 3, 15),), xp=40),
            Step(
                "archer", "Archer push-up", "Archer Push-up", (C("Diamond Push-up", 3, 10),), xp=80
            ),
            Step(
                "incline_oap",
                "Incline one-arm push-up",
                "Incline One-arm Push-up",
                (C("Archer Push-up", 3, 6, side=True),),
                xp=100,
            ),
            Step(
                "oap",
                "One-arm push-up",
                "One-arm Push-up",
                (
                    C("Incline One-arm Push-up", 3, 5, side=True),
                    C("One-arm Push-up", 1, 1, side=True),
                ),
                xp=250,
            ),
        ),
        ("Push-up", "Diamond Push-up", "Pseudo Planche Push-up", "Chest Dip", "Plank"),
        ("RR", "BWF", "OG"),
    ),
    Skill(
        "dips",
        "Dips",
        "push",
        "From a support hold to weighted dips.",
        (
            Step("support", "Support hold", "Parallel Bar Support Hold"),
            Step(
                "negative",
                "Negative dip",
                "Negative Dip",
                (C("Parallel Bar Support Hold", 3, hold=30),),
                xp=30,
            ),
            Step("dip", "Parallel-bar dip", "Chest Dip", (C("Negative Dip", 3, 5),), xp=80),
            Step(
                "ring_dip",
                "Ring dip",
                "Ring Dip",
                (C("Chest Dip", 3, 10), C("Ring Support Hold", 3, hold=20)),
                xp=100,
            ),
            Step(
                "weighted",
                "Weighted dip",
                "Weighted Dip",
                (C("Ring Dip", 3, 8), C("Weighted Dip", 3, 5, kg=10)),
                xp=150,
                uncertain=True,
                note="+10 kg is a fixed starting load; relative to bodyweight would be fairer.",
            ),
        ),
        (
            "Chest Dip",
            "Straight Bar Dip",
            "Close-grip Bench Press",
            "Diamond Push-up",
            "Triceps Pushdown",
        ),
        ("RR", "BWF"),
    ),
    Skill(
        "l_sit",
        "Plank to V-sit",
        "core",
        "Plank, hollow body, L-sit, then the V-sit.",
        (
            Step("plank", "Plank", "Plank"),
            Step(
                "hollow", "Hollow body hold", "Hollow Body Hold", (C("Plank", 3, hold=60),), xp=30
            ),
            Step(
                "tuck_lsit", "Tuck L-sit", "Tuck L-sit", (C("Hollow Body Hold", 3, hold=30),), xp=40
            ),
            Step(
                "one_leg", "One-leg L-sit", "One-leg L-sit", (C("Tuck L-sit", 3, hold=15),), xp=60
            ),
            Step(
                "lsit",
                "L-sit",
                "L-sit",
                (C("One-leg L-sit", 3, hold=15), C("L-sit", 1, hold=10)),
                xp=200,
            ),
            Step(
                "vsit",
                "V-sit",
                "V-sit",
                (
                    C("L-sit", 3, hold=20),
                    C("Seated Pike Compression", 3, 10),
                    C("V-sit", 1, hold=3),
                ),
                xp=300,
                uncertain=True,
                note="Sources agree a strong L-sit and compression come first; numbers vary.",
            ),
        ),
        (
            "Hollow Body Hold",
            "Hanging Leg Raise",
            "Seated Pike Compression",
            "Parallel Bar Support Hold",
        ),
        ("RR", "GMB", "OG"),
    ),
    Skill(
        "handstand",
        "Handstand & HSPU",
        "balance",
        "Headstand to handstand, then handstand push-ups.",
        (
            Step("pike", "Pike push-up", "Pike Push-up"),
            Step("headstand", "Headstand", "Headstand", (C("Pike Push-up", 3, 8),), xp=40),
            Step(
                "wall_hs", "Wall handstand", "Wall Handstand", (C("Headstand", 3, hold=30),), xp=60
            ),
            Step(
                "free_hs",
                "Freestanding handstand",
                "Freestanding Handstand",
                (C("Wall Handstand", 3, hold=60), C("Freestanding Handstand", 1, hold=10)),
                requires=("wall_hs",),
                xp=250,
            ),
            Step(
                "elevated_pike",
                "Elevated pike push-up",
                "Elevated Pike Push-up",
                (C("Pike Push-up", 3, 12), C("Wall Handstand", 3, hold=30)),
                requires=("wall_hs",),
                xp=60,
            ),
            Step(
                "wall_hspu",
                "Wall handstand push-up",
                "Wall Handstand Push-up",
                (C("Elevated Pike Push-up", 3, 8), C("Wall Handstand Push-up", 1, 1)),
                requires=("elevated_pike",),
                xp=200,
            ),
            Step(
                "free_hspu",
                "Freestanding HSPU",
                "Freestanding Handstand Push-up",
                (
                    C("Wall Handstand Push-up", 3, 5),
                    C("Freestanding Handstand", 3, hold=30),
                    C("Freestanding Handstand Push-up", 1, 1),
                ),
                requires=("wall_hspu", "free_hs"),
                xp=400,
                uncertain=True,
                note="An advanced goal; thresholds are our estimate.",
            ),
        ),
        ("Pike Push-up", "Overhead Press", "Wall Handstand", "Hollow Body Hold"),
        ("BWF", "GMB", "OG"),
    ),
    Skill(
        "pistol",
        "Pistol squat",
        "legs",
        "Single-leg squat to full depth.",
        (
            Step("squat", "Bodyweight squat", "Bodyweight Squat"),
            Step("box", "Box pistol", "Box Pistol Squat", (C("Bodyweight Squat", 3, 20),), xp=40),
            Step(
                "assisted",
                "Assisted pistol",
                "Assisted Pistol Squat",
                (C("Box Pistol Squat", 3, 8, side=True),),
                xp=60,
            ),
            Step(
                "pistol",
                "Pistol squat",
                "Pistol Squat",
                (C("Assisted Pistol Squat", 3, 8, side=True), C("Pistol Squat", 1, 1, side=True)),
                xp=200,
            ),
        ),
        ("Bodyweight Squat", "Bulgarian Split Squat", "Deep Squat Hold", "Back Squat"),
        ("RR", "GMB"),
    ),
    Skill(
        "front_lever",
        "Front lever",
        "levers",
        "Horizontal under the bar, face up.",
        (
            Step("tuck", "Tuck front lever", "Tuck Front Lever", (C("Pull-up", 3, 5),), xp=60),
            Step(
                "adv_tuck",
                "Advanced tuck",
                "Advanced Tuck Front Lever",
                (C("Tuck Front Lever", 3, hold=15),),
                xp=80,
            ),
            Step(
                "one_leg",
                "One-leg",
                "One-leg Front Lever",
                (C("Advanced Tuck Front Lever", 3, hold=15),),
                xp=100,
            ),
            Step(
                "straddle",
                "Straddle",
                "Straddle Front Lever",
                (C("One-leg Front Lever", 3, hold=10),),
                xp=150,
                uncertain=True,
            ),
            Step(
                "full",
                "Full front lever",
                "Front Lever",
                (C("Straddle Front Lever", 3, hold=10), C("Front Lever", 1, hold=5)),
                xp=400,
                uncertain=True,
            ),
        ),
        ("Pull-up", "Inverted Row", "Hanging Leg Raise", "Hollow Body Hold", "Lat Pulldown"),
        ("BWF", "OG"),
    ),
    Skill(
        "back_lever",
        "Back lever",
        "levers",
        "Horizontal under the rings, face down.",
        (
            Step("skin_cat", "Skin the cat", "Skin the Cat"),
            Step("german", "German hang", "German Hang", (C("Skin the Cat", 3, 5),), xp=40),
            Step(
                "tuck", "Tuck back lever", "Tuck Back Lever", (C("German Hang", 3, hold=20),), xp=60
            ),
            Step(
                "adv_tuck",
                "Advanced tuck",
                "Advanced Tuck Back Lever",
                (C("Tuck Back Lever", 3, hold=15),),
                xp=80,
            ),
            Step(
                "straddle",
                "Straddle",
                "Straddle Back Lever",
                (C("Advanced Tuck Back Lever", 3, hold=15),),
                xp=120,
                uncertain=True,
            ),
            Step(
                "full",
                "Full back lever",
                "Back Lever",
                (C("Straddle Back Lever", 3, hold=10), C("Back Lever", 1, hold=5)),
                xp=300,
                uncertain=True,
            ),
        ),
        ("Pull-up", "Chin-up", "Chest Dip", "German Hang"),
        ("BWF", "OG"),
    ),
    Skill(
        "planche",
        "Planche (tuck to straddle)",
        "push",
        "Body held horizontal on straight arms.",
        (
            Step("lean", "Planche lean", "Planche Lean", (C("Push-up", 3, 15),), xp=40),
            Step("frog", "Frog stand", "Frog Stand", (C("Planche Lean", 3, hold=20),), xp=40),
            Step(
                "tuck",
                "Tuck planche",
                "Tuck Planche",
                (C("Frog Stand", 3, hold=30), C("Planche Lean", 3, hold=30)),
                xp=150,
            ),
            Step(
                "adv_tuck",
                "Advanced tuck planche",
                "Advanced Tuck Planche",
                (C("Tuck Planche", 3, hold=15),),
                xp=200,
                uncertain=True,
            ),
            Step(
                "straddle",
                "Straddle planche",
                "Straddle Planche",
                (C("Advanced Tuck Planche", 3, hold=15), C("Straddle Planche", 1, hold=3)),
                xp=500,
                uncertain=True,
                note="A multi-year goal for most people; sources give wide ranges.",
            ),
        ),
        ("Pseudo Planche Push-up", "Planche Lean", "Chest Dip", "Parallel Bar Support Hold"),
        ("BWF", "OG"),
        stretch=True,
    ),
    Skill(
        "human_flag",
        "Human flag",
        "core",
        "Hold the body sideways off a pole. A stretch goal.",
        (
            Step("side_plank", "Side plank", "Side Plank"),
            Step(
                "vertical",
                "Vertical flag",
                "Vertical Flag",
                (C("Side Plank", 3, hold=45), C("Pull-up", 3, 8)),
                xp=60,
                uncertain=True,
            ),
            Step(
                "tuck",
                "Tuck flag",
                "Tuck Human Flag",
                (C("Vertical Flag", 3, hold=15),),
                xp=120,
                uncertain=True,
            ),
            Step(
                "straddle",
                "Straddle flag",
                "Straddle Human Flag",
                (C("Tuck Human Flag", 3, hold=10),),
                xp=200,
                uncertain=True,
            ),
            Step(
                "full",
                "Human flag",
                "Human Flag",
                (C("Straddle Human Flag", 3, hold=5), C("Human Flag", 1, hold=3)),
                xp=400,
                uncertain=True,
            ),
        ),
        ("Side Plank", "Pull-up", "Overhead Press", "Russian Twist"),
        ("BWF",),
        stretch=True,
    ),
    Skill(
        "nordic_curl",
        "Nordic curl",
        "legs",
        "Eccentric hamstring strength, kind to sprinters' knees.",
        (
            Step("bridge", "Single-leg glute bridge", "Single-leg Glute Bridge"),
            Step(
                "negative",
                "Nordic negative",
                "Nordic Curl Negative",
                (C("Single-leg Glute Bridge", 3, 12, side=True),),
                xp=60,
            ),
            Step(
                "nordic",
                "Nordic curl",
                "Nordic Curl",
                (C("Nordic Curl Negative", 3, 6), C("Nordic Curl", 1, 1)),
                xp=200,
            ),
            Step(
                "nordic_3x5",
                "Nordic curl 3\u00d75",
                "Nordic Curl",
                (C("Nordic Curl", 3, 5),),
                xp=250,
            ),
        ),
        ("Romanian Deadlift", "Leg Curl", "Single-leg Glute Bridge", "Back Extension"),
        ("NHE", "RR"),
    ),
    Skill(
        "dragon_flag",
        "Dragon flag",
        "core",
        "A rigid body lowered from the shoulders.",
        (
            Step("leg_raise", "Lying leg raise", "Lying Leg Raise"),
            Step(
                "tuck_neg",
                "Tuck negative",
                "Tuck Dragon Flag Negative",
                (C("Lying Leg Raise", 3, 12), C("Hollow Body Hold", 3, hold=30)),
                xp=60,
            ),
            Step(
                "negative",
                "Dragon flag negative",
                "Dragon Flag Negative",
                (C("Tuck Dragon Flag Negative", 3, 6),),
                xp=100,
            ),
            Step(
                "flag",
                "Dragon flag",
                "Dragon Flag",
                (C("Dragon Flag Negative", 3, 5), C("Dragon Flag", 1, 1)),
                xp=250,
                uncertain=True,
            ),
        ),
        ("Hanging Leg Raise", "Hollow Body Hold", "Plank", "Lying Leg Raise"),
        ("BWF", "OG"),
    ),
)

SKILL_BY_KEY: dict[str, Skill] = {s.key: s for s in SKILLS}

# Holds longer than this (seconds) on these exercises are not believed for skill progress:
# they would be far beyond published records/standards, so they are ignored and flagged.
ELITE_HOLDS = {
    "Front Lever", "Straddle Front Lever", "One-leg Front Lever", "Back Lever",
    "Straddle Back Lever", "Straddle Planche", "Advanced Tuck Planche", "Human Flag",
    "Straddle Human Flag", "V-sit",
}  # fmt: skip
MAX_ELITE_HOLD_S = 120
MAX_HOLD_S = 600


def all_exercise_names() -> set[str]:
    names: set[str] = set()
    for s in SKILLS:
        names.update(s.feeders)
        for step in s.steps:
            names.add(step.exercise)
            names.update(c.exercise for c in step.unlock)
    return names


def plausible_hold_limit(exercise: str) -> int:
    return MAX_ELITE_HOLD_S if exercise in ELITE_HOLDS else MAX_HOLD_S
