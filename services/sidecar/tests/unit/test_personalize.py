from dataclasses import replace
from datetime import date

from app.modules.gamification.quests import Tuning, generate_daily_quest
from app.modules.progress.muscle_load import compute_states
from app.modules.selector.personalize import personalize
from app.modules.selector.state import PlayerState, StrengthRatios

DAY = date(2026, 10, 23)


def state(**over) -> PlayerState:
    base = PlayerState(
        level="intermediate",
        game_level=5,
        age=21,
        training_weeks=30,
        sets_per_week=40,
        ratios=StrengthRatios(None, None, None),
        load={"push": 1.0, "pull": 0.3, "legs": 0.9, "core": 0.8, "cardio": 1.0,
              "calisthenics": 1.0},
        readiness=80,
        readiness_source="checkin",
        streak=3,
        days_since_workout=1,
        sessions_14d=6,
        planned_per_week=3,
        kcal_ratio=1.0,
        protein_ratio=1.0,
        meal_days_7d=6,
        goal="bulk",
        weight_trend_kg_week=0.2,
        trend_matches_goal=True,
    )  # fmt: skip
    return replace(base, **over)


def test_levels_set_the_range_and_reasons_say_why():
    p = personalize(state(level="beginner"))
    assert (p.tuning.sets_min, p.tuning.sets_max) == (2, 3)
    assert "Form first" in p.tuning.note
    assert any("beginner" in r for r in p.reasons)
    p = personalize(state(level="expert"))
    assert (p.tuning.sets_min, p.tuning.sets_max) == (3, 6)
    assert p.focus == "pull" and any("pulling" in r for r in p.reasons)


def test_low_readiness_and_a_long_break_lower_the_ceiling():
    p = personalize(state(readiness=30, days_since_workout=8))
    assert p.tuning.sets_max == 3 and p.tone == "gentle"


def test_nutrition_item_follows_the_gap():
    assert personalize(state(meal_days_7d=1)).tuning.nutrition == "meals"
    assert personalize(state(protein_ratio=0.5)).tuning.nutrition == "protein"
    assert personalize(state()).tuning.nutrition is None


def test_minors_are_named_in_the_reasons():
    assert any("Under 18" in r for r in personalize(state(age=16)).reasons)


def test_tuning_shapes_the_quest():
    states = compute_states([], __import__("datetime").datetime(2026, 10, 23, 9))
    from tests.unit.test_quests import EXERCISES

    plain = generate_daily_quest(DAY, states, EXERCISES, 120)
    tuned = generate_daily_quest(
        DAY, states, EXERCISES, 120, tuning=Tuning(2, 3, "meals", "Form first.")
    )
    assert tuned[0].target <= 3 and tuned[0].detail.endswith("Form first.")
    assert tuned[1].code == "log_meals"
    protein = generate_daily_quest(DAY, states, EXERCISES, 120, tuning=Tuning(nutrition="protein"))
    assert protein[1].code == "protein"
    assert plain[0].code == tuned[0].code
