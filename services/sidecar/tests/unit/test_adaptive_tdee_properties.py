"""Property tests for tdee-v1: finite and bounded on any history, gaps included, and the
uncertainty never grows when a weigh-in is added."""

import math
from datetime import date, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from app.modules.intelligence import tdee as td

TODAY = date(2026, 10, 18)

profile = st.builds(
    td.Profile,
    st.sampled_from(["male", "female", "other"]),
    st.integers(14, 90),
    st.floats(130, 210),
    st.floats(35, 180),
    st.sampled_from(["sedentary", "light", "moderate", "active", "very_active", "unknown"]),
    st.sampled_from(["cut", "maintain", "bulk"]),
)
weight = st.one_of(st.none(), st.floats(30, 200), st.just(float("nan")), st.just(0.0))
intake = st.one_of(st.none(), st.floats(0, 8000), st.just(float("inf")))
history = st.lists(st.tuples(st.integers(0, 400), weight, intake), max_size=60).map(
    lambda rows: [td.DayInput(TODAY - timedelta(days=d), w, i) for d, w, i in rows]
)


@settings(max_examples=150, deadline=None)
@given(history, profile)
def test_never_nan_and_bounded(days: list[td.DayInput], p: td.Profile) -> None:
    r = td.compute(days, p, TODAY)
    for s in r.series:
        assert math.isfinite(s.tdee_kcal) and math.isfinite(s.sd_kcal) and math.isfinite(s.trend_kg)
        assert td.TDEE_MIN <= s.tdee_kcal <= td.TDEE_MAX
        assert 0 < s.sd_kcal <= td.PRIOR_SD_KCAL
    assert 1200 <= r.target_kcal
    assert r.status in {"cold_start", "learning", "adaptive"}
    assert len(r.series) <= td.MAX_DAYS


@settings(max_examples=100, deadline=None)
@given(history, profile)
def test_weekly_steps_are_capped(days: list[td.DayInput], p: td.Profile) -> None:
    r = td.compute(days, p, TODAY)
    targets = [r.formula_target_kcal] + [w.target_kcal for w in r.weeks]
    for a, b in zip(targets, targets[1:], strict=False):
        assert abs(b - a) <= td.MAX_WEEKLY_CHANGE_KCAL


@settings(max_examples=100, deadline=None)
@given(history, st.floats(40, 150))
def test_a_weigh_in_never_widens_the_tdee_uncertainty(
    days: list[td.DayInput], extra: float
) -> None:
    base = [d for d in days if d.day != TODAY]
    without = td.run_filter(base + [td.DayInput(TODAY, None, None)], 2500, 75)
    with_w = td.run_filter(base + [td.DayInput(TODAY, extra, None)], 2500, 75)
    assert with_w[-1].sd_kcal <= without[-1].sd_kcal + 1e-6
