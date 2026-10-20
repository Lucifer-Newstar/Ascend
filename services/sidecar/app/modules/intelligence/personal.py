"""Personal recovery factors k_g for recovery-v2 (ADR-0014, backlog AI-3).

The prior half-lives in taxonomy.py fit an "average" lifter. Some people recover a
muscle group faster or slower, and the signal ASCEND has for that is performance: if your
bench is lower whenever the chest was still fatigued, the decay rate that makes "fatigue
at the start of the session" best explain the dips is your decay rate.

Observations, one per exercise per session (lifts with a usable e1RM only):

    y_s    log of the session's mean RIR-adjusted Epley e1RM: Epley(load, reps + RIR)
           over sets of at most 12 reps (RIR = 10 - RPE; RIR 2 assumed without RPE)
    phi_s  fatigue fraction of the exercise's primary muscles at the session start, from
           sets logged BEFORE the session: sum_m w_m min(1, F_m / C_m) / sum_m w_m

Model per muscle group g, jointly over the group's exercises:

    y_s = trend_e(t_s) - alpha x phi_s(k) + noise

where trend_e is a piecewise-linear curve per exercise (knots every 6 weeks), so strength
gains are not mistaken for recovery. Both y and phi are first residualised on the trend
basis (Frisch-Waugh-Lovell), which leaves a one-parameter regression for every k.

The estimate is a grid posterior: k on 0.6-1.6 (step 0.05), alpha on 0-0.3, Gaussian
errors with the variance of the best fit, a log-normal prior on k centred on the
population value 1 (sd 0.25 in log units) and a flat prior on alpha. k_g is the posterior
mean, reported with a 90 % interval. With little information the posterior is the prior
and k_g stays near 1; that is the shrinkage, done by the data rather than a fixed count.
Below MIN_OBS informative observations (phi > 0.05 at k = 1) the group keeps k = 1.
`shrink_simple` is the backlog's count-based shrinkage, kept for the evaluation.
"""

from __future__ import annotations

import bisect
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from app.modules.intelligence import recovery as rec
from app.modules.progress.taxonomy import MUSCLE_BY_KEY

ALGO_VERSION = "recovery-k-v1"
K_GRID: tuple[float, ...] = tuple(round(0.6 + 0.05 * i, 2) for i in range(21))
ALPHA_GRID: tuple[float, ...] = tuple(round(0.025 * i, 3) for i in range(13))
PRIOR_SD = 0.25
N0 = 6.0
MIN_OBS = 4
MIN_SESSIONS_PER_EXERCISE = 4
INFORMATIVE_PHI = 0.05
KNOT_WEEKS = 6.0
_LN2 = math.log(2.0)
LOOKBACK_H = 336.0  # 14 days: even at k = 1.6 the slowest muscles are below 5 % by then


@dataclass(frozen=True)
class SessionPerf:
    """Mean e1RM of one exercise in one session, with the session's start time."""

    exercise: str
    start: datetime
    e1rm: float
    muscles: Mapping[str, float]


@dataclass(frozen=True)
class Observation:
    group: str
    exercise: str
    start: datetime
    y: float  # log e1RM
    # per primary muscle: (weight share, prior half-life, ((hours before, ES / capacity), ...))
    parts: tuple[tuple[float, float, tuple[tuple[float, float], ...]], ...]

    def phi(self, k: float) -> float:
        """Fatigue fraction at the session start, saturating at 1 like readiness does."""
        total = 0.0
        for share, hl, items in self.parts:
            c = -_LN2 / (hl * k)
            f = sum(v * math.exp(c * h) for h, v in items)
            total += share * min(1.0, f)
        return total


@dataclass(frozen=True)
class GroupFit:
    group: str
    k: float  # what the engine uses
    k_hat: float | None  # the best-fitting grid value (None when not fitted)
    n: int  # informative observations
    alpha: float | None  # log-performance lost by a fully fatigued muscle
    personal: bool
    k_low: float  # 90 % credible interval
    k_high: float


def session_e1rm(sets: Iterable[tuple[float, int, float | None]]) -> float | None:
    """Mean RIR-adjusted Epley e1RM over a session's usable (load, reps, rpe) sets."""
    vals: list[float] = []
    for load, reps, rpe in sets:
        if load <= 0 or reps < 1 or reps > rec.MAX_E1RM_REPS:
            continue
        rir = rec.DEFAULT_RIR if rpe is None else rec.clamp(10.0 - rpe, 0.0, 10.0)
        total = reps + rir
        vals.append(load if total <= 1 else load * (1 + total / 30))
    return sum(vals) / len(vals) if vals else None


