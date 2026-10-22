"""Property tests for prog-v1: never NaN, never negative, bounded jumps, deterministic,
and monotonic in the last session's reps."""

import math
from datetime import datetime, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from app.modules.intelligence import progression as prog
from app.modules.intelligence.progression import ExerciseInfo, SessionRec, SetRec

NOW = datetime(2026, 10, 20, 18, 0)

exercise = st.builds(
    ExerciseInfo,
    st.just("X"),
    st.sampled_from(["barbell", "dumbbell", "cable", "machine", "kettlebell", "bodyweight", "bar"]),
    st.sampled_from(["reps", "reps", "reps", "hold"]),
    st.sampled_from(["compound", "isolation", None]),
    st.sampled_from(["push", "pull", "squat", "hinge", "other"]),
    st.one_of(st.none(), st.integers(3, 12)),
    st.one_of(st.none(), st.integers(13, 30)),
)
set_rec = st.builds(
    SetRec,
    st.integers(0, 40),
    st.sampled_from([0.0, 5.0, 8.0, 20.0, 42.5, 60.0, 61.25, 100.0, 180.0]),
    st.one_of(st.none(), st.sampled_from([5.0, 6.0, 6.5, 7.0, 8.0, 8.5, 9.0, 9.5, 10.0])),
    st.one_of(st.none(), st.integers(1, 180)),
)
history = st.lists(
    st.tuples(st.integers(1, 120), st.lists(set_rec, min_size=1, max_size=6)),
    max_size=12,
).map(
    lambda rows: [
        SessionRec(NOW - timedelta(days=d, hours=i), tuple(sets))
        for i, (d, sets) in enumerate(rows)
    ]
)
optional_readiness = st.one_of(st.none(), st.floats(0, 1))


@settings(max_examples=300, deadline=None)
@given(exercise, history, optional_readiness)
def test_targets_are_finite_and_bounded(ex, hist, readiness) -> None:
    t = prog.next_target(ex, hist, NOW, readiness=readiness)
    assert t.algo_version == "prog-v1"
    assert math.isfinite(t.weight_kg) and t.weight_kg >= 0
    if t.reps is not None:
        assert 1 <= t.reps <= 40
    if t.seconds is not None:
        assert t.seconds >= 1
    assert t.why and isinstance(t.why, str)
    for v in t.facts.values():
        assert not (isinstance(v, float) and not math.isfinite(v))


@settings(max_examples=300, deadline=None)
@given(exercise, history)
def test_never_jumps_more_than_ten_percent_or_one_plate(ex, hist) -> None:
    t = prog.next_target(ex, hist, NOW)
    usable = [s for s in hist if prog.working_sets(s, ex.measure == "hold")]
    if not usable or t.kind == "none":
        return
    last = prog.top_load(max(usable, key=lambda s: s.at))
    if last <= 0:
        return
    allowed = max(last * prog.MAX_STEP_FRACTION, prog.increment(ex, last) or 2.5)
    assert t.weight_kg <= last + allowed + 1e-9


@settings(max_examples=200, deadline=None)
@given(exercise, history, optional_readiness)
def test_deterministic(ex, hist, readiness) -> None:
    a = prog.next_target(ex, hist, NOW, readiness=readiness)
    b = prog.next_target(ex, list(reversed(hist)), NOW, readiness=readiness)
    assert (a.weight_kg, a.reps, a.seconds, a.reason) == (b.weight_kg, b.reps, b.seconds, b.reason)


@settings(max_examples=200, deadline=None)
@given(st.integers(6, 9), st.integers(1, 3), st.sampled_from([50.0, 60.0, 80.0, 100.0]))
def test_more_reps_never_lowers_the_next_load(base, extra, load) -> None:
    ex = ExerciseInfo("Bench", "barbell", "reps", "compound", "push")
    fewer = [SessionRec(NOW - timedelta(days=3), tuple(SetRec(base, load, 8.0) for _ in range(3)))]
    more = [
        SessionRec(
            NOW - timedelta(days=3), tuple(SetRec(base + extra, load, 8.0) for _ in range(3))
        )
    ]
    assert prog.next_target(ex, more, NOW).weight_kg >= prog.next_target(ex, fewer, NOW).weight_kg


@settings(max_examples=150, deadline=None)
@given(exercise, history, st.floats(0, 1), st.floats(0, 1))
def test_lower_readiness_never_raises_the_target(ex, hist, r1, r2) -> None:
    lo, hi = sorted([r1, r2])
    a = prog.next_target(ex, hist, NOW, readiness=lo)
    b = prog.next_target(ex, hist, NOW, readiness=hi)
    assert a.weight_kg <= b.weight_kg + 1e-9
    if a.reps is not None and b.reps is not None and a.weight_kg == b.weight_kg:
        assert a.reps <= b.reps
