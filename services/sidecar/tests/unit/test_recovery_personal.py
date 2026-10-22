"""Personal recovery factors: shrinkage to the population value, and recovery of a known
k on a synthetic user (eval/synth.py)."""

import random
from datetime import datetime, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from app.modules.intelligence import personal
from app.modules.intelligence import recovery as rec
from eval import synth

T0 = datetime(2026, 1, 5, 18, 0)
BENCH = {"pec_major_sternal": 1.0, "triceps_lateral": 0.5}


def inputs(sessions: list[synth.Session]) -> tuple[list[rec.SetInput], list[personal.SessionPerf]]:
    sets: list[rec.SetInput] = []
    perfs: list[personal.SessionPerf] = []
    for sess in sessions:
        by: dict[str, list[tuple[float, int, float | None]]] = {}
        for ls in sess.sets:
            if ls.reps <= 0:
                continue
            w = synth.WEIGHTS[ls.exercise]
            sets.append(
                rec.SetInput(at=ls.at, muscles=w, reps=ls.reps, weight_kg=ls.weight_kg, rpe=ls.rpe)
            )
            by.setdefault(ls.exercise, []).append((ls.weight_kg, ls.reps, ls.rpe))
        for ex, lst in by.items():
            e = personal.session_e1rm(lst)
            if e:
                perfs.append(personal.SessionPerf(ex, sess.start, e, synth.WEIGHTS[ex]))
    return sets, perfs


def test_session_e1rm_uses_rir() -> None:
    # 100 kg x 5 @ RPE 8 -> Epley(100, 7) = 123.3; without RPE RIR 2 is assumed too
    assert personal.session_e1rm([(100.0, 5, 8.0)]) == 100 * (1 + 7 / 30)
    assert personal.session_e1rm([(100.0, 5, None)]) == 100 * (1 + 7 / 30)
    assert personal.session_e1rm([(0.0, 5, 8.0), (50.0, 20, None)]) is None


def test_primary_group() -> None:
    assert personal.primary_group(BENCH) == "Push"
    assert personal.primary_group({"vastus_lateralis": 1.0, "gluteus_maximus": 1.0}) == "Legs"
    assert personal.primary_group({"unknown": 1.0}) is None


def test_no_data_keeps_the_population_value() -> None:
    fits = personal.fit([], [])
    assert {f.group for f in fits} == set(rec.GROUPS)
    assert all(f.k == 1.0 and not f.personal for f in fits)


def test_too_few_observations_keep_k_1() -> None:
    perfs = [personal.SessionPerf("Bench", T0 + timedelta(days=i), 100.0, BENCH) for i in range(3)]
    fit = {f.group: f for f in personal.fit(perfs, [])}
    assert fit["Push"].k == 1.0 and fit["Push"].personal is False


def test_recovers_a_known_k_on_a_frequent_synthetic_lifter() -> None:
    rng = random.Random(7)
    user = synth.make_user(rng, 0, frequent=True)
    user.noise_sd, user.rpe_sd, user.sleep_effect = 0.005, 0.25, 0.0
    sets, perfs = inputs(synth.simulate_self_coached(user, rng, days=150))
    fits = {f.group: f for f in personal.fit(perfs, rec.contributions(sets))}
    errors = [abs(fits[g].k - user.k_true[g]) for g in ("Push", "Pull", "Legs")]
    prior = [abs(1.0 - user.k_true[g]) for g in ("Push", "Pull", "Legs")]
    assert sum(errors) < sum(prior)
    assert max(errors) < 0.2
    for g in ("Push", "Pull", "Legs"):
        assert fits[g].k_low <= fits[g].k <= fits[g].k_high


@settings(max_examples=40, deadline=None)
@given(
    st.lists(
        st.tuples(st.integers(0, 120), st.floats(20, 200), st.floats(0.5, 3.0)),
        min_size=0,
        max_size=40,
    )
)
def test_k_is_always_in_range(points) -> None:
    perfs = [personal.SessionPerf("Bench", T0 + timedelta(days=d), e, BENCH) for d, e, _ in points]
    contribs = [
        rec.Contribution("pec_major_sternal", es, T0 + timedelta(days=d, hours=-30))
        for d, _, es in points
    ]
    for f in personal.fit(perfs, contribs):
        assert rec.K_MIN <= f.k <= rec.K_MAX
        assert f.k == f.k
        assert f.alpha is None or 0 <= f.alpha <= 0.3 + 1e-9
