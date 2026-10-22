"""Skill progress engine: pure functions from logged sets to tree state.

Deterministic for the same sets and `now`. Version: ENGINE_VERSION.

Session      all sets of one exercise on one calendar day.
Score        for a criterion "S x T" (S sets of T reps or T seconds, optionally with at
             least K kg added): take the session's S best qualifying sets and average
             min(1, value / T); missing sets count as 0. So 3 sets of 8, 8, 6 against
             3x8 scores (1 + 1 + 0.75) / 3 = 0.92.
Window       only sessions in the last WINDOW_DAYS count (recency).
Met          a session scoring 1.0. A criterion is MET after CONFIRM_SESSIONS such
             sessions in the window (consistency: one lucky day is not enough).
Progress     criterion % = 90 x best score + 10 x min(1, met sessions / CONFIRM_SESSIONS);
             a step's % is the mean over its criteria.
Unlock       a step unlocks when every criterion is met and the steps it requires are
             unlocked. Entry steps (no criteria) start unlocked. Unlocks are kept once
             earned (the service stores them); losing form later shows as "rusty".
Plausibility holds longer than catalog.plausible_hold_limit() are ignored and counted.
ETA          only with >= ETA_MIN_SESSIONS sessions spanning >= ETA_MIN_SPAN_DAYS for
             every criterion: a least-squares line through session scores over time,
             extrapolated to 1.0 plus the confirming session. An ESTIMATE, labelled so.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from app.modules.skills.catalog import Criterion, Skill, Step, plausible_hold_limit

ENGINE_VERSION = "skills-v1"
WINDOW_DAYS = 42
CONFIRM_SESSIONS = 2
RUSTY_AFTER_DAYS = 28
ETA_MIN_SESSIONS = 3
ETA_MIN_SPAN_DAYS = 7
ETA_MAX_DAYS = 365
ETA_MIN_SLOPE = 0.002  # score per day; flatter than this is "no clear trend"


@dataclass(frozen=True)
class SetRecord:
    set_id: int
    exercise: str
    performed_at: datetime
    reps: int
    duration_s: int | None
    weight_kg: float


@dataclass
class CriterionResult:
    criterion: Criterion
    best_score: float = 0.0
    best_value: int | None = None
    sessions_met: int = 0
    pct: float = 0.0
    met: bool = False
    evidence: list[int] = field(default_factory=list)
    ignored_sets: int = 0
    sessions: list[tuple[date, float]] = field(default_factory=list)


@dataclass
class StepResult:
    step: Step
    status: str  # unlocked | next | locked
    pct: float
    criteria: list[CriterionResult]
    eligible: bool
    unlocked_at: datetime | None = None


@dataclass
class Eta:
    days: float | None
    reason: str


@dataclass
class SkillResult:
    skill: Skill
    steps: list[StepResult]
    current: Step | None
    next: StepResult | None
    acquired: bool
    eta: Eta
    last_trained: datetime | None
    sessions_28d: int
    rusty: bool


def _value(r: SetRecord, c: Criterion) -> int | None:
    if r.weight_kg + 1e-9 < c.added_kg:
        return None
    if c.is_hold:
        return r.duration_s or None
    return r.reps


def evaluate_criterion(
    c: Criterion, records: Iterable[SetRecord], now: datetime, window_days: int = WINDOW_DAYS
) -> CriterionResult:
    start = now - timedelta(days=window_days)
    by_day: dict[date, list[tuple[int, int]]] = defaultdict(list)
    res = CriterionResult(c)
    limit = plausible_hold_limit(c.exercise)
    for r in records:
        if r.exercise != c.exercise or not (start <= r.performed_at <= now):
            continue
        v = _value(r, c)
        if v is None:
            continue
        if c.is_hold and v > limit:
            res.ignored_sets += 1
            continue
        by_day[r.performed_at.date()].append((v, r.set_id))
    met_days: list[date] = []
    for day in sorted(by_day):
        best = sorted(by_day[day], reverse=True)[: c.sets]
        score = sum(min(1.0, v / c.target) for v, _ in best) / c.sets
        res.sessions.append((day, score))
        top = best[0][0]
        if res.best_value is None or top > res.best_value:
            res.best_value = top
        if score > res.best_score:
            res.best_score = score
        if score >= 1.0 - 1e-9:
            met_days.append(day)
    res.sessions_met = len(met_days)
    res.met = res.sessions_met >= CONFIRM_SESSIONS
    res.pct = round(90 * res.best_score + 10 * min(1.0, res.sessions_met / CONFIRM_SESSIONS), 1)
    for day in met_days[-CONFIRM_SESSIONS:]:
        best = sorted(by_day[day], reverse=True)[: c.sets]
        res.evidence.extend(set_id for _, set_id in best)
    return res


def criterion_eta(res: CriterionResult) -> float | None:
    """Days until this criterion is met at the current trend, or None (not enough data)."""
    if res.met:
        return 0.0
    pts = res.sessions
    if len(pts) < ETA_MIN_SESSIONS or (pts[-1][0] - pts[0][0]).days < ETA_MIN_SPAN_DAYS:
        return None
    x0 = pts[0][0]
    xs = [(d - x0).days for d, _ in pts]
    ys = [s for _, s in pts]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    var = sum((x - mx) ** 2 for x in xs)
    if var == 0:
        return None
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / var
    if slope < ETA_MIN_SLOPE:
        return None
    fitted_last = my + slope * (xs[-1] - mx)
    days_to_full = max(0.0, (1.0 - fitted_last) / slope)
    # One more qualifying session confirms it; assume the user's own average gap.
    gap = (xs[-1] - xs[0]) / max(1, n - 1)
    extra = gap * max(0, CONFIRM_SESSIONS - res.sessions_met - (1 if days_to_full == 0 else 0))
    return days_to_full + extra


def step_eta(step: StepResult) -> Eta:
    if not step.criteria:
        return Eta(None, "nothing to unlock")
    days: list[float] = []
    for c in step.criteria:
        d = criterion_eta(c)
        if d is None:
            return Eta(
                None,
                f"not enough data yet: log {c.criterion.exercise} in at least "
                f"{ETA_MIN_SESSIONS} sessions over {ETA_MIN_SPAN_DAYS}+ days, with progress",
            )
        days.append(d)
    worst = max(days)
    if worst > ETA_MAX_DAYS:
        return Eta(None, "more than a year at the current rate")
    return Eta(round(worst, 1), "estimate from your recent trend")


def evaluate_skill(
    skill: Skill,
    records: Sequence[SetRecord],
    unlocked: dict[str, datetime],
    now: datetime,
) -> SkillResult:
    """Tree state. `unlocked` maps stored step keys to their unlock time; entry steps
    (no criteria) count as unlocked. Steps that are eligible but not stored yet are
    marked `eligible` (the service stores them, then evaluates again)."""
    have = dict(unlocked)
    results: list[StepResult] = []
    for step in skill.steps:
        crits = [evaluate_criterion(c, records, now) for c in step.unlock]
        pct = round(sum(c.pct for c in crits) / len(crits), 1) if crits else 100.0
        reqs = skill.requires_of(step)
        open_ = all(r in have for r in reqs)
        is_unlocked = step.key in have or not step.unlock
        if is_unlocked:
            status = "unlocked"
        elif open_:
            status = "next"
        else:
            status = "locked"
        eligible = (not is_unlocked) and open_ and all(c.met for c in crits)
        results.append(
            StepResult(
                step, status, 100.0 if is_unlocked else pct, crits, eligible, have.get(step.key)
            )
        )
        if not step.unlock:
            have.setdefault(step.key, now)
    unlocked_steps = [r.step for r in results if r.status == "unlocked"]
    frontier = [r for r in results if r.status == "next"]
    nxt = max(frontier, key=lambda r: r.pct) if frontier else None
    names = {s.exercise for s in skill.steps} | set(skill.feeders)
    mine = [r for r in records if r.exercise in names and r.performed_at <= now]
    last = max((r.performed_at for r in mine), default=None)
    month_ago = now - timedelta(days=28)
    sessions = {(r.exercise, r.performed_at.date()) for r in mine if r.performed_at >= month_ago}
    current = unlocked_steps[-1] if unlocked_steps else None
    rusty = False
    if current is not None:
        last_current = max(
            (r.performed_at for r in mine if r.exercise == current.exercise), default=None
        )
        rusty = last_current is not None and last_current < now - timedelta(days=RUSTY_AFTER_DAYS)
    return SkillResult(
        skill=skill,
        steps=results,
        current=current,
        next=nxt,
        acquired=skill.steps[-1].key in have,
        eta=step_eta(nxt) if nxt else Eta(None, "every step unlocked"),
        last_trained=last,
        sessions_28d=len({d for _, d in sessions}),
        rusty=rusty,
    )