def primary_group(muscles: Mapping[str, float]) -> str | None:
    known = [(w, k) for k, w in muscles.items() if k in MUSCLE_BY_KEY]
    if not known:
        return None
    top = max(w for w, _ in known)
    first = sorted(k for w, k in known if w == top)[0]
    return MUSCLE_BY_KEY[first].group


def observations(
    perfs: Sequence[SessionPerf], contribs: Sequence[rec.Contribution]
) -> list[Observation]:
    # Per muscle: contribution times (hours since an epoch, sorted) and ES / capacity.
    epoch = min([c.at for c in contribs] + [p.start for p in perfs], default=datetime(2000, 1, 1))
    by_muscle: dict[str, tuple[list[float], list[float]]] = {}
    for c in sorted(contribs, key=lambda c: c.at):
        mus = MUSCLE_BY_KEY.get(c.muscle)
        if mus is None:
            continue
        ts, vs = by_muscle.setdefault(c.muscle, ([], []))
        ts.append((c.at - epoch).total_seconds() / 3600)
        vs.append(c.es / mus.capacity_es)
    out: list[Observation] = []
    for p in perfs:
        group = primary_group(p.muscles)
        if group is None or p.e1rm <= 0:
            continue
        start_h = (p.start - epoch).total_seconds() / 3600
        prim = {m: w for m, w in p.muscles.items() if w >= 1.0 and m in MUSCLE_BY_KEY}
        total_w = sum(prim.values()) or 1.0
        parts: list[tuple[float, float, tuple[tuple[float, float], ...]]] = []
        for m, w in sorted(prim.items()):
            ts, vs = by_muscle.get(m, ([], []))
            lo = bisect.bisect_left(ts, start_h - LOOKBACK_H)
            hi = bisect.bisect_left(ts, start_h)  # strictly before the session start
            # Sets of one session sit minutes apart: bucket by half hour (error < 1 %).
            buckets: dict[float, float] = {}
            for i in range(lo, hi):
                key = round((start_h - ts[i]) * 2) / 2 or 0.5
                buckets[key] = buckets.get(key, 0.0) + vs[i]
            parts.append((w / total_w, MUSCLE_BY_KEY[m].half_life_h, tuple(buckets.items())))
        out.append(Observation(group, p.exercise, p.start, math.log(p.e1rm), tuple(parts)))
    return out


# --- linear algebra for the trend basis (tiny, so plain Python) -------------------------


def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    """Gauss-Jordan with partial pivoting and a small ridge for stability."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for i in range(n):
        m[i][i] += 1e-9
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        m[col], m[piv] = m[piv], m[col]
        d = m[col][col]
        if abs(d) < 1e-15:
            continue
        for j in range(col, n + 1):
            m[col][j] /= d
        for r in range(n):
            if r != col and m[r][col] != 0.0:
                f = m[r][col]
                for j in range(col, n + 1):
                    m[r][j] -= f * m[col][j]
    return [m[i][n] for i in range(n)]


def _basis(ts: Sequence[float]) -> list[list[float]]:
    """Piecewise-linear (hat function) basis on knots every KNOT_WEEKS over ts (weeks)."""
    lo, hi = min(ts), max(ts)
    n_knots = max(2, int(math.ceil((hi - lo) / KNOT_WEEKS)) + 1)
    step = (hi - lo) / (n_knots - 1) if hi > lo else 1.0
    knots = [lo + i * step for i in range(n_knots)]
    rows = []
    for t in ts:
        row = []
        for j, kt in enumerate(knots):
            left = knots[j - 1] if j > 0 else None
            right = knots[j + 1] if j + 1 < n_knots else None
            if t == kt or (left is None and t < kt) or (right is None and t > kt):
                v = 1.0
            elif left is not None and left < t < kt:
                v = (t - left) / (kt - left)
            elif right is not None and kt < t < right:
                v = (right - t) / (right - kt)
            else:
                v = 0.0
            row.append(v)
        rows.append(row)
    return rows


class _Residualiser:
    """Projects vectors off one exercise's trend basis: r = v - B (B'B)^-1 B' v."""

    def __init__(self, ts: Sequence[float]) -> None:
        self.b = _basis(ts)
        p = len(self.b[0])
        self.btb = [[sum(row[i] * row[j] for row in self.b) for j in range(p)] for i in range(p)]

    def __call__(self, v: Sequence[float]) -> list[float]:
        p = len(self.b[0])
        btv = [sum(row[i] * x for row, x in zip(self.b, v, strict=True)) for i in range(p)]
        coef = _solve(self.btb, btv)
        return [
            x - sum(c * r for c, r in zip(coef, row, strict=True))
            for row, x in zip(self.b, v, strict=True)
        ]


