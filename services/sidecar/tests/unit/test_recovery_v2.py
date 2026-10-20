"""recovery-v2 (E1) on hand-computed fixtures."""

from datetime import datetime, timedelta

import pytest

from app.modules.intelligence import recovery as rec

NOW = datetime(2026, 10, 20, 18, 0)
BENCH = {"lower_chest": 1.0, "upper_chest": 0.5, "front_delts": 0.5, "triceps": 0.5}


def s(hours_ago: float, **kw: object) -> rec.SetInput:
    base: dict[str, object] = {"muscles": BENCH, "reps": 8, "weight_kg": 60.0}
    base.update(kw)
    return rec.SetInput(at=NOW - timedelta(hours=hours_ago), **base)  # type: ignore[arg-type]


def state(states: list[rec.MuscleRecovery], key: str) -> rec.MuscleRecovery:
    return next(m for m in states if m.key == key)


@pytest.mark.parametrize(
    ("rir", "expected"), [(0, 1.0), (1, 1.0), (2, 0.9), (3, 0.8), (5, 0.6), (8, 0.3), (10, 0.3)]
)
def test_intensity_from_rir(rir: float, expected: float) -> None:
    assert rec.intensity(rir) == pytest.approx(expected)


def test_rir_comes_from_rpe_first() -> None:
    assert rec.estimate_rir(s(0, rpe=8.0)) == (2.0, "rpe")
    assert rec.estimate_rir(s(0, rpe=10.0)) == (0.0, "rpe")


def test_rir_estimated_from_own_e1rm_without_rpe() -> None:
    # 30 x (80 / 60 - 1) = 10 reps possible at 60 kg; 8 done -> RIR 2
    rir, src = rec.estimate_rir(s(0, e1rm_ref=80.0))
    assert src == "e1rm"
    assert rir == pytest.approx(2.0)


def test_rir_default_without_rpe_or_e1rm() -> None:
    assert rec.estimate_rir(s(0)) == (rec.DEFAULT_RIR, "default")


def test_volume_rules() -> None:
    assert rec.volume(s(0, reps=3)) == 0.85
    assert rec.volume(s(0, reps=10)) == 1.0
    assert rec.volume(s(0, reps=25)) == 1.1
    assert rec.volume(s(0, kind="hold", duration_s=30, reps=1)) == 1.0
    assert rec.volume(s(0, kind="hold", duration_s=3, reps=1)) == 0.25
    assert rec.volume(s(0, kind="time", duration_s=1800)) == 3.0
    assert rec.volume(s(0, reps=0)) == 0.0


def test_dose_is_weight_times_intensity_times_volume() -> None:
    c = rec.contributions([s(0, rpe=8.0)])
    by = {x.muscle: x.es for x in c}
    assert by["lower_chest"] == pytest.approx(0.9)
    assert by["triceps"] == pytest.approx(0.45)


def test_one_half_life_halves_the_fatigue() -> None:
    # lower chest: half-life 36 h, capacity 10; one RPE-8 set = 0.9 ES
    fresh = state(rec.compute([s(0, rpe=8.0)], NOW), "lower_chest")
    later = state(rec.compute([s(36, rpe=8.0)], NOW), "lower_chest")
    assert fresh.fatigue == pytest.approx(0.9)
    assert later.fatigue == pytest.approx(0.45)
    assert later.readiness == pytest.approx(1 - 0.045)


def test_personal_k_stretches_the_half_life() -> None:
    k = {"Push": 1.5}
    m = state(rec.compute([s(54, rpe=8.0)], NOW, k), "lower_chest")
    assert m.half_life_h == pytest.approx(54.0)
    assert m.fatigue == pytest.approx(0.45)
    assert m.k == 1.5
    # the population value (k = 1) is reported beside it for "population vs you"
    assert m.readiness_population > m.readiness


def test_k_is_clamped() -> None:
    m = state(rec.compute([s(1)], NOW, {"Push": 9.0}), "lower_chest")
    assert m.k == rec.K_MAX


def test_checkin_modifier() -> None:
    assert rec.checkin_modifier(None, True) == 1.0
    assert rec.checkin_modifier(rec.CheckinInput(5, "none"), True) == pytest.approx(1.0)
    assert rec.checkin_modifier(rec.CheckinInput(1, "none"), True) == pytest.approx(1.2)
    assert rec.checkin_modifier(rec.CheckinInput(1, "a_lot"), True) == pytest.approx(1.45)
    # soreness only counts for muscles trained in the last 72 h
    assert rec.checkin_modifier(rec.CheckinInput(5, "a_lot"), False) == pytest.approx(1.0)


def test_status_and_ready_at() -> None:
    sets = [s(0, rpe=9.0) for _ in range(8)]  # 8 x 1.0 ES on the lower chest, just now
    m = state(rec.compute(sets, NOW), "lower_chest")
    assert m.fatigue == pytest.approx(8.0)
    assert m.readiness == pytest.approx(0.2)
    assert m.status == "recovering"
    # readiness 0.70 when F = 3: 36 h x log2(8 / 3) from now
    assert m.ready_at is not None
    hours = (m.ready_at - NOW).total_seconds() / 3600
    assert hours == pytest.approx(36 * 1.4150375, rel=1e-4)


def test_no_data_and_future_sets() -> None:
    states = rec.compute([s(-5)], NOW)  # logged after "now"
    assert all(m.status == "no_data" for m in states)
    assert len(states) == 19


def test_top_sets_explain_the_fatigue() -> None:
    m = state(rec.compute([s(2, exercise="Bench"), s(30, exercise="Dip")], NOW), "lower_chest")
    assert [t[0] for t in m.top_sets] == ["Bench", "Dip"]
