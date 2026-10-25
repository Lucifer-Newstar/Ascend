from app.modules.planbuilder.extract import extract
from app.modules.planbuilder.facts import PlanFacts, dumbbell_label, lines, merge


def facts(text: str) -> PlanFacts:
    p = extract(text)
    assert p is not None, text
    return p.facts


def test_dumbbells_with_weights():
    p = extract("I have an 8kg dumbbell and two 5kg")
    assert p is not None
    assert p.facts.dumbbells_kg == [8.0, 5.0, 5.0]
    assert p.equipment_add == ["dumbbells"]
    assert dumbbell_label(p.facts.dumbbells_kg) == "8 kg and 2 × 5 kg"
    assert facts("i got dumbbells 1x8 kg, 2x5 kg").dumbbells_kg == [8.0, 5.0, 5.0]


def test_home_kit():
    assert facts("I have a punching bag").kit == ["punching_bag"]
    assert facts("got hand wraps, gloves and a gripper").kit == ["gripper", "hand_wraps", "gloves"]
    p = extract("I have rings, a pull-up bar and a bench too")
    assert p is not None and p.equipment_add == ["rings", "pullup_bar", "bench"]
    assert not p.specific  # base kit alone stays with the normal "I have a bench" edit


def test_sports_and_how_long_ago():
    assert facts("I want to train muay thai").sports == ["muay_thai"]
    f = facts("kickboxing and muay thai, trained 3 years ago")
    assert f.sports == ["muay_thai", "kickboxing"]
    assert f.sports_years_ago == 3
    f = facts("I trained kicks 3 years ago")
    assert f.sports == ["kickboxing"] and f.sports_years_ago == 3


def test_goal_target_and_time_frame():
    f = facts("I want to reach 50 kg")
    assert f.target_weight_kg == 50 and f.weight_kg is None
    f = facts("my goal is 50 kg from 42 kg in a month")
    assert (f.target_weight_kg, f.weight_kg, f.weeks) == (50, 42, 4)
    assert facts("I want to gain weight").goal == "gain_weight"


def test_appetite():
    assert facts("I can't eat much but I can drink").liquid_calories is True
    assert facts("i have a small appetite").liquid_calories is True


def test_days_or_a_target_alone_stay_the_v13_edits():
    for text in ("I want to train 4 days a week", "I want to reach 50 kg", "I have a bench"):
        p = extract(text)
        assert p is None or not p.specific, text
    p = extract("muay thai 3 years ago, I can train 5 days a week")
    assert p is not None and p.specific and p.facts.days_per_week == 5


def test_questions_and_chatter_are_not_facts():
    for text in (
        "how do I use a punching bag?",
        "what dumbbell weight should I buy",
        "is muay thai good for beginners?",
        "hello",
        "10 pushups",
        "I ate 2 idli",
    ):
        assert extract(text) is None, text


def test_merge_keeps_lists_and_replaces_scalars():
    a = PlanFacts(kit=["punching_bag"], sports=["boxing"], dumbbells_kg=[5, 5], days_per_week=3)
    b = PlanFacts(kit=["gripper"], sports=["muay_thai"], dumbbells_kg=[8], days_per_week=5)
    m = merge(a, b)
    assert m.kit == ["punching_bag", "gripper"]
    assert m.sports == ["boxing", "muay_thai"]
    assert m.dumbbells_kg == [8] and m.days_per_week == 5
    assert "Dumbbells: 8 kg." in lines(m)
