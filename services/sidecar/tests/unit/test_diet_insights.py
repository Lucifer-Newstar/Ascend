"""insights-v1: each rule fires on its pattern, stays quiet below its guard, and the report
keeps at most three findings, each with a formula and its inputs."""

import math
from datetime import date, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from app.modules.intelligence import insights as ins
from app.modules.intelligence import tdee as td

END = date(2026, 10, 18)  # Sunday
PROFILE = td.Profile(
    sex="male", age=21, height_cm=175, weight_kg=75, activity="moderate", goal="cut"
)


def days(
    kcal: float, protein: float, n: int = 14, weekend_extra: float = 0.0
) -> list[ins.NutritionDay]:
    out = []
    for i in range(n):
        d = END - timedelta(days=i)
        extra = weekend_extra if d.weekday() >= 5 else 0.0
        out.append(ins.NutritionDay(d, kcal + extra, protein))
    return out


def tdee_for(rate_kg_week: float, n: int = 21, weigh_every: int = 1) -> td.TdeeResult:
    start = END - timedelta(days=n - 1)
    inputs = [
        td.DayInput(
            start + timedelta(days=i),
            75 + rate_kg_week / 7 * i if i % weigh_every == 0 else None,
            2200,
        )
        for i in range(n)
    ]
    return td.compute(inputs, PROFILE, END)


def codes(r: ins.InsightReport) -> list[str]:
    return [f.code for f in r.findings]


def test_on_plan_week_is_quiet() -> None:
    r = ins.weekly(days(2200, 140), tdee_for(-0.5), "cut", 2200, 140, END)
    assert r.findings == []
    assert {c.code for c in r.checks} == {
        "intake_vs_target",
        "protein_short",
        "weekend_gap",
        "trend_vs_goal",
        "tdee_vs_formula",
        "logging_gap",
    }


def test_intake_above_target_is_computed_from_the_logged_days() -> None:
    r = ins.weekly(days(2600, 140), tdee_for(-0.5), "cut", 2200, 140, END)
    f = next(f for f in r.findings if f.code == "intake_vs_target")
    assert f.numbers == {"mean_intake_kcal": 2600, "target_kcal": 2200, "difference_kcal": 400}
    assert f.inputs["difference_pct"] == 18.2
    assert "2600 kcal" in f.text and "400 kcal above" in f.text


def test_protein_shortfall_fires_below_85_percent() -> None:
    assert "protein_short" in codes(
        ins.weekly(days(2200, 100), tdee_for(-0.5), "cut", 2200, 140, END)
    )
    assert "protein_short" not in codes(
        ins.weekly(days(2200, 125), tdee_for(-0.5), "cut", 2200, 140, END)
    )


def test_weekend_gap() -> None:
    r = ins.weekly(days(2100, 140, weekend_extra=600), tdee_for(-0.5), "cut", 2200, 140, END)
    f = next(f for f in r.findings if f.code == "weekend_gap")
    assert f.numbers["gap_kcal"] == 600


def test_cut_that_is_not_losing() -> None:
    r = ins.weekly(days(2200, 140), tdee_for(+0.2), "cut", 2200, 140, END)
    f = next(f for f in r.findings if f.code == "trend_vs_goal")
    assert f.title == "Cut, but the trend isn't falling"
    assert f.inputs["rate_kg_per_week"] > -0.1


def test_trend_needs_six_weigh_ins_in_fourteen_days() -> None:
    r = ins.weekly(days(2200, 140), tdee_for(+0.5, weigh_every=4), "cut", 2200, 140, END)
    check = next(c for c in r.checks if c.code == "trend_vs_goal")
    assert check.outcome == "not_enough_data"


def test_guards_keep_rules_quiet_with_little_data() -> None:
    few = days(3000, 50, n=3)
    r = ins.weekly(few, tdee_for(0.0, n=3), "cut", 2200, 140, END)
    by = {c.code: c.outcome for c in r.checks}
    assert by["intake_vs_target"] == "not_enough_data"
    assert by["protein_short"] == "not_enough_data"
    assert by["weekend_gap"] == "not_enough_data"
    assert codes(r) == ["logging_gap"]


def test_at_most_three_findings_largest_first() -> None:
    noisy = days(2900, 60, weekend_extra=700)[:10]
    r = ins.weekly(noisy, tdee_for(+0.4), "cut", 2200, 140, END)
    assert len(r.findings) <= ins.MAX_FINDINGS
    sev = [f.severity for f in r.findings]
    assert sev == sorted(sev, reverse=True)


nutrition = st.lists(
    st.tuples(
        st.integers(0, 30),
        st.one_of(st.none(), st.floats(0, 6000)),
        st.one_of(st.none(), st.floats(0, 400)),
    ),
    max_size=30,
).map(lambda rows: [ins.NutritionDay(END - timedelta(days=d), k, p) for d, k, p in rows])


@settings(max_examples=150, deadline=None)
@given(
    nutrition,
    st.sampled_from(["cut", "maintain", "bulk"]),
    st.integers(1200, 4000),
    st.integers(0, 250),
)
def test_findings_are_finite_bounded_and_explained(
    nd: list[ins.NutritionDay], goal: str, target: int, protein: int
) -> None:
    r = ins.weekly(nd, tdee_for(-0.3), goal, target, protein, END)
    assert len(r.findings) <= ins.MAX_FINDINGS
    assert len(r.checks) == 6
    for f in r.findings:
        assert f.formula and f.inputs
        assert math.isfinite(f.severity) and f.severity >= 0
        for v in list(f.numbers.values()) + list(f.inputs.values()):
            if isinstance(v, float):
                assert math.isfinite(v)
