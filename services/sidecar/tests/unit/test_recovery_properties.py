"""Property tests for recovery-v2: bounded, never NaN, monotonic where it should be."""

from datetime import datetime, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from app.modules.intelligence import recovery as rec

NOW = datetime(2026, 10, 20, 18, 0)
MUSCLE_KEYS = ["lower_chest", "triceps", "quads", "lats", "abs", "calves"]

set_strategy = st.builds(
    lambda hours, ms, kind, reps, w, rpe, dur, ref: rec.SetInput(
        at=NOW - timedelta(hours=hours),
        muscles=ms,
        kind=kind,
        reps=reps,
        weight_kg=w,
        rpe=rpe,
        duration_s=dur,
        e1rm_ref=ref,
    ),
    st.floats(0, 24 * 40, allow_nan=False),
    st.dictionaries(st.sampled_from(MUSCLE_KEYS), st.sampled_from([0.25, 0.5, 1.0]), min_size=1),
    st.sampled_from(["reps", "hold", "time"]),
    st.integers(0, 60),
    st.floats(0, 400, allow_nan=False),
    st.one_of(st.none(), st.floats(1, 10, allow_nan=False)),
    st.one_of(st.none(), st.integers(0, 4 * 3600)),
    st.one_of(st.none(), st.floats(0, 500, allow_nan=False)),
)
checkin_strategy = st.one_of(
    st.none(),
    st.builds(rec.CheckinInput, st.integers(1, 5), st.sampled_from(["none", "some", "a_lot"])),
)
k_strategy = st.dictionaries(
    st.sampled_from(list(rec.GROUPS)), st.floats(0.01, 10, allow_nan=False)
)


@settings(max_examples=150, deadline=None)
@given(st.lists(set_strategy, max_size=40), k_strategy, checkin_strategy)
def test_outputs_are_bounded_and_finite(sets, k, checkin) -> None:
    for m in rec.compute(sets, NOW, k, checkin):
        assert 0.0 <= m.readiness <= 1.0
        assert 0.0 <= m.readiness_population <= 1.0
        assert m.fatigue >= 0.0
        assert m.fatigue == m.fatigue  # not NaN
        assert rec.K_MIN <= m.k <= rec.K_MAX
        assert 1.0 <= m.modifier <= 1.45
        assert m.ready_at is None or m.ready_at >= NOW


@settings(max_examples=100, deadline=None)
@given(st.lists(set_strategy, min_size=1, max_size=20), set_strategy)
def test_another_set_never_raises_readiness(sets, extra) -> None:
    before = {m.key: m.readiness for m in rec.compute(sets, NOW)}
    after = {m.key: m.readiness for m in rec.compute([*sets, extra], NOW)}
    assert all(after[k] <= before[k] + 1e-9 for k in before)


@settings(max_examples=100, deadline=None)
@given(st.lists(set_strategy, max_size=20), st.floats(0, 24 * 10, allow_nan=False))
def test_waiting_never_lowers_readiness(sets, hours) -> None:
    now = {m.key: m.readiness for m in rec.compute(sets, NOW)}
    later = {m.key: m.readiness for m in rec.compute(sets, NOW + timedelta(hours=hours))}
    assert all(later[k] >= now[k] - 1e-9 for k in now)


@settings(max_examples=100, deadline=None)
@given(st.floats(1, 10), st.floats(1, 10))
def test_harder_sets_dose_more(rpe_a, rpe_b) -> None:
    lo, hi = sorted([rpe_a, rpe_b])
    base = {"at": NOW, "muscles": {"quads": 1.0}, "reps": 8, "weight_kg": 80.0}
    assert rec.dose(rec.SetInput(rpe=lo, **base)).es <= rec.dose(rec.SetInput(rpe=hi, **base)).es


@settings(max_examples=100, deadline=None)
@given(st.lists(set_strategy, min_size=1, max_size=20), st.floats(0.6, 1.6), st.floats(0.6, 1.6))
def test_slower_recovery_means_lower_readiness(sets, k_a, k_b) -> None:
    lo, hi = sorted([k_a, k_b])
    fast = {m.key: m.readiness for m in rec.compute(sets, NOW, {g: lo for g in rec.GROUPS})}
    slow = {m.key: m.readiness for m in rec.compute(sets, NOW, {g: hi for g in rec.GROUPS})}
    assert all(slow[k] <= fast[k] + 1e-9 for k in fast)


@settings(max_examples=60, deadline=None)
@given(st.lists(set_strategy, min_size=1, max_size=20), st.integers(1, 5))
def test_worse_sleep_never_raises_readiness(sets, sleep) -> None:
    good = {m.key: m.readiness for m in rec.compute(sets, NOW, None, rec.CheckinInput(5, "none"))}
    bad = {
        m.key: m.readiness for m in rec.compute(sets, NOW, None, rec.CheckinInput(sleep, "none"))
    }
    assert all(bad[k] <= good[k] + 1e-9 for k in good)
