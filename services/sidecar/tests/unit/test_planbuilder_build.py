from app.modules.planbuilder.build import SHAKE, Person, build
from app.modules.planbuilder.facts import PlanFacts

NAVIN = PlanFacts(
    goal="gain_weight",
    weight_kg=42,
    target_weight_kg=50,
    dumbbells_kg=[8, 5, 5],
    kit=["punching_bag", "hand_wraps", "gripper"],
    sports=["kickboxing", "muay_thai"],
    sports_years_ago=3,
    days_per_week=5,
    liquid_calories=True,
)
ME = Person(weight_kg=42, age=21, equipment=["dumbbells", "rings"], pushups=15, pullups=4)


def names(day) -> list[str]:
    return [s.exercise for s in day.slots]


def test_the_whole_conversation_builds_strength_and_skill_days():
    b = build(NAVIN, ME)
    by_day = {d.weekday: d for d in b.draft.days}
    assert sorted(by_day) == [0, 1, 2, 4, 5]  # 2 rest days: Thu, Sun
    assert by_day[1].name.startswith("Skill") and by_day[5].name.startswith("Skill")
    assert b.week_line.startswith("Mon Strength A · Tue Skill")
    strength = names(by_day[0]) + names(by_day[2])
    assert "Pull-up" in strength  # rings count as a bar; 4 pull-ups -> full pull-ups
    assert "Dumbbell Squat" in strength and "Dumbbell Floor Press" in strength  # no bench
    assert "Dumbbell Bench Press" not in strength
    skill = names(by_day[1])
    assert {"Kickboxing Shadow Rounds", "Roundhouse Kick Drill", "Heavy Bag Combos"} <= set(skill)
    notes = " ".join(b.notes)
    assert "8 kg dumbbell" in notes and "two 5 kg dumbbells" in notes
    assert "waist height" in notes and "60% power with your hands wrapped" in notes
    assert "Gripper" in notes


def test_food_targets_shakes_and_no_oats():
    food = " ".join(build(NAVIN, ME).food)
    assert "Protein: about 67-84 g" in food
    assert "300-500 kcal" in food
    assert SHAKE in food and "oat" not in food.lower()
    assert "Week 1: one shake a day" in food and "skill days add one more" in food


def test_calories_hidden_under_18_and_with_hide_calories():
    for p in (Person(weight_kg=42, age=16), Person(weight_kg=42, age=21, hide_calories=True)):
        food = " ".join(build(NAVIN, p).food)
        assert "kcal" not in food
        assert "Eat a little more than now" in food


def test_days_are_capped_to_keep_two_rest_days_and_follow_the_kit():
    b = build(PlanFacts(days_per_week=6), Person(equipment=["none"]))
    assert len(b.draft.days) == 5
    flat = [n for d in b.draft.days for n in names(d)]
    assert not any("Dumbbell" in n or n == "Pull-up" for n in flat)
    assert all(not d.name.startswith("Skill") for d in b.draft.days)
    # A beginner with 3 push-ups starts on incline push-ups.
    b = build(PlanFacts(), Person(pushups=3, equipment=["none"]))
    assert names(b.draft.days[0])[0] == "Incline Push-up"
