"""Progression evaluation (prog-v1 vs baselines) on synthetic users. See
docs/ai/evaluation.md for the method and the numbers.

    cd services/sidecar && uv run python -m eval.progression_eval --users 60 --seed 2026
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from pathlib import Path

from app.modules.intelligence import progression as prog
from app.modules.intelligence import recovery as rec
from eval import synth

Policy = Callable[[str, list[synth.Session], datetime, int], synth.Prescription | None]


def info(ex: str) -> prog.ExerciseInfo:
    return prog.ExerciseInfo(
        name=ex,
        equipment=synth.EQUIPMENT.get(ex, "barbell"),
        measure="reps",
        mechanic="isolation" if ex in synth.ISOLATION else "compound",
        pattern=synth.PATTERN.get(ex, "other"),
        rep_low=6,
        rep_high=12,
    )


def history(ex: str, sessions: Sequence[synth.Session]) -> list[prog.SessionRec]:
    out = []
    for s in sessions:
        sets = tuple(
            prog.SetRec(ls.reps, ls.weight_kg, ls.rpe) for ls in s.sets if ls.exercise == ex
        )
        if sets:
            out.append(prog.SessionRec(s.start, sets))
    return out


def readiness(ex: str, sessions: Sequence[synth.Session], now: datetime) -> float | None:
    since = now - timedelta(days=rec.LOOKBACK_DAYS)
    sets = [
        rec.SetInput(
            at=ls.at,
            muscles=synth.WEIGHTS[ls.exercise],
            reps=ls.reps,
            weight_kg=ls.weight_kg,
            rpe=ls.rpe,
        )
        for s in sessions
        if s.start >= since
        for ls in s.sets
        if ls.reps > 0
    ]
    prim = [m for m, w in synth.WEIGHTS[ex].items() if w >= 1.0]
    states = {m.key: m.readiness for m in rec.compute(sets, now)}
    return min(states[m] for m in prim) if prim else None


def engine_policy(use_readiness: bool = True) -> Policy:
    def policy(ex: str, sessions: list[synth.Session], now: datetime, uid: int):
        hist = history(ex, sessions)
        r = readiness(ex, sessions, now) if use_readiness and hist else None
        t = prog.next_target(info(ex), hist, now, readiness=r)
        if t.change == "first" or t.reps is None:
            return None
        return synth.Prescription(t.weight_kg, t.reps, 3, t.stall.stalled)

    return policy


def repeat_last(ex: str, sessions: list[synth.Session], now: datetime, uid: int):
    hist = history(ex, sessions)
    if not hist:
        return None
    last = hist[-1]
    reps = [x.reps for x in last.sets if x.reps > 0] or [8]
    return synth.Prescription(max(x.weight_kg for x in last.sets), min(reps))


def fixed_increment(ex: str, sessions: list[synth.Session], now: datetime, uid: int):
    hist = history(ex, sessions)
    if not hist:
        return None
    load = max(x.weight_kg for x in hist[-1].sets)
    return synth.Prescription(load + synth.increment(ex), 8)


def linear_with_reset(ex: str, sessions: list[synth.Session], now: datetime, uid: int):
    """Classic novice linear progression: +1 increment after a session where every set hit
    8 reps; after a missed session, repeat; after two missed sessions in a row, -10 %."""
    hist = history(ex, sessions)
    if not hist:
        return None
    load = max(x.weight_kg for x in hist[-1].sets)
    missed = [min(x.reps for x in s.sets) < 8 for s in hist[-2:]]
    if not missed[-1]:
        return synth.Prescription(load + synth.increment(ex), 8)
    if len(missed) == 2 and all(missed):
        return synth.Prescription(synth.round_to(load * 0.9, 1.25), 8)
    return synth.Prescription(load, 8)


POLICIES: dict[str, Policy] = {
    "prog-v1": engine_policy(True),
    "prog-v1 (no recovery input)": engine_policy(False),
    "repeat last session": repeat_last,
    "fixed +2.5 kg (5 kg lower body)": fixed_increment,
    "linear +2.5 kg with resets": linear_with_reset,
}


def prescription_metrics(exps: Sequence[synth.Exposure]) -> dict[str, object]:
    """Over prescribed exposures (not each exercise's first, which the user picks)."""
    rx = [e for e in exps if e.index >= 1]
    sets = [(e, a) for e in rx for a in e.achieved]
    within1 = sum(1 for e, a in sets if a >= e.target_reps - 1) / len(sets)
    exact = sum(1 for e, a in sets if a >= e.target_reps) / len(sets)
    # realised RIR of the first prescribed set: true reps possible - prescribed reps
    rir = [e.possible_first - e.target_reps for e in rx]
    err = [r - prog.TARGET_RIR for r in rir]
    load_err = [100 * (e.load - e.ideal_load) / e.ideal_load for e in rx]
    return {
        "exposures": len(rx),
        "sets": len(sets),
        "hit_within_1_rep": round(within1, 3),
        "hit_exact": round(exact, 3),
        "rir_error_mean": round(statistics.mean(err), 2),
        "rir_error_mae": round(statistics.mean(abs(x) for x in err), 2),
        "too_hard_share": round(sum(1 for r in rir if r < 0) / len(rir), 3),
        "too_easy_share": round(sum(1 for r in rir if r > 4) / len(rir), 3),
        "load_error_mean_pct": round(statistics.mean(load_err), 2),
        "load_error_mae_pct": round(statistics.mean(abs(x) for x in load_err), 2),
    }


FLAT_GAIN = 0.01  # under 1 % true gain in 4 weeks: truly stalled
CLEAR_GAIN = 0.02  # 2 % or more in 4 weeks: clearly progressing


def stall_metrics(exps: Sequence[synth.Exposure], window: int = 8) -> dict[str, float]:
    """Event level, against the simulator's truth. A true stall episode starts when the
    true 4-week strength gain falls under 1 % (an injected plateau or natural saturation)
    and lasts while it stays there; it is detected when the engine flags a stall within
    `window` exposures of its start. A flag while the true 4-week gain is 2 % or more is a
    false alarm (one per run of consecutive flags). Between 1 and 2 % is a grey zone that
    counts neither way."""
    by: dict[tuple[int, str], list[synth.Exposure]] = {}
    for e in exps:
        by.setdefault((e.user, e.exercise), []).append(e)
    tp = fn = fa = 0
    delays: list[int] = []
    clear_exposures = 0
    for series in by.values():
        series.sort(key=lambda e: e.index)
        prev_false = False
        i = 0
        while i < len(series):
            e = series[i]
            if e.gain_4w >= CLEAR_GAIN:
                clear_exposures += 1
                if e.flagged_stall and not prev_false:
                    fa += 1
                prev_false = e.flagged_stall
            else:
                prev_false = False
            if e.gain_4w < FLAT_GAIN and (i == 0 or series[i - 1].gain_4w >= FLAT_GAIN):
                # start of a flat episode; skip the first 4 weeks (no 4-week history yet)
                if e.start - series[0].start >= timedelta(days=28) and len(series) - i >= window:
                    hit = next(
                        (j - i for j in range(i, i + window) if series[j].flagged_stall), None
                    )
                    if hit is None:
                        fn += 1
                    else:
                        tp += 1
                        delays.append(hit)
            i += 1
    precision = tp / (tp + fa) if tp + fa else float("nan")
    recall = tp / (tp + fn) if tp + fn else float("nan")
    return {
        "true_stalls": tp + fn,
        "detected": tp,
        "missed": fn,
        "false_alarms": fa,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "median_delay_exposures": statistics.median(delays) if delays else float("nan"),
        "false_alarms_per_100_progressing_exposures": round(100 * fa / max(1, clear_exposures), 2),
    }


def run(users: int, seed: int, days: int) -> dict[str, object]:
    out: dict[str, object] = {"users": users, "seed": seed, "days": days, "policies": {}}
    for name, policy in POLICIES.items():
        rng = random.Random(seed)  # same users and the same noise draws for every policy
        exps: list[synth.Exposure] = []
        for uid in range(users):
            user = synth.make_user(rng, uid, stalls=True)
            exps += synth.simulate_policy(user, rng, policy, days)
        metrics: dict[str, object] = prescription_metrics(exps)
        logs = [e for e in exps if e.rpe_log_prob >= 0.9]
        no = [e for e in exps if e.rpe_log_prob == 0.0]
        metrics["rpe_loggers"] = prescription_metrics(logs) if logs else {}
        metrics["no_rpe"] = prescription_metrics(no) if no else {}
        if name.startswith("prog-v1"):
            metrics.update({"stall_" + k: v for k, v in stall_metrics(exps).items()})
        out["policies"][name] = metrics  # type: ignore[index]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=60)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--days", type=int, default=182)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    res = run(a.users, a.seed, a.days)
    text = json.dumps(res, indent=2)
    print(text)
    if a.out:
        a.out.write_text(text + "\n")


if __name__ == "__main__":
    main()
