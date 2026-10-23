import pytest

from app.modules.nutrition.tdee import (
    bmr_mifflin_st_jeor,
    calorie_target,
    energy_goal,
    protein_target_g,
    tdee,
)


def test_bmr_male_reference_value():
    # 10*70 + 6.25*175 - 5*21 + 5 = 1693.75
    assert bmr_mifflin_st_jeor("male", 70, 175, 21) == pytest.approx(1693.75)


def test_bmr_female_reference_value():
    # 10*60 + 6.25*165 - 5*30 - 161 = 1320.25
    assert bmr_mifflin_st_jeor("female", 60, 165, 30) == pytest.approx(1320.25)


def test_tdee_applies_activity_factor():
    assert tdee(1000, "moderate") == pytest.approx(1550)


@pytest.mark.parametrize("goal,expected", [("cut", 2000), ("maintain", 2500), ("bulk", 2800)])
def test_calorie_target_by_goal(goal, expected):
    assert calorie_target(2500, goal) == expected


def test_calorie_target_has_safety_floor():
    assert calorie_target(1300, "cut") == 1200


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        bmr_mifflin_st_jeor("male", 0, 175, 21)


def test_protein_target():
    assert protein_target_g(70, "bulk") == 112


def test_no_deficit_below_bmi_18_5_or_under_18():
    # 45 kg at 170 cm is a BMI of 15.6: "lose fat" must not set a 500 kcal deficit
    assert energy_goal("cut", 45, 170, 21) == "maintain"
    assert energy_goal("cut", 70, 175, 16) == "maintain"
    assert energy_goal("cut", 70, 175, 21) == "cut"
    assert energy_goal("bulk", 45, 170, 21) == "bulk"
