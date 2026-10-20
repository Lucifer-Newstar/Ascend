"""Recovery evaluation: recovery-v2 (population and personal) against a fixed 48-hour
rule, on synthetic users whose true readiness is known. See docs/ai/evaluation.md.

    cd services/sidecar && uv run python -m eval.recovery_eval --users 40 --seed 2026
"""

from __future__ import annotations

import argparse
import bisect
import json
import math
import random
import statistics
from collections.abc import Sequence
from datetime import datetime, timedelta
from pathlib import Path

from app.modules.intelligence import personal
from app.modules.intelligence import recovery as rec
from app.modules.progress.taxonomy import MUSCLE_BY_KEY
from eval import synth

DAYS = 365
WARMUP_DAYS = 56  # personal factors start from the population value; skip the first 8 weeks
REFIT_DAYS = 28
TRAINED_WITHIN = timedelta(days=7)  # only (session, muscle) pairs with recent load count
FIXED_HOURS = 48.0
METHODS = ("fixed 48 h", "recovery-v2 population", "recovery-v2 personal")


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float:
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else float("nan")


def ranks(xs: Sequence[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    out = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for t in range(i, j + 1):
            out[order[t]] = (i + j) / 2
        i = j + 1
    return out


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float:
    return pearson(ranks(xs), ranks(ys))


def calibration(pred: Sequence[float], true: Sequence[float], bins: int = 10) -> dict[str, object]:
    edges = [i / bins for i in range(bins + 1)]
    rows = []
    ece = 0.0
    for b in range(bins):
        lo, hi = edges[b], edges[b + 1]
        idx = [i for i, p in enumerate(pred) if lo <= p < hi or (b == bins - 1 and p == 1.0)]
        if not idx:
            continue
        mp = statistics.fmean(pred[i] for i in idx)
        mt = statistics.fmean(true[i] for i in idx)
        rows.append(
            {
                "bin": f"{lo:.1f}-{hi:.1f}",
                "n": len(idx),
                "mean_pred": round(mp, 3),
                "mean_true": round(mt, 3),
            }
        )
        ece += len(idx) / len(pred) * abs(mp - mt)
    return {"ece": round(ece, 4), "bins": rows}


def fixed_rule(last: datetime | None, now: datetime) -> float:
    """The common "48 hours per muscle" rule as a readiness: 0 right after training,
    rising linearly to 1 at 48 h."""
    if last is None:
        return 1.0
    return min(1.0, max(0.0, (now - last).total_seconds() / 3600 / FIXED_HOURS))


def set_inputs(sessions: Sequence[synth.Session]) -> list[rec.SetInput]:
    return [
        rec.SetInput(
            at=ls.at,
            muscles=synth.WEIGHTS[ls.exercise],
            reps=ls.reps,
            weight_kg=ls.weight_kg,
            rpe=ls.rpe,
        )
        for s in sessions
        for ls in s.sets
        if ls.reps > 0
    ]


def perfs_of(sessions: Sequence[synth.Session]) -> list[personal.SessionPerf]:
    out = []
    for s in sessions:
        by: dict[str, list[tuple[float, int, float | None]]] = {}
        for ls in s.sets:
            if ls.reps > 0:
                by.setdefault(ls.exercise, []).append((ls.weight_kg, ls.reps, ls.rpe))
        for ex, lst in by.items():
            e = personal.session_e1rm(lst)
            if e:
                out.append(personal.SessionPerf(ex, s.start, e, synth.WEIGHTS[ex]))
    return out


def evaluate_user(user: synth.User, rng: random.Random) -> dict[str, object]:
    sessions = synth.simulate_self_coached(user, rng, DAYS)
    sets = set_inputs(sessions)
    contribs = rec.contributions(sets)
    contribs.sort(key=lambda c: c.at)
    times = [c.at for c in contribs]
    perfs = perfs_of(sessions)
    last_hit: dict[str, list[datetime]] = {}
    for st in sorted(sets, key=lambda x: x.at):
        for m, w in st.muscles.items():
            if w >= 0.5:
                last_hit.setdefault(m, []).append(st.at)
    k_by_block: dict[int, dict[str, float]] = {}
    pairs: dict[str, list[float]] = {m: [] for m in METHODS}
    truth: list[float] = []
    perf_pairs: dict[str, list[float]] = {m: [] for m in METHODS}
    perf_truth: list[float] = []
    start0 = sessions[0].start
    for s in sessions:
        day = (s.start - start0).days
        if day < WARMUP_DAYS:
            continue
        block = day // REFIT_DAYS
        if block not in k_by_block:
            cut = start0 + timedelta(days=block * REFIT_DAYS)
            i = bisect.bisect_left(times, cut)
            fits = personal.fit([p for p in perfs if p.start < cut], contribs[:i])
            k_by_block[block] = {f.group: f.k for f in fits}
        window_lo = bisect.bisect_left(times, s.start - timedelta(days=rec.LOOKBACK_DAYS))
        window_hi = bisect.bisect_left(times, s.start)
        recent = contribs[window_lo:window_hi]
        checkin = rec.CheckinInput(s.sleep, s.soreness) if s.checkin_logged else None
        pop = {m.key: m.readiness for m in rec.compute_from(recent, s.start, None, checkin)}
        mine = {
            m.key: m.readiness
            for m in rec.compute_from(recent, s.start, k_by_block[block], checkin)
        }
        fixed: dict[str, float] = {}
        for m in MUSCLE_BY_KEY:
            hits = last_hit.get(m, [])
            j = bisect.bisect_left(hits, s.start)
            last = hits[j - 1] if j else None
            fixed[m] = fixed_rule(last, s.start)
            if last is not None and s.start - last <= TRAINED_WITHIN:
                truth.append(s.true_readiness[m])
                pairs["fixed 48 h"].append(fixed[m])
                pairs["recovery-v2 population"].append(pop[m])
                pairs["recovery-v2 personal"].append(mine[m])
        # Does the readiness of an exercise's primary muscles track today's true capacity?
        for ex in s.exercises:
            prim = [m for m, w in synth.WEIGHTS[ex].items() if w >= 1.0]
            perf_truth.append(s.true_capacity[ex] / s.true_strength[ex])
            for name, table in (
                ("fixed 48 h", fixed),
                ("recovery-v2 population", pop),
                ("recovery-v2 personal", mine),
            ):
                perf_pairs[name].append(statistics.fmean(table[m] for m in prim))
    final = {f.group: f for f in personal.fit(perfs, contribs)}
    return {
        "pairs": pairs,
        "truth": truth,
        "perf_pairs": perf_pairs,
        "perf_truth": perf_truth,
        "k_err": {
            g: (final[g].k - user.k_true[g], 1.0 - user.k_true[g], final[g].personal) for g in final
        },
    }


def run(users: int, seed: int) -> dict[str, object]:
    rng = random.Random(seed)
    cohorts = {"typical": False, "frequent": True}
    out: dict[str, object] = {"users": users, "seed": seed, "days": DAYS, "cohorts": {}}
    for cname, frequent in cohorts.items():
        pairs: dict[str, list[float]] = {m: [] for m in METHODS}
        truth: list[float] = []
        perf_pairs: dict[str, list[float]] = {m: [] for m in METHODS}
        perf_truth: list[float] = []
        k_pers: list[float] = []
        k_prior: list[float] = []
        n_personal = 0
        n_groups = 0
        for uid in range(users):
            kernel = "delayed" if uid % 4 == 3 else "exp"
            u = synth.make_user(rng, uid, kernel_kind=kernel, frequent=frequent)  # type: ignore[arg-type]
            r = evaluate_user(u, rng)
            for m in METHODS:
                pairs[m] += r["pairs"][m]  # type: ignore[index]
                perf_pairs[m] += r["perf_pairs"][m]  # type: ignore[index]
            truth += r["truth"]  # type: ignore[arg-type]
            perf_truth += r["perf_truth"]  # type: ignore[arg-type]
            for _g, (e_pers, e_prior, is_personal) in r["k_err"].items():  # type: ignore[attr-defined]
                k_pers.append(abs(e_pers))
                k_prior.append(abs(e_prior))
                n_groups += 1
                n_personal += int(is_personal)
        res: dict[str, object] = {"pairs": len(truth), "exposures": len(perf_truth), "methods": {}}
        for m in METHODS:
            p = pairs[m]
            res["methods"][m] = {  # type: ignore[index]
                "pearson_r": round(pearson(p, truth), 3),
                "spearman_rho": round(spearman(p, truth), 3),
                "mae": round(
                    statistics.fmean(abs(a - b) for a, b in zip(p, truth, strict=True)), 4
                ),
                "calibration": calibration(p, truth),
                "capacity_pearson_r": round(pearson(perf_pairs[m], perf_truth), 3),
            }
        res["k_mae_personal"] = round(statistics.fmean(k_pers), 3)
        res["k_mae_prior"] = round(statistics.fmean(k_prior), 3)
        res["groups_personalised"] = f"{n_personal}/{n_groups}"
        out["cohorts"][cname] = res  # type: ignore[index]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=40)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    res = run(a.users, a.seed)
    text = json.dumps(res, indent=2)
    print(text)
    if a.out:
        a.out.write_text(text + "\n")


if __name__ == "__main__":
    main()
