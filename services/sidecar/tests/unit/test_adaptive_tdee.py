"""tdee-v1: hand-checkable fixtures for the adaptive TDEE filter and the weekly target."""

import random
from datetime import date, timedelta

import pytest

from app.modules.intelligence import tdee as td

TODAY = date(2026, 10, 18)  # a Sunday
PROFILE = td.Profile(
    sex="male", age=21, height_cm=175, weight_kg=75, activity="moderate", goal="cut"
)


def simulate(
    true_tdee: float,
    intake: float,
    days: int,
    *,
    seed: int = 1,
    weigh_p: float = 1.0,
    log_p: float = 1.0,
    scale_sd: float = 0.4,
) -> list[td.DayInput]:
    rng = random.Random(seed)
    w = 75.0
    out = []
    start = TODAY - timedelta(days=days - 1)
    for i in range(days):
        eat = intake + rng.gauss(0, 150)
        w += (eat - true_tdee) / td.RHO_KCAL_PER_KG
        out.append(
            td.DayInput(
                start + timedelta(days=i),
                w + rng.gauss(0, scale_sd) if rng.random() < weigh_p else None,
                eat if rng.random() < log_p else None,
            )
        )
    return out


def test_prior_is_mifflin_st_jeor_times_activity() -> None:
    # 10*75 + 6.25*175 - 5*21 + 5 = 1743.75 ; x 1.55 = 2702.8
    assert td.prior_tdee(PROFILE) == pytest.approx(2702.8125)
    assert td.goal_target(2702.8, "cut") == 2200
    assert td.goal_target(2702.8, "bulk") == 3000
    assert td.goal_target(1000, "cut") == 1200


def test_no_data_is_a_cold_start_with_the_formula_range() -> None:
    r = td.compute([], PROFILE, TODAY)
    assert r.status == "cold_start"
    assert r.tdee_kcal == pytest.approx(2702.8, abs=0.1)
    assert r.sd_kcal == td.PRIOR_SD_KCAL
    assert r.target_kcal == 2200 and r.target_source == "formula"


def test_first_day_keeps_the_prior_and_a_weigh_in_moves_the_trend() -> None:
    s = td.run_filter([td.DayInput(TODAY, 80.0, None)], 2500, 75)
    assert len(s) == 1
    assert s[0].tdee_kcal == 2500
    assert s[0].trend_kg == 80.0  # the first weigh-in seeds the trend


def test_converges_to_the_true_expenditure_with_full_logs() -> None:
    days = simulate(true_tdee=2400, intake=1900, days=70)
    r = td.compute(days, PROFILE, TODAY)
    assert r.status == "adaptive"
    assert abs(r.tdee_kcal - 2400) < 150
    assert r.sd_kcal < td.SETTLED_SD_KCAL
    assert r.low_kcal < r.tdee_kcal < r.high_kcal


def test_gaps_in_weigh_ins_and_meals_still_converge() -> None:
    days = simulate(true_tdee=2400, intake=1900, days=90, weigh_p=0.5, log_p=0.8, seed=7)
    r = td.compute(days, PROFILE, TODAY)
    assert abs(r.tdee_kcal - 2400) < 200
    assert len(r.series) == 90  # one state per calendar day, gaps included


def test_missing_days_widen_the_uncertainty() -> None:
    full = td.run_filter(simulate(2400, 1900, 30, seed=3), 2700, 75)
    sparse = td.run_filter(simulate(2400, 1900, 30, seed=3, weigh_p=0.2, log_p=0.3), 2700, 75)
    assert sparse[-1].sd_kcal > full[-1].sd_kcal


def test_partly_logged_days_are_not_used_as_intake() -> None:
    s = td.run_filter(
        [td.DayInput(TODAY - timedelta(days=1), 75, None), td.DayInput(TODAY, None, 450)], 2500, 75
    )
    assert s[-1].intake_kcal == 450 and s[-1].intake_used is False


def test_target_holds_when_a_week_has_fewer_than_six_logged_days() -> None:
    days = simulate(true_tdee=2400, intake=1900, days=70)
    # Drop intake on three days of the last full week (Mon 5 Oct to Sun 11 Oct).
    gap = {date(2026, 10, 6), date(2026, 10, 7), date(2026, 10, 8)}
    days = [td.DayInput(d.day, d.weight_kg, None if d.day in gap else d.intake_kcal) for d in days]
    r = td.compute(days, PROFILE, date(2026, 10, 13))
    week = r.weeks[-1]
    assert week.week_start == date(2026, 10, 12)
    assert week.changed is False and "4 of 7" in week.reason
    assert week.target_kcal == r.weeks[-2].target_kcal


def test_weekly_change_is_capped() -> None:
    # True expenditure far above the formula: the target climbs 250 kcal a week at most.
    days = simulate(true_tdee=3600, intake=3100, days=84, seed=5)
    r = td.compute(days, PROFILE, TODAY)
    steps = [b.target_kcal - a.target_kcal for a, b in zip(r.weeks, r.weeks[1:], strict=False)]
    assert max(abs(x) for x in steps) <= td.MAX_WEEKLY_CHANGE_KCAL
    assert r.target_source == "adaptive"


def test_target_changes_only_on_mondays() -> None:
    days = simulate(true_tdee=2400, intake=1900, days=70)
    r = td.compute(days, PROFILE, TODAY)
    assert all(w.week_start.weekday() == 0 for w in r.weeks)


def test_deterministic() -> None:
    days = simulate(2400, 1900, 60, weigh_p=0.6, log_p=0.7)
    assert td.compute(days, PROFILE, TODAY) == td.compute(days, PROFILE, TODAY)


def test_future_days_are_ignored() -> None:
    days = simulate(2400, 1900, 30)
    future = [td.DayInput(TODAY + timedelta(days=3), 60.0, 5000.0)]
    assert td.compute(days + future, PROFILE, TODAY).series[-1].day == TODAY
