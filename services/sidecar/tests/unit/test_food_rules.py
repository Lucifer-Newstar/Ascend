"""Food rules (v1.2): India's food guidelines (ICMR-NIN 2024) and the day check."""

from __future__ import annotations

import re

from app.modules.nutrition import food_rules as fr

BODY_WORDS = re.compile(r"\b(weight|fat loss|body ?fat|bmi|calorie|kcal|slim|thin|lose)\b", re.I)


def test_keywords_match_whole_words_only():
    assert fr.groups_of("Moong sprouts salad") == {"pulses", "vegetables"}
    assert fr.groups_of("Curd rice") == {"cereals_millets", "milk_curd"}
    assert "cereals_millets" not in fr.groups_of("Whey protein (in water)")  # not "roti"
    assert fr.is_hfss("Maggi noodles (masala)") and fr.is_hfss("Potato chips")
    assert not fr.is_hfss("Pancake")  # "cake" inside a word is not matched
    assert not fr.is_hfss("Steamed rice")


def test_an_empty_day_asks_for_meals():
    check = fr.check_day([])
    assert check.foods == 0 and check.missing == []
    assert "Log your meals" in check.tips[0]


def test_gaps_become_at_most_three_kind_tips():
    check = fr.check_day(["Steamed rice", "Potato chips", "Samosa", "Cola (soft drink)"])
    assert "vegetables" in check.missing and "fruit" in check.missing
    assert check.hfss == ["Potato chips", "Samosa", "Cola (soft drink)"]
    assert 1 <= len(check.tips) <= 3
    assert any("3 HFSS" in t for t in check.tips)


def test_eggs_or_pulses_both_count_as_protein():
    vegetarian = fr.check_day(["Idli", "Sambar", "Banana", "Curd (plain)", "Almonds", "Avial"])
    assert vegetarian.missing == []
    assert vegetarian.tips == ["A varied plate today. Keep the salt and added sugar low."]
    eggs = fr.check_day(["Boiled egg", "Chapati"])
    assert not any("No pulses" in t for t in eggs.tips)


def test_the_guidance_is_body_neutral_and_never_about_weight():
    texts = [t for g in fr.GUIDELINES for t in g]
    texts += fr.check_day([]).tips + fr.check_day(["Samosa", "Jalebi"]).tips
    texts += fr.check_day(["Steamed rice"]).tips
    for t in texts:
        assert not BODY_WORDS.search(t), t
    assert fr.SOURCE.endswith("ICMR-NIN 2024")
