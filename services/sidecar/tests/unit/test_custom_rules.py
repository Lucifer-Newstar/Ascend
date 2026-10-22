import pytest

from app.modules.workouts.custom import apply_ai, rules_proposal


@pytest.mark.parametrize(
    ("name", "equipment", "section", "measure", "primary"),
    [
        ("Incline Dumbbell Fly", "dumbbell", "gym", "reps", "pec_major_clavicular"),
        ("Archer Pull-up", "bodyweight", "calisthenics", "reps", "latissimus_dorsi"),
        ("Copenhagen Plank", "bodyweight", "calisthenics", "hold", "adductor_longus"),
        ("Kettlebell Romanian Deadlift", "kettlebell", "gym", "reps", "biceps_femoris"),
        ("Hill Sprints", "none", "cardio", "time", None),
        ("Box Breathing 4-4-4-4", "none", "meditation", "time", None),
        ("Cable Lateral Raise", "cable", "gym", "reps", "deltoid_lateral"),
    ],
)
def test_rules(name, equipment, section, measure, primary):
    p = rules_proposal(name)
    v = p.values
    assert (v["equipment"], v["section"], v["measure"]) == (equipment, section, measure)
    if primary:
        assert v["muscles"][primary] == 1.0
    assert set(p.sources.values()) == {"rules"}


def test_difficulty_hints():
    assert rules_proposal("Assisted Dip").values["difficulty"] == "beginner"
    assert rules_proposal("One-arm Ring Row").values["difficulty"] == "expert"


def test_ai_reply_that_is_not_an_object_changes_nothing():
    p = rules_proposal("Zercher Squat")
    before = dict(p.values)
    assert apply_ai(p, {"muscles": "vastus_lateralis"}) == []
    assert p.values == before