def _log_prior(k: float) -> float:
    return -0.5 * (math.log(k) / PRIOR_SD) ** 2


def _interval(post: Mapping[float, float], mass: float = 0.9) -> tuple[float, float]:
    tail = (1 - mass) / 2
    acc = 0.0
    lo = hi = None
    for k in K_GRID:
        acc += post.get(k, 0.0)
        if lo is None and acc >= tail:
            lo = k
        if hi is None and acc >= 1 - tail:
            hi = k
    return lo if lo is not None else K_GRID[0], hi if hi is not None else K_GRID[-1]


def fit_group(group: str, obs: Sequence[Observation]) -> GroupFit:
    mine = [o for o in obs if o.group == group]
    series: dict[str, list[Observation]] = {}
    for o in mine:
        series.setdefault(o.exercise, []).append(o)
    usable = {e: sorted(v, key=lambda o: o.start) for e, v in series.items()}
    usable = {e: v for e, v in usable.items() if len(v) >= MIN_SESSIONS_PER_EXERCISE}
    flat = [o for v in usable.values() for o in v]
    n = sum(1 for o in flat if o.phi(1.0) > INFORMATIVE_PHI)
    if n < MIN_OBS:
        return GroupFit(group, 1.0, None, n, None, False, 1.0, 1.0)
    t0 = min(o.start for o in flat)
    resid = {
        e: _Residualiser([(o.start - t0).total_seconds() / 604800 for o in v])
        for e, v in usable.items()
    }
    y_res: list[float] = []
    for name, v in usable.items():
        y_res += resid[name]([o.y for o in v])
    syy = sum(y * y for y in y_res)
    dof = max(1, len(flat) - sum(len(r.b[0]) for r in resid.values()) - 1)
    table: list[tuple[float, float, float]] = []
    for k in K_GRID:
        x_res: list[float] = []
        for name, v in usable.items():
            x_res += resid[name]([o.phi(k) for o in v])
        sxx = sum(x * x for x in x_res)
        sxy = sum(x * y for x, y in zip(x_res, y_res, strict=True))
        for alpha in ALPHA_GRID:
            # sum (y + alpha x)^2, expanded so each alpha costs O(1)
            table.append((k, alpha, syy + 2 * alpha * sxy + alpha * alpha * sxx))
    best_k, _, best_sse = min(table, key=lambda r: r[2])
    sigma2 = max(best_sse / dof, 1e-8)
    logp = [(k, a, -sse / (2 * sigma2) + _log_prior(k)) for k, a, sse in table]
    top = max(lp for _, _, lp in logp)
    w_k: dict[float, float] = {}
    w_sum = 0.0
    alpha_acc = 0.0
    for k, a, lp in logp:
        w = math.exp(lp - top)
        w_k[k] = w_k.get(k, 0.0) + w
        w_sum += w
        alpha_acc += a * w
    post = {k: w / w_sum for k, w in w_k.items()}
    k_mean = sum(k * w for k, w in post.items())
    lo, hi = _interval(post)
    return GroupFit(
        group=group,
        k=round(rec.clamp(k_mean, rec.K_MIN, rec.K_MAX), 3),
        k_hat=best_k,
        n=n,
        alpha=round(alpha_acc / w_sum, 4),
        personal=True,
        k_low=lo,
        k_high=hi,
    )


def fit(perfs: Sequence[SessionPerf], contribs: Sequence[rec.Contribution]) -> list[GroupFit]:
    obs = observations(perfs, contribs)
    return [fit_group(g, obs) for g in rec.GROUPS]


def shrink_simple(fit_: GroupFit) -> float:
    """The backlog's count-based shrinkage k = (n k_hat + N0) / (n + N0), for comparison."""
    if fit_.k_hat is None:
        return 1.0
    return rec.clamp((fit_.n * fit_.k_hat + N0) / (fit_.n + N0), rec.K_MIN, rec.K_MAX)
