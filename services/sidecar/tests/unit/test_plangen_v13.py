"""plangen fixes in v1.3 (the five bugs Navin hit on v1.2.0)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.modules.planner import workout_gen as wg
from app.modules.workouts import equipment

HOLDS = {"Plank", "Side Plank", "Dead Hang", "Hollow Body Hold"}


def _plan(choices: list[str], lib: set[str], **kw: object) -> wg.GeneratedProgram:
    allowed = equipment.allowed_equipment(choices)
    gear = {
        "Pull-up": "bar", "Chin-up": "bar", "Negative Pull-up": "bar", "Inverted Row": "bar",
        "Hanging Leg Raise": "bar", "Dead Hang": "bar", "Dumbbell Bench Press": "dumbbell",
        "Incline Dumbbell Press": "dumbbell", "Dumbbell Floor Press": "dumbbell",
        "Lateral Raise": "dumbbell", "Rear Delt Fly": "dumbbell",
        "One-arm Dumbbell Row": "dumbbell",
        "Hammer Curl": "dumbbell", "Goblet Squat": "dumbbell",
        "Seated Dumbbell Shoulder Press": "dumbbell",
    }  # fmt: skip
    args: dict = {
        "focus": "muscle", "experience": "beginner", "equipment": choices, "days_per_week": 5,
        "minutes": 60,
        "available": lambda n: n in lib
        and equipment.fits_exercise(n, gear.get(n, "bodyweight"), allowed),
        "is_hold": lambda n: n in HOLDS,
    }  # fmt: skip
    args.update(kw)
    return wg.generate(**args)


LIB = {
    "Pull-up", "Chin-up", "Negative Pull-up", "Inverted Row", "Push-up", "Diamond Push-up",
    "Pike Push-up", "Plank", "Dead Hang", "Hanging Leg Raise", "Bodyweight Squat",
    "Single-leg Glute Bridge", "Bodyweight Walking Lunge", "Dumbbell Bench Press",
    "Incline Dumbbell Press", "Dumbbell Floor Press", "Lateral Raise", "Rear Delt Fly",
    "One-arm Dumbbell Row", "Hammer Curl", "Goblet Squat", "Seated Dumbbell Shoulder Press",
    "Superman", "Hollow Body Hold",
}  # fmt: skip


def names(p: wg.GeneratedProgram) -> set[str]:
    return {s.exercise for d in p.days for s in d.slots}


def test_rings_count_as_a_bar_for_pull_ups() -> None:
    assert "Pull-up" in names(_plan(["rings"], LIB))
    assert "Pull-up" not in names(_plan(["none"], LIB))


def test_bench_lifts_need_a_bench() -> None:
    no_bench = names(_plan(["dumbbells"], LIB))
    assert "Dumbbell Bench Press" not in no_bench and "Incline Dumbbell Press" not in no_bench
    assert "Dumbbell Floor Press" in no_bench
    assert "Dumbbell Bench Press" in names(_plan(["dumbbells", "bench"], LIB))
    assert equipment.needs_bench("Barbell Bench Press") and not equipment.needs_bench("Bench Dips")


def test_push_ups_are_dosed_from_the_baseline() -> None:
    p = _plan(["none"], LIB, capacity={"pushups": 15})
    push = next(s for d in p.days for s in d.slots if s.exercise == "Push-up")
    assert (push.rep_low, push.rep_high) == (9, 12)


def test_holds_are_dosed_in_seconds_from_the_baseline() -> None:
    p = _plan(["none"], LIB - {"Hollow Body Hold"}, capacity={"plank_s": 60}, days_per_week=3)
    plank = next(s for d in p.days for s in d.slots if s.exercise == "Plank")
    assert (plank.rep_low, plank.rep_high) == (35, 50)
    assert wg.hold_dose("Hollow Body Hold", "beginner", {"plank_s": 60}) == (20, 30)


def test_no_lateral_raise_stands_in_on_pull_day() -> None:
    p = _plan(["dumbbells"], LIB)  # no bar: the vertical pull slot stays empty
    pull = next(d for d in p.days if d.name.startswith("Pull"))
    assert "Lateral Raise" not in {s.exercise for s in pull.slots}


def test_swap_for_kit_keeps_the_slot() -> None:
    ok = {"Dumbbell Bench Press", "Push-up"}.__contains__
    assert wg.swap_for_kit("Barbell Bench Press", ok) == "Dumbbell Bench Press"
    assert wg.swap_for_kit("Barbell Row", {"Inverted Row"}.__contains__) == "Inverted Row"
    assert wg.swap_for_kit("Zercher Hold", ok) is None


def test_the_profile_accepts_bench(client: TestClient) -> None:
    r = client.put(
        "/profile",
        json={"name": "N", "age": 21, "sex": "male", "height_cm": 170, "weight_kg": 60,
              "goal": "bulk", "activity": "moderate", "equipment": ["dumbbells", "bench"]},
    )  # fmt: skip
    assert r.status_code == 200 and set(r.json()["equipment"]) == {"dumbbells", "bench"}
