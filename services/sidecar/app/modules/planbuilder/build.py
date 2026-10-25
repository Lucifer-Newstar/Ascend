"""Build a week from the plan facts (planbuilder-v1).

Strength days (calisthenics plus the dumbbells you own, sized to their weights), skill days
for a sport you mix in (form first after a long break), at least two rest days, and food
targets. The result is a planner ProgramDraft, so it is saved and followed like any plan
built on the Planner, and the training days go into your schedule.

Rules:
- 2 to 5 training days, so at least two rest days. With a sport: skill days on Tuesday and
  Saturday (Navin, 2026-10-25), strength on the other picked days.
- After a break of a year or more, skill days start as a beginner: footwork, shadow rounds,
  kicks at waist height for 2-3 weeks, bag rounds at about 60% power.
- Dumbbells: the heaviest one goes to squats (held at the chest) and rows, a matching pair
  to floor press, curls and deadlifts. No bench, no bench press (floor press instead).
- Food: protein 1.6-2 g per kg; a gain goal adds 300-500 kcal a day (calorie numbers hidden
  under 18 or with "hide calories"); "can't eat much but can drink" gets a shake (no oats),
  ramping from one to three a day over three weeks.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from app.modules.planbuilder.facts import SPORT_LABEL, PlanFacts
from app.modules.planner.schemas import DayIO, ProgramDraft, SlotIO

WEEKDAY = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
SKILL_DAYS = {1: (), 2: (3,), 3: (5,), 4: (1, 5), 5: (1, 5)}
STRENGTH_DAYS_WITH_SKILL = {2: (0,), 3: (0, 3), 4: (0, 3), 5: (0, 2, 4)}
STRENGTH_DAYS = {2: (0, 3), 3: (0, 2, 4), 4: (0, 1, 3, 4), 5: (0, 1, 2, 4, 5)}
SHAKE = "300 ml full-fat milk, 1-2 bananas or 3-4 dates, 2 tbsp peanut butter, 1 scoop whey"
KICK_SPORTS = {"kickboxing", "muay_thai", "taekwondo", "karate", "mma"}


@dataclass
class Person:
    weight_kg: float | None = None
    age: int | None = None
    equipment: list[str] = field(default_factory=list)
    pushups: int | None = None
    pullups: int | None = None
    plank_s: int | None = None
    sessions_per_week: int = 3
    hide_calories: bool = False
    # The profile's goal is "bulk" or its target weight is above the current weight.
    gaining: bool = False


@dataclass
class Built:
    draft: ProgramDraft
    weekdays: list[int]
    week_line: str
    food: list[str]
    notes: list[str]


def _slot(ex: str, sets: int, lo: int, hi: int, rest: int = 90, hold: bool = False) -> SlotIO:
    return SlotIO(
        exercise=ex,
        sets=sets,
        rep_low=lo,
        rep_high=max(lo, hi),
        measure="hold" if hold else "reps",
        target_rpe=7.0,
        rest_s=rest,
    )


def _from_best(best: int | None, default: tuple[int, int]) -> tuple[int, int]:
    """About half to two thirds of a max set, so every set ends with reps in reserve."""
    if not best:
        return default
    lo = max(3, round(best * 0.5))
    return lo, min(25, max(lo + 2, round(best * 0.7)))


def _push(p: Person) -> SlotIO:
    best = p.pushups
    if best is not None and best < 5:
        return _slot("Incline Push-up", 3, 6, 10)
    if best is not None and best >= 25:
        return _slot("Diamond Push-up", 3, *_from_best(best // 2, (8, 12)))
    return _slot("Push-up", 3, *_from_best(best, (6, 10)))


def _dumbbells(weights: list[float]) -> tuple[float | None, float | None]:
    """(the heaviest single, a weight you have at least two of)."""
    if not weights:
        return None, None
    pair = [w for w, n in Counter(weights).items() if n >= 2]
    return max(weights), (max(pair) if pair else None)


def _strength_days(f: PlanFacts, p: Person, per_day: int) -> tuple[list[DayIO], list[str]]:
    kit = set(p.equipment)
    bar = bool(kit & {"pullup_bar", "rings", "gym"})
    heavy, pair = _dumbbells(f.dumbbells_kg)
    notes: list[str] = []
    a: list[SlotIO] = [_push(p)]
    b: list[SlotIO] = [_slot("Pike Push-up", 3, 5, 8)]
    if bar:
        pull = p.pullups or 0
        a.append(
            _slot("Negative Pull-up", 3, 3, 5, 120)
            if pull < 3
            else _slot("Pull-up", 3, *_from_best(pull, (3, 6)), rest=120)
        )
        b.append(_slot("Inverted Row", 3, 8, 12))
    elif heavy:
        a.append(_slot("One-arm Dumbbell Row", 3, 10, 15))
        b.append(_slot("One-arm Dumbbell Row", 3, 10, 15))
    else:
        a.append(_slot("Inverted Row", 3, 6, 10))
        b.append(_slot("Inverted Row", 3, 6, 10))
    if heavy and heavy >= 6:
        a.append(_slot("Dumbbell Squat", 3, 10, 15))
        notes.append(f"Squats (held at your chest) and rows: the {heavy:g} kg dumbbell.")
    else:
        a.append(_slot("Bodyweight Squat", 3, 12, 20, 60))
    b.append(_slot("Bulgarian Split Squat", 3, 8, 12))
    if pair:
        floor = "Dumbbell Bench Press" if "bench" in kit or "gym" in kit else "Dumbbell Floor Press"
        a.append(_slot(floor, 3, 10, 15))
        b.append(_slot("Stiff-Legged Dumbbell Deadlift", 3, 10, 15))
        b.append(_slot("Hammer Curl", 2, 10, 15, 60))
        notes.append(f"Floor press, deadlifts and curls: the two {pair:g} kg dumbbells.")
    plank_lo, plank_hi = _from_best(p.plank_s, (20, 30))
    a.append(_slot("Plank", 2, max(15, plank_lo), max(20, plank_hi), 60, hold=True))
    b.append(
        _slot("Hanging Leg Raise", 2, 6, 10, 60)
        if bar
        else _slot("Side Plank", 2, 15, 30, 60, hold=True)
    )
    days = [
        DayIO(key="A", name="Strength A", focus="Full body: push, pull, legs", weekday=0,
              slots=a[:per_day]),
        DayIO(key="B", name="Strength B", focus="Full body: shoulders, back, legs", weekday=0,
              slots=b[:per_day]),
    ]  # fmt: skip
    return days, notes


def _skill_day(f: PlanFacts, p: Person, per_day: int) -> tuple[DayIO, list[str]]:
    sports = set(f.sports)
    kicks = bool(sports & KICK_SPORTS)
    fresh = f.sports_years_ago is None or f.sports_years_ago >= 1
    rounds = (2, 3) if fresh else (3, 3)
    # In order of what matters most; the session length trims from the end.
    slots = [_slot("Boxing Footwork Drill", 2, 2, 3, 60)]
    if kicks:
        slots.append(_slot("Kickboxing Shadow Rounds", 3, *rounds, rest=60))
        slots.append(_slot("Roundhouse Kick Drill", 2, 2, 3, 60))
    else:
        slots.append(_slot("Jab-Cross Shadow Drill", 3, *rounds, rest=60))
    if "punching_bag" in f.kit:
        slots.append(_slot("Heavy Bag Combos", 3, 2, 2, 60))
    slots.append(
        _slot("Teep Push Kick Drill", 2, 2, 3, 60)
        if kicks
        else _slot("Slip and Roll Drill", 2, 2, 3, 60)
    )
    slots.append(_slot("Fighter Core Circuit", 1, 6, 10, 0))
    names = [SPORT_LABEL[s] for s in f.sports] or ["Striking"]
    notes: list[str] = []
    if fresh:
        notes.append(
            "Skill days: form first. Kicks at waist height for the first 2-3 weeks, "
            "light power, and stop a round early if your form slips."
        )
    if "punching_bag" in f.kit:
        wrap = " with your hands wrapped" if "hand_wraps" in f.kit else ""
        notes.append(f"Bag rounds at about 60% power{wrap}.")
    if "gripper" in f.kit:
        notes.append("Gripper: 3 × 10 each hand after a skill day.")
    day = DayIO(key="S", name="Skill: " + " + ".join(names)[:50], focus="Footwork, shadow "
                "rounds, technique", weekday=0, slots=slots[: max(per_day, 5)])  # fmt: skip
    return day, notes


def _food(f: PlanFacts, p: Person, skill_days: int) -> list[str]:
    w = f.weight_kg or p.weight_kg
    out: list[str] = []
    if w:
        out.append(f"Protein: about {round(1.6 * w)}-{round(2.0 * w)} g a day (1.6-2 g per kg).")
    gaining = f.goal in ("gain_weight", "gain_muscle") or (
        f.target_weight_kg is not None and w is not None and f.target_weight_kg > w
    )
    gaining = gaining or (f.goal is None and p.gaining)
    numbers = not p.hide_calories and (p.age is None or p.age >= 18)
    if gaining:
        out.append(
            "Eat about 300-500 kcal a day more than now, for +0.25-0.5 kg a week."
            if numbers
            else "Eat a little more than now, every day, for +0.25-0.5 kg a week."
        )
    elif f.goal == "lose_fat":
        out.append(
            "A small deficit, about 300-500 kcal a day, for -0.25-0.75 kg a week."
            if numbers
            else "Slightly smaller portions, for -0.25-0.75 kg a week; never skip meals."
        )
    if f.liquid_calories:
        kcal = " (about 600 kcal)" if numbers else ""
        out.append(f"Shake{kcal}: {SHAKE}.")
        extra = " On skill days add one more." if skill_days else ""
        out.append(
            f"Week 1: one shake a day; week 2: two; week 3: up to three if they sit well.{extra}"
        )
    return out


def build(f: PlanFacts, p: Person, minutes_per_day: int | None = None) -> Built:
    from app.modules.planner.workout_gen import exercises_per_day

    days = min(5, max(2, f.days_per_week or p.sessions_per_week or 3))
    per_day = exercises_per_day(f.session_minutes or minutes_per_day or 45)
    strength, notes = _strength_days(f, p, max(3, per_day))
    plan_days: list[DayIO] = []
    skill: DayIO | None = None
    if f.sports or "punching_bag" in f.kit:
        skill, skill_notes = _skill_day(f, p, per_day)
        notes += skill_notes
        s_days, k_days = STRENGTH_DAYS_WITH_SKILL[days], SKILL_DAYS[days]
    else:
        s_days, k_days = STRENGTH_DAYS[days], ()
    for i, wd in enumerate(s_days):
        base = strength[i % 2]
        plan_days.append(base.model_copy(update={"key": f"{base.key}{i + 1}", "weekday": wd}))
    for i, wd in enumerate(k_days):
        assert skill is not None
        plan_days.append(skill.model_copy(update={"key": f"S{i + 1}", "weekday": wd}))
    plan_days.sort(key=lambda d: d.weekday)
    by_day = {d.weekday: d.name for d in plan_days}
    week_line = " · ".join(f"{WEEKDAY[i]} {by_day.get(i, 'rest')}" for i in range(7))
    food = _food(f, p, len(k_days))
    summary = (
        f"{days} days a week: {len(s_days)} strength"
        + (f", {len(k_days)} skill" if k_days else "")
        + f", {7 - days} rest. Built from what you told your trainer."
    )
    draft = ProgramDraft(
        name="My plan",
        summary=summary,
        level="beginner",
        equipment="dumbbells" if f.dumbbells_kg else "bodyweight",
        days=plan_days,
        notes=(notes + food)[:10],
    )
    return Built(draft, sorted(by_day), week_line, food, notes)
