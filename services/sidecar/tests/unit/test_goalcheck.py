"""goalcheck-v1: unrealistic or unsafe goals are flagged with their numbers."""

from __future__ import annotations

from app.modules.planner import validate as g


def codes(flags: list[g.Flag]) -> list[str]:
    return [f.code for f in flags]


def test_losing_ten_kg_in_a_month_is_blocked() -> None:
    flags = g.check_weight_goal(80, 70, 4)
    assert codes(flags) == ["loss_too_fast"]
    f = flags[0]
    assert f.severity == "block"
    assert f.numbers["kg_per_week"] == 2.5 and f.numbers["pct_per_week"] == 3.12
    assert f.numbers["safe_weeks"] == 17  # 10 kg at 0.75 % of 80 kg a week
    assert "17 weeks" in f.message


def test_sensible_paces_pass_and_edges_warn() -> None:
    assert g.check_weight_goal(80, 76, 8) == []  # 0.5 kg/week = 0.625 %
    assert codes(g.check_weight_goal(80, 74.5, 8)) == ["loss_aggressive"]  # 0.86 %/week
    assert codes(g.check_weight_goal(80, 73, 8)) == ["loss_too_fast"]  # 1.09 %/week
    assert codes(g.check_weight_goal(70, 72, 4)) == ["gain_fast"]  # 0.71 %/week
    assert codes(g.check_weight_goal(70, 75, 4)) == ["gain_too_fast"]
    assert g.check_weight_goal(70, 72, 12) == []


def test_underweight_target_is_blocked() -> None:
    assert "underweight_target" in codes(g.check_weight_goal(60, 50, 52, height_cm=175))


def test_calorie_floor_uses_bmr_and_sex() -> None:
    assert g.kcal_floor("female", 1100) == 1200
    assert g.kcal_floor("male", 1700) == 1700
    assert codes(g.check_calories(1400, "male", 1650)) == ["kcal_below_floor"]
    assert g.check_calories(1800, "male", 1650) == []


def test_protein_band() -> None:
    assert codes(g.check_protein(80, 70)) == ["protein_low"]  # 1.14 g/kg
    assert g.check_protein(120, 70) == []
    assert codes(g.check_protein(250, 70)) == ["protein_very_high"]


def test_schedule_and_strength() -> None:
    assert codes(g.check_schedule(7, 60, "intermediate")) == ["no_rest_day"]
    assert codes(g.check_schedule(6, 60, "beginner")) == ["beginner_too_many_days"]
    assert codes(g.check_schedule(3, 150, "beginner")) == ["long_sessions"]
    assert codes(g.check_strength_goal(60, 100, 4, "beginner")) == ["strength_unrealistic"]
    assert codes(g.check_strength_goal(100, 105, 4, "intermediate")) == ["strength_ambitious"]
    assert g.check_strength_goal(100, 105, 12, "intermediate") == []
    assert g.worst(g.check_strength_goal(60, 100, 4, "beginner")) == "block"
