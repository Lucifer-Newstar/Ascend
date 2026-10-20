import pytest

from app.modules.coach.validate import (
    Num,
    check_banned,
    check_numbers,
    check_reply,
    extract_numbers,
)

FACTS = "\n".join(
    [
        "Calories eaten today: 2650 of an estimated 2900 kcal",
        "Protein today: 96 g of 140 g",
        "Streak: 5 days; sets logged today: 12",
        "Chest: under, 4.5 effective sets this week (target 10-20), readiness 82%",
        "Weight 88.7 kg",
    ]
)


def values(text: str) -> list[float]:
    return [n.value for n in extract_numbers(text)]


def test_extracts_separators_decimals_ratios_and_words():
    assert values("2,650 kcal, 88.7 kg, pain 3/10, three sets") == [2650, 88.7, 3, 10, 3]


def test_units_are_canonicalised():
    nums = extract_numbers("12 reps at 60 kgs, 30 minutes, 82 percent")
    assert [n.unit for n in nums] == ["reps", "kg", "min", "%"]


def test_unknown_trailing_words_are_not_units():
    assert extract_numbers("5 great days")[0] == Num(5.0, "5", None)


def test_ordinals_and_words_inside_words_are_ignored():
    assert values("the first set, someone, phone") == []


@pytest.mark.parametrize(
    "reply",
    [
        "You've had 2650 of 2900 kcal today.",
        "About 2,600 kcal so far, so add a snack.",  # rounded, 1.9% off
        "Chest is at 4.5 effective sets against a 10-20 target.",
        "Readiness is 82%, so train as planned.",
        "A 5 day streak, and 12 sets today is plenty.",
        "Pick one thing and keep two habits.",  # allowed words
        "Protein is at 96 g of 140 g.",
    ],
)
def test_replies_that_only_reuse_facts_pass(reply):
    assert check_numbers(reply, FACTS).ok


@pytest.mark.parametrize(
    ("reply", "bad"),
    [
        ("Aim for 2,800 kcal today.", ["2,800 kcal"]),  # rounded, but 3.4% off
        ("You weigh 88.7 kcal.", ["88.7 kcal"]),  # right number, wrong unit
        ("Do 4 sets of curls.", ["4 sets"]),
        ("Rest three days.", ["three days"]),
        ("Your streak is 6 days.", ["6 days"]),
        ("Add 2 eggs.", ["2"]),  # "two" is allowed as a word, not as a digit
    ],
)
def test_invented_numbers_fail_and_are_named(reply, bad):
    result = check_numbers(reply, FACTS)
    assert not result.ok
    assert result.offending == bad


def test_numbers_from_the_users_message_are_allowed():
    question = "I benched 70 kg for 5 reps, is that good?"
    assert check_numbers("70 kg for 5 reps is solid work.", FACTS, question).ok


def test_rounding_must_drop_digits():
    # 2,651 has as many significant digits as 2,650: not a rounding, an invention.
    assert not check_numbers("2,651 kcal", FACTS).ok


def test_empty_reply_and_reply_without_numbers_pass():
    assert check_numbers("", FACTS).ok
    assert check_numbers("Great work, keep going.", FACTS).ok


@pytest.mark.parametrize(
    ("reply", "rule"),
    [
        ("Take 400 mg of ibuprofen before training.", "dose"),
        ("A painkiller will help.", "medicine"),
        ("You probably have a torn rotator cuff.", "diagnosis"),
        ("I've updated your plan to add squats.", "plan_changed"),
        ("No excuses, get to the gym.", "shame"),
    ],
)
def test_banned_phrases_name_their_rule(reply, rule):
    assert rule in check_banned(reply)


def test_ordinary_advice_is_not_banned():
    assert check_banned("Sleep well, eat your protein and keep the rest days.") == []
    assert check_banned("Want me to suggest a change to your plan? You can approve it.") == []


def test_check_reply_summarises_both_validators():
    checks = check_reply("Rest three days and take 2 tablets.", FACTS, None)
    assert not checks.ok
    summary = checks.summary()
    assert summary["numbers"] == "fail"
    assert summary["banned"] == "fail:dose"
    assert summary["version"].startswith("validate-")
    assert check_reply("Protein is at 96 g of 140 g.", FACTS, "how is my protein?").ok
