"""The evaluation's own metric code (eval/recovery_eval.py, eval/progression_eval.py)."""

import math
from datetime import datetime, timedelta

import pytest

from eval import synth
from eval.progression_eval import prescription_metrics, stall_metrics
from eval.recovery_eval import calibration, fixed_rule, pearson, spearman

T0 = datetime(2025, 3, 3, 18, 0)


def test_correlations() -> None:
    assert pearson([1, 2, 3], [2, 4, 6]) == pytest.approx(1.0)
    assert pearson([1, 2, 3], [3, 2, 1]) == pytest.approx(-1.0)
    assert math.isnan(pearson([1, 1, 1], [1, 2, 3]))
    # Spearman only sees order: a monotone curve is a perfect rank correlation
    assert spearman([1, 2, 3, 4], [1, 8, 27, 64]) == pytest.approx(1.0)
    assert spearman([1, 2, 2, 3], [1, 2, 2, 3]) == pytest.approx(1.0)


def test_calibration_of_a_perfect_and_a_biased_predictor() -> None:
    xs = [i / 100 for i in range(100)]
    assert calibration(xs, xs)["ece"] == pytest.approx(0.0)
    biased = calibration(xs, [min(1.0, x + 0.1) for x in xs])
    assert biased["ece"] == pytest.approx(0.0955, abs=0.005)
    assert len(biased["bins"]) == 10


def test_fixed_48_hour_rule() -> None:
    assert fixed_rule(None, T0) == 1.0
    assert fixed_rule(T0 - timedelta(hours=24), T0) == pytest.approx(0.5)
    assert fixed_rule(T0 - timedelta(hours=72), T0) == 1.0


def exposure(
    i: int,
    *,
    target=8,
    achieved=(8, 8, 8),
    possible=10.0,
    load=60.0,
    ideal=60.0,
    flagged=False,
    gain=0.05,
) -> synth.Exposure:
    return synth.Exposure(
        user=0,
        exercise="Bench",
        start=T0 + timedelta(days=3 * i),
        index=i,
        load=load,
        target_reps=target,
        achieved=list(achieved),
        rpe=[8.0] * len(achieved),
        possible_first=possible,
        ideal_load=ideal,
        true_strength=100.0,
        true_capacity=100.0,
        plateau=False,
        plateau_since=None,
        flagged_stall=flagged,
        gain_4w=gain,
        rpe_log_prob=1.0,
    )


def test_prescription_metrics_skip_the_first_exposure() -> None:
    exps = [
        exposure(0, achieved=(1, 1, 1)),
        exposure(1),
        exposure(2, achieved=(8, 7, 6), possible=7.0),
    ]
    m = prescription_metrics(exps)
    assert m["exposures"] == 2 and m["sets"] == 6
    assert m["hit_within_1_rep"] == pytest.approx(5 / 6, abs=1e-3)
    assert m["hit_exact"] == pytest.approx(4 / 6, abs=1e-3)
    # realised RIR: 10 - 8 = 2 (on target) and 7 - 8 = -1 (too hard)
    assert m["rir_error_mean"] == pytest.approx(-1.5)
    assert m["too_hard_share"] == pytest.approx(0.5)


def test_stall_metrics_count_events_and_false_alarms() -> None:
    # progressing for 12 exposures (one false alarm), then flat with a flag 2 exposures in
    exps = [exposure(i, gain=0.05, flagged=(i == 5)) for i in range(12)]
    exps += [exposure(12 + i, gain=0.0, flagged=(i == 2)) for i in range(10)]
    s = stall_metrics(exps)
    assert (s["true_stalls"], s["detected"], s["false_alarms"]) == (1, 1, 1)
    assert s["precision"] == pytest.approx(0.5) and s["recall"] == pytest.approx(1.0)
    assert s["median_delay_exposures"] == 2
