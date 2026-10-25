"""goalcheck-v1: deterministic checks that flag unrealistic or unsafe goals and plans.

The planner (and the trainer, when you ask "can I lose 10 kg in a month?") runs these
before anything is generated. Each flag carries its numbers, so the trainer can explain
it word for word and the local model, if it rephrases it, is held to the same numbers by
the coach's number guard.

Sources (docs/architecture/trainer-and-planner.md has the links):
  - weight loss ~0.5-1 % of body weight a week keeps muscle (Helms, Aragon & Fitschen 2014)
  - weight gain ~0.25-0.5 %/week for novice/intermediate lifters (Iraki et al. 2019)
  - protein 1.4-2.0 g/kg/day for people who train (ISSN position stand, Jaeger et al. 2017)
  - calorie floor: low-calorie diets of ~1,200 (women) / ~1,500 (men) kcal are the usual
    unsupervised lower bound; we also never go below the estimated BMR
  - ICMR-NIN Dietary Guidelines for Indians 2024: ~0.5 kg/week loss considered safe,
    reducing diets >= 1,000 kcal/day, protein RDA 0.83 g/kg; no deficit plans under 18
These are ASCEND's thresholds, informed by those sources; they are not medical advice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ALGO_VERSION = "goalcheck-v2"

Severity = Literal["info", "warn", "block"]
Experience = Literal["beginner", "intermediate", "advanced"]

LOSS_WARN_PCT = 0.75  # % body weight per week
LOSS_MAX_PCT = 1.0
GAIN_MAX_PCT = 0.5
GAIN_BLOCK_PCT = 1.0
SAFE_LOSS_PCT = 0.75  # the pace used to suggest a realistic timeline
SAFE_GAIN_PCT = 0.35
PROTEIN_LOW_G_PER_KG = 1.4
PROTEIN_HIGH_G_PER_KG = 3.0
KCAL_FLOOR = {"female": 1200, "male": 1500}
MIN_BMI = 18.5
# ICMR-NIN Dietary Guidelines for Indians (2024): about 0.5 kg a week is considered safe,
# reducing diets should not go below about 1,000 kcal a day (our floor above is stricter),
# and the protein RDA for adults is 0.83 g per kg (food first, no supplement advice).
ICMR_SAFE_LOSS_KG_WEEK = 0.5
ICMR_REDUCING_DIET_MIN_KCAL = 1000
PROTEIN_RDA_G_PER_KG = 0.83
ADULT_AGE = 18
# Best realistic weekly e1RM gain (% per week) by training age; twice this is impossible.
STRENGTH_PCT_PER_WEEK: dict[str, float] = {"beginner": 2.5, "intermediate": 1.0, "advanced": 0.5}


@dataclass(frozen=True)
class Flag:
    code: str
    severity: Severity
    message: str
    numbers: dict[str, float] = field(default_factory=dict)


def _r(x: float, n: int = 1) -> float:
    return round(x, n)


# v1.2: someone below a healthy BMI regains weight faster than a lean lifter adds muscle;
# about 0.25-0.5 kg a week is the usual guidance for a healthy catch-up gain, so the plan
# uses 0.4 kg a week (warn above 0.75, block above 1 kg a week).
UNDERWEIGHT_SAFE_GAIN_KG_WEEK = 0.4
UNDERWEIGHT_GAIN_WARN_KG_WEEK = 0.75
UNDERWEIGHT_GAIN_BLOCK_KG_WEEK = 1.0


def is_underweight(weight_kg: float, height_cm: float | None) -> bool:
    return bool(height_cm) and weight_kg / (height_cm / 100) ** 2 < MIN_BMI  # type: ignore[operator]


def safe_weeks(weight_kg: float, target_kg: float, height_cm: float | None = None) -> int:
    """Weeks to reach the target at a sustainable pace (0.75 %/wk down, 0.35 %/wk up, or
    0.4 kg/wk up from an underweight start)."""
    diff = target_kg - weight_kg
    if abs(diff) < 0.05:
        return 0
    if diff > 0 and is_underweight(weight_kg, height_cm):
        per_week = UNDERWEIGHT_SAFE_GAIN_KG_WEEK
    else:
        pct = SAFE_LOSS_PCT if diff < 0 else SAFE_GAIN_PCT
        per_week = weight_kg * pct / 100
    return max(1, round(abs(diff) / per_week))


def check_weight_goal(
    weight_kg: float, target_kg: float, weeks: float, height_cm: float | None = None
) -> list[Flag]:
    """Is going from weight_kg to target_kg in `weeks` weeks realistic?"""
    flags: list[Flag] = []
    if height_cm:
        bmi = target_kg / (height_cm / 100) ** 2
        # v1.3: an underweight user gaining toward a healthy BMI is the goal, not a risk;
        # only a target BELOW the current weight (a loss) is blocked here.
        if bmi < MIN_BMI and target_kg < weight_kg:
            flags.append(
                Flag(
                    "underweight_target",
                    "block",
                    f"A target of {_r(target_kg)} kg at {_r(height_cm, 0):g} cm is a BMI of "
                    f"{_r(bmi)}, below {MIN_BMI}. I won't plan for an underweight target.",
                    {"target_kg": _r(target_kg), "bmi": _r(bmi)},
                )
            )
    if weeks <= 0:
        return flags
    diff = target_kg - weight_kg
    if abs(diff) < 0.05:
        return flags
    rate = diff / weeks
    pct = rate / weight_kg * 100
    nums = {
        "kg_per_week": _r(abs(rate), 2),
        "pct_per_week": _r(abs(pct), 2),
        "weeks": _r(weeks),
        "safe_weeks": float(safe_weeks(weight_kg, target_kg, height_cm)),
    }
    realistic = int(nums["safe_weeks"])
    if diff > 0 and is_underweight(weight_kg, height_cm):
        return flags + _underweight_gain_flags(diff, weeks, abs(rate), realistic, nums)
    if diff < 0 and abs(pct) > LOSS_MAX_PCT:
        flags.append(
            Flag(
                "loss_too_fast",
                "block",
                f"Losing {_r(abs(diff))} kg in {_r(weeks):g} weeks is {nums['kg_per_week']} kg "
                f"a week ({nums['pct_per_week']}% of your body weight). Above about 1% a week "
                f"you lose muscle with the fat. A pace you can hold gets you there in about "
                f"{realistic} weeks.",
                nums,
            )
        )
    elif diff < 0 and abs(pct) > LOSS_WARN_PCT:
        flags.append(
            Flag(
                "loss_aggressive",
                "warn",
                f"{nums['kg_per_week']} kg a week ({nums['pct_per_week']}% of body weight) is "
                f"doable but hard. Keep protein high and expect hungry weeks; about "
                f"{realistic} weeks is the comfortable version.",
                nums,
            )
        )
    elif diff < 0 and abs(rate) > ICMR_SAFE_LOSS_KG_WEEK:
        flags.append(
            Flag(
                "loss_above_icmr",
                "info",
                f"{nums['kg_per_week']} kg a week is within the 1% range, but India's dietary "
                f"guidelines (ICMR-NIN 2024) call about {ICMR_SAFE_LOSS_KG_WEEK} kg a week safe. "
                f"Slower is gentler.",
                {**nums, "icmr_kg_per_week": ICMR_SAFE_LOSS_KG_WEEK},
            )
        )
    elif diff > 0 and pct > GAIN_BLOCK_PCT:
        flags.append(
            Flag(
                "gain_too_fast",
                "block",
                f"Gaining {_r(diff)} kg in {_r(weeks):g} weeks is {nums['kg_per_week']} kg a "
                f"week. Muscle doesn't grow that fast; most of it would be fat. Plan on about "
                f"{realistic} weeks.",
                nums,
            )
        )
    elif diff > 0 and pct > GAIN_MAX_PCT:
        flags.append(
            Flag(
                "gain_fast",
                "warn",
                f"{nums['kg_per_week']} kg a week ({nums['pct_per_week']}% of body weight) is "
                f"faster than lean gains usually go (0.25-0.5% a week). About {realistic} "
                f"weeks keeps fat gain down.",
                nums,
            )
        )
    return flags


def kcal_floor(sex: str, bmr: float) -> int:
    return int(max(KCAL_FLOOR.get(sex, 1500), round(bmr)))


def check_calories(kcal: float, sex: str, bmr: float) -> list[Flag]:
    floor = kcal_floor(sex, bmr)
    if kcal < floor:
        return [
            Flag(
                "kcal_below_floor",
                "block",
                f"{round(kcal)} kcal a day is below your floor of {floor} kcal (the higher of "
                f"your estimated BMR and {KCAL_FLOOR.get(sex, 1500)} kcal). Going lower needs "
                f"a doctor, not an app.",
                {"kcal": float(round(kcal)), "floor": float(floor)},
            )
        ]
    return []


def check_age(age: int | None, deficit: bool) -> list[Flag]:
    """No calorie-deficit plans for under-18s: growing bodies need maintenance energy."""
    if age is None or age >= ADULT_AGE or not deficit:
        return []
    return [
        Flag(
            "under_18_no_deficit",
            "block",
            f"At {age}, I won't plan a calorie deficit; you are still growing. I'll plan at "
            f"maintenance and focus on training, sleep and protein. Talk to a doctor or a "
            f"dietitian about weight.",
            {"age": float(age)},
        )
    ]


def check_protein(protein_g: float, weight_kg: float) -> list[Flag]:
    per_kg = protein_g / weight_kg
    nums = {"protein_g": float(round(protein_g)), "g_per_kg": _r(per_kg)}
    if per_kg < PROTEIN_RDA_G_PER_KG:
        return [
            Flag(
                "protein_below_rda",
                "warn",
                f"{round(protein_g)} g of protein is {_r(per_kg)} g per kg, below the "
                f"{PROTEIN_RDA_G_PER_KG} g per kg everyone needs (ICMR-NIN 2024). Add dal, "
                f"paneer, curd, eggs or chicken before anything else.",
                nums,
            )
        ]
    if per_kg < PROTEIN_LOW_G_PER_KG:
        return [
            Flag(
                "protein_low",
                "warn",
                f"{round(protein_g)} g of protein is {_r(per_kg)} g per kg; people who train "
                f"do best at 1.4-2.0 g per kg.",
                nums,
            )
        ]
    if per_kg > PROTEIN_HIGH_G_PER_KG:
        return [
            Flag(
                "protein_very_high",
                "info",
                f"{round(protein_g)} g ({_r(per_kg)} g per kg) is more protein than you need; "
                f"above about 2 g per kg the extra does little.",
                nums,
            )
        ]
    return []


def _underweight_gain_flags(
    diff: float, weeks: float, rate: float, realistic: int, nums: dict[str, float]
) -> list[Flag]:
    """Gaining from an underweight start: a healthy catch-up gain, not a lean bulk."""
    if rate > UNDERWEIGHT_GAIN_BLOCK_KG_WEEK:
        return [
            Flag(
                "gain_too_fast",
                "block",
                f"Gaining {_r(diff)} kg in {_r(weeks):g} weeks is {nums['kg_per_week']} kg a "
                f"week, more than your body can build well. About {realistic} weeks at "
                f"{UNDERWEIGHT_SAFE_GAIN_KG_WEEK} kg a week is a strong, steady pace.",
                nums,
            )
        ]
    if rate > UNDERWEIGHT_GAIN_WARN_KG_WEEK:
        return [
            Flag(
                "gain_fast",
                "warn",
                f"{nums['kg_per_week']} kg a week is quick. It can work early on; about "
                f"{realistic} weeks is the comfortable version. Eat a little more each week "
                "and keep training.",
                nums,
            )
        ]
    return [
        Flag(
            "gain_on_track",
            "info",
            f"{nums['kg_per_week']} kg a week is a healthy pace for you. About {realistic} weeks "
            "at a steady pace; eat regular meals with protein in each and train 3 days a week.",
            nums,
        )
    ]


def check_schedule(days_per_week: int, minutes: int, experience: Experience) -> list[Flag]:
    flags: list[Flag] = []
    if days_per_week >= 7:
        flags.append(
            Flag(
                "no_rest_day",
                "warn",
                "Seven training days leaves no rest day. Muscles grow between sessions; "
                "I'll plan 6 and keep one day for rest.",
                {"days": float(days_per_week)},
            )
        )
    elif experience == "beginner" and days_per_week > 5:
        flags.append(
            Flag(
                "beginner_too_many_days",
                "warn",
                f"{days_per_week} days a week is a lot for a beginner; 3-4 full-body days build "
                f"the habit and recover better.",
                {"days": float(days_per_week)},
            )
        )
    if minutes < 20:
        flags.append(
            Flag(
                "short_sessions",
                "info",
                f"{minutes} minutes fits 2-3 exercises. That still counts; I'll keep it tight.",
                {"minutes": float(minutes)},
            )
        )
    elif minutes > 120:
        flags.append(
            Flag(
                "long_sessions",
                "warn",
                f"{minutes} minutes is long; past about 90 minutes quality drops. I'll cap the "
                f"plan at 90.",
                {"minutes": float(minutes)},
            )
        )
    return flags


def check_strength_goal(
    current_kg: float, target_kg: float, weeks: float, experience: Experience
) -> list[Flag]:
    """Is lifting target_kg (estimated 1RM) in `weeks` weeks plausible from current_kg?"""
    if weeks <= 0 or current_kg <= 0 or target_kg <= current_kg:
        return []
    pct = ((target_kg / current_kg) - 1) * 100 / weeks
    limit = STRENGTH_PCT_PER_WEEK[experience]
    realistic = math_ceil((target_kg / current_kg - 1) * 100 / limit)
    nums = {"pct_per_week": _r(pct, 2), "limit_pct": limit, "realistic_weeks": float(realistic)}
    if pct > 2 * limit:
        return [
            Flag(
                "strength_unrealistic",
                "block",
                f"Going from {_r(current_kg)} to {_r(target_kg)} kg in {_r(weeks):g} weeks "
                f"needs {nums['pct_per_week']}% a week; a {experience} lifter gains about "
                f"{limit}% at best. Give it about {realistic} weeks.",
                nums,
            )
        ]
    if pct > limit:
        return [
            Flag(
                "strength_ambitious",
                "warn",
                f"{nums['pct_per_week']}% a week is ambitious for a {experience} lifter "
                f"(about {limit}% is typical). Possible, but about {realistic} weeks is safer.",
                nums,
            )
        ]
    return []


def math_ceil(x: float) -> int:
    i = int(x)
    return i if i == x else i + 1


def worst(flags: list[Flag]) -> Severity | None:
    order = {"info": 0, "warn": 1, "block": 2}
    return max((f.severity for f in flags), key=lambda s: order[s], default=None)
