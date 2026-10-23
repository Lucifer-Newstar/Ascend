"""E2 progression engine, version prog-v1 (ADR-0015, backlog FT-1).

Pure functions: from one exercise's recent sessions to the next session's target, with a
reason code, a one-line "why", the formula and every input. No database, clock or I/O.

Working sets   the sets at the session's top load (within 85 %); warm-ups do not count.
Rep range      the exercise's own range when it is specific; the library's generic 6-12
               is replaced by a zone from your own history: every one of the last 6
               sessions at a median of 5 reps or fewer -> strength 3-6, all at 15 or more ->
               high-rep 12-20, otherwise 6-10 (compound) or 8-12 (isolation).
               Calisthenics use the skill-tree criterion when one applies.
Target effort  RPE 8 (2 reps in reserve), the common hypertrophy/strength default
               (Helms et al. 2016).
Increments     barbell 2.5 kg (5 kg for squats, hinges and lunges), dumbbell, cable,
               machine and EZ-bar 2.5 kg, kettlebell 4 kg; bodyweight moves add reps,
               seconds or the next ladder step. A step never adds more than 10 % of the load:
               when the smallest plate is bigger than that, reps go up to the top + 2 first.
e1RM           Epley with RIR: load x (1 + (reps + RIR) / 30), sets of at most 12 reps,
               RIR = 10 - RPE (no RPE: RIR 0, i.e. plain Epley as the PR detector uses).

Rules for a reps exercise, first match wins (L = last session's working sets):
  kept           you chose "keep mine" in the last 7 days -> repeat L
  stall_reset    stalled (below) -> load x 0.90, same reps: a per-lift deload
  below_twice    reps under the range two sessions running -> load x 0.925
  below_range    reps under the range once -> same load, aim for the bottom
  too_hard       RPE >= 9.5 on L -> repeat L before adding anything
  top_of_range   every set at the top (RPE <= 9 or unrated) -> + one increment, reps reset
                 to the bottom (double progression; Suchomel et al. 2021)
  too_easy       every set of L at RPE 7.5 or easier -> load from e1RM for L's reps at
                 RPE 8, at least one step and at most +10 %
  add_rep        otherwise same load, one more rep on the weakest set (up to the top)
  hold_recovering  any "up" target is held when the exercise's primary muscles are below
                 40 % recovered (recovery-v2), so the two engines never disagree. (60 % was
                 tried first; in the simulator it held so often that users without RPE
                 ended up 10+ reps above the target reserve, see docs/ai/evaluation.md.)
Holds use the same shape with seconds: +10 % (at least 2 s) toward the top or the
criterion; at the top they advance (next step, or +2.5 kg on a weighted hold).

Stall: in the current cycle (since the last load drop of 7 % or more), at least 4
sessions, the last 3 within 6 weeks, and none of the last 3 set a rep-at-load record (a
set with more reps, or seconds, than any earlier set of the cycle at that load or more).
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

ALGO_VERSION = "prog-v1"
TARGET_RIR = 2.0
TARGET_RPE = 10.0 - TARGET_RIR
WORKING_SET_FRACTION = 0.85
MAX_STEP_FRACTION = 0.10
STALL_MIN_SESSIONS = 4
STALL_WINDOW = 3
STALL_TOLERANCE = 0.01
STALL_MAX_SPAN_DAYS = 42
RESET_DROP = 0.07
RESET_FACTOR = 0.90
BELOW_FACTOR = 0.925
HOLD_RECOVERING_BELOW = 0.40
EASY_RPE = 7.5  # every working set at RPE 7.5 or easier: at least 2.5 in reserve
KEEP_DAYS = 7
MAX_E1RM_REPS = 12
MAX_BODYWEIGHT_REPS = 30

LOWER_PATTERNS = {"squat", "hinge", "lunge"}
INCREMENT: dict[str, float] = {
    "barbell": 2.5,
    "ez_bar": 2.5,
    "dumbbell": 2.5,
    "cable": 2.5,
    "machine": 2.5,
    "kettlebell": 4.0,
}

Kind = Literal["reps", "hold", "none"]
Change = Literal[
    "first", "up_load", "up_reps", "up_time", "hold", "down", "reset", "advance", "none"
]


@dataclass(frozen=True)
class SetRec:
    reps: int
    weight_kg: float = 0.0
    rpe: float | None = None
    duration_s: int | None = None


@dataclass(frozen=True)
class SessionRec:
    at: datetime
    sets: tuple[SetRec, ...]


@dataclass(frozen=True)
class ExerciseInfo:
    name: str
    equipment: str = "barbell"
    measure: str = "reps"  # reps | hold | time
    mechanic: str | None = "compound"
    pattern: str = "other"
    rep_low: int | None = None
    rep_high: int | None = None


@dataclass(frozen=True)
class SkillGoal:
    """An open criterion of the next step of a skill tree that this exercise serves."""

    skill_name: str
    step_name: str
    sets: int
    target: int  # reps, or seconds for a hold
    is_hold: bool
    added_kg: float = 0.0
    sessions_met: int = 0
    confirm_sessions: int = 2

    def describe(self) -> str:
        unit = " s" if self.is_hold else ""
        extra = f" at +{self.added_kg:g} kg" if self.added_kg else ""
        return f"{self.sets}\u00d7{self.target}{unit}{extra}"


@dataclass(frozen=True)
class E1rmTrack:
    current: float | None  # smoothed (EWMA, alpha 0.4) session e1RM
    best: float | None
    last: float | None
    trend_pct_week: float | None  # least-squares slope over 8 weeks, % of the mean per week
    series: tuple[tuple[datetime, float], ...]


@dataclass(frozen=True)
class Stall:
    stalled: bool
    sessions_flat: int
    cycle_best: float | None
    cycle_sessions: int


@dataclass(frozen=True)
class Target:
    kind: Kind
    sets: int
    reps: int | None
    seconds: int | None
    weight_kg: float
    rpe: float | None
    change: Change
    reason: str
    why: str
    formula: str
    inputs: dict[str, float | int | str | None]
    rep_range: tuple[int, int] | None
    increment_kg: float | None
    e1rm: E1rmTrack | None
    stall: Stall
    skill: SkillGoal | None = None
    facts: dict[str, float | int | str] = field(default_factory=dict)
    algo_version: str = ALGO_VERSION


# --- small pure helpers ---------------------------------------------------------------


def epley_rir(load: float, reps: int, rpe: float | None) -> float | None:
    if load <= 0 or reps < 1 or reps > MAX_E1RM_REPS:
        return None
    rir = 0.0 if rpe is None else max(0.0, min(5.0, 10.0 - rpe))
    total = reps + rir
    return load if total <= 1 else load * (1 + total / 30)


def load_for(e1rm: float, reps: int, rir: float = TARGET_RIR) -> float:
    """Epley inverse: the load that leaves `rir` in reserve after `reps`."""
    return e1rm / (1 + (reps + rir) / 30)


def increment(ex: ExerciseInfo, last_load: float) -> float | None:
    inc = INCREMENT.get(ex.equipment)
    if inc is None:
        return 2.5 if last_load > 0 else None  # weighted calisthenics: belt plates
    if ex.equipment == "barbell" and ex.pattern in LOWER_PATTERNS:
        return 5.0
    return inc


def load_step(ex: ExerciseInfo, inc: float | None) -> float:
    if inc is None:
        return 0.5
    return inc / 2 if ex.equipment in ("barbell", "ez_bar") else inc


def round_down(x: float, step: float) -> float:
    return max(0.0, math.floor(x / step + 1e-9) * step)


def round_near(x: float, step: float) -> float:
    return max(0.0, round(x / step) * step)


def working_sets(s: SessionRec, hold: bool) -> list[SetRec]:
    if hold:
        return [x for x in s.sets if (x.duration_s or 0) > 0]
    usable = [x for x in s.sets if x.reps > 0]
    if not usable:
        return []
    top = max(x.weight_kg for x in usable)
    if top <= 0:
        return usable
    return [x for x in usable if x.weight_kg >= WORKING_SET_FRACTION * top]


def top_load(s: SessionRec) -> float:
    return max((x.weight_kg for x in s.sets if x.reps > 0 or x.duration_s), default=0.0)


def mean_rpe(ws: Sequence[SetRec]) -> float | None:
    rated = [x.rpe for x in ws if x.rpe is not None]
    return round(sum(rated) / len(rated), 1) if rated else None


def performance(s: SessionRec, hold: bool) -> float | None:
    """Session best: e1RM for loaded lifts, reps for bodyweight, seconds for holds."""
    ws = working_sets(s, hold)
    if not ws:
        return None
    if hold:
        return float(max(x.duration_s or 0 for x in ws))
    if top_load(s) > 0:
        vals = [v for x in ws if (v := epley_rir(x.weight_kg, x.reps, x.rpe)) is not None]
        return sum(vals) / len(vals) if vals else None  # mean: steadier than one set
    return float(max(x.reps for x in ws))


def rep_range(ex: ExerciseInfo, history: Sequence[SessionRec]) -> tuple[int, int, str]:
    lo, hi = ex.rep_low, ex.rep_high
    if lo and hi and (lo, hi) != (6, 12) and lo < hi:
        return lo, hi, "the exercise's range"
    medians = [
        statistics.median(x.reps for x in ws)
        for s in history[-6:]
        if (ws := working_sets(s, False))
    ]
    if medians:
        # Zones need every recent session to agree, so a bad day or creeping reps never
        # switch the range by themselves.
        if max(medians) <= 5:
            return 3, 6, "strength zone (your recent sessions were all 5 reps or fewer)"
        if min(medians) >= 15:
            return 12, 20, "high-rep zone (your recent sessions were all 15 reps or more)"
    if ex.mechanic == "isolation":
        return 8, 12, "isolation default"
    return 6, 10, "compound default"


def e1rm_track(history: Sequence[SessionRec], hold: bool, now: datetime) -> E1rmTrack:
    series = tuple((s.at, v) for s in history if (v := performance(s, hold)) is not None)
    if not series:
        return E1rmTrack(None, None, None, None, ())
    ew: float | None = None
    for _, v in series:
        ew = v if ew is None else 0.4 * v + 0.6 * ew
    recent = [(t, v) for t, v in series if t >= now - timedelta(weeks=8)]
    trend = None
    if len(recent) >= 3 and (recent[-1][0] - recent[0][0]).days >= 14:
        xs = [(t - recent[0][0]).total_seconds() / 604800 for t, _ in recent]
        ys = [v for _, v in recent]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        sxx = sum((x - mx) ** 2 for x in xs)
        if sxx > 0 and my > 0:
            slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sxx
            trend = round(100 * slope / my, 2)
    return E1rmTrack(
        current=round(ew, 1) if ew is not None else None,
        best=round(max(v for _, v in series), 1),
        last=round(series[-1][1], 1),
        trend_pct_week=trend,
        series=tuple((t, round(v, 1)) for t, v in series),
    )


def cycle_start(history: Sequence[SessionRec]) -> int:
    """Index of the first session after the latest load drop of RESET_DROP or more."""
    start = 0
    for i in range(1, len(history)):
        a, b = top_load(history[i - 1]), top_load(history[i])
        if a > 0 and b <= a * (1 - RESET_DROP):
            start = i
    return start


def _record_points(s: SessionRec, hold: bool) -> list[tuple[float, int]]:
    return [(x.weight_kg, (x.duration_s or 0) if hold else x.reps) for x in working_sets(s, hold)]


def detect_stall(history: Sequence[SessionRec], hold: bool) -> Stall:
    """Stalled: none of the last 3 sessions of the current cycle set a record, i.e. no
    working set beat every earlier set of the cycle on load or on reps (seconds) at that
    load or more; at least 4 sessions in the cycle; the last 3 within 6 weeks.

    A rep-at-load record rather than e1RM, because without logged RPE an e1RM from sets
    stopped short of failure follows the prescription (it falls whenever reps reset after a
    load step), and the simulator showed that alone produced most false alarms."""
    cycle = [s for s in history[cycle_start(history) :] if working_sets(s, hold)]
    n = len(cycle)
    perf = [p for s in cycle if (p := performance(s, hold)) is not None]
    best = round(max(perf), 1) if perf else None
    if n < max(STALL_MIN_SESSIONS, STALL_WINDOW + 1):
        return Stall(False, 0, best, n)
    frontier: list[tuple[float, int]] = []
    flat = 0
    for s in cycle:
        pts = _record_points(s, hold)
        record = not frontier or any(
            not any(fl >= load and fr >= reps for fl, fr in frontier) for load, reps in pts
        )
        flat = 0 if record else flat + 1
        frontier.extend(pts)
    span = (cycle[-1].at - cycle[-STALL_WINDOW].at).days
    stalled = flat >= STALL_WINDOW and span <= STALL_MAX_SPAN_DAYS
    return Stall(stalled, flat if stalled else 0, best, n)


def _fmt(x: float) -> str:
    return f"{x:g}" if abs(x - round(x)) > 1e-9 else str(int(round(x)))


def _sets_text(ws: Sequence[SetRec], hold: bool) -> str:
    if hold:
        return ", ".join(f"{x.duration_s} s" for x in ws)
    return ", ".join(str(x.reps) for x in ws)


# --- the decision -----------------------------------------------------------------------


def next_target(
    ex: ExerciseInfo,
    history: Sequence[SessionRec],
    now: datetime,
    *,
    readiness: float | None = None,
    readiness_muscle: str | None = None,
    kept_at: datetime | None = None,
    skill: SkillGoal | None = None,
) -> Target:
    """The next session's target for one exercise. `history` is oldest first and holds
    finished sessions only (not the one being logged)."""
    hist = sorted((s for s in history if s.at <= now), key=lambda s: s.at)
    hold = ex.measure == "hold"
    if ex.measure == "time":
        return _none(ex, "timed", "Timed activities have no progression target.")
    hist = [s for s in hist if working_sets(s, hold)]
    track = e1rm_track(hist, hold, now)
    stall = detect_stall(hist, hold)
    if not hist:
        return _first(ex, hold, track, stall, skill)
    if hold:
        t = _hold_target(ex, hist, now, track, stall, skill, kept_at)
    else:
        t = _reps_target(ex, hist, now, track, stall, skill, kept_at)
    if (
        readiness is not None
        and readiness < HOLD_RECOVERING_BELOW
        and t.change in ("up_load", "up_reps", "up_time")
    ):
        return _held_for_recovery(t, hist[-1], hold, readiness, readiness_muscle)
    return t


def _first(
    ex: ExerciseInfo, hold: bool, track: E1rmTrack, stall: Stall, skill: SkillGoal | None
) -> Target:
    why = f"First time: log a set that feels like RPE {_fmt(TARGET_RPE)}; it becomes your baseline."
    if skill is not None:
        why = f"First time. {skill.step_name} ({skill.skill_name}) asks for {skill.describe()}."
    return Target(
        kind="hold" if hold else "reps",
        sets=skill.sets if skill else 3,
        reps=None,
        seconds=None,
        weight_kg=0.0,
        rpe=TARGET_RPE,
        change="first",
        reason="first",
        why=why,
        formula="No history yet: the first session sets the baseline.",
        inputs={"sessions": 0},
        rep_range=None,
        increment_kg=None,
        e1rm=track,
        stall=stall,
        skill=skill,
        facts={"target_rpe": TARGET_RPE},
    )


def _none(ex: ExerciseInfo, reason: str, why: str) -> Target:
    return Target(
        kind="none",
        sets=0,
        reps=None,
        seconds=None,
        weight_kg=0.0,
        rpe=None,
        change="none",
        reason=reason,
        why=why,
        formula="",
        inputs={},
        rep_range=None,
        increment_kg=None,
        e1rm=None,
        stall=Stall(False, 0, None, 0),
    )


def _reps_target(
    ex: ExerciseInfo,
    hist: Sequence[SessionRec],
    now: datetime,
    track: E1rmTrack,
    stall: Stall,
    skill: SkillGoal | None,
    kept_at: datetime | None,
) -> Target:
    last = hist[-1]
    ws = working_sets(last, False)
    load = top_load(last)
    lo, hi, range_src = rep_range(ex, hist)
    if skill is not None and not skill.is_hold and load <= 0:
        hi = max(lo + 1, min(MAX_BODYWEIGHT_REPS, skill.target))
        lo = min(lo, hi - 1)
        range_src = f"{skill.step_name} criterion"
    inc = increment(ex, load)
    step = load_step(ex, inc)
    min_reps = min(x.reps for x in ws)
    rpe = mean_rpe(ws)
    sets = max(len(ws), skill.sets if skill else 0) or 3
    e1 = track.last
    inputs: dict[str, float | int | str | None] = {
        "last_sets": _sets_text(ws, False),
        "last_load_kg": load,
        "last_rpe": rpe,
        "rep_low": lo,
        "rep_high": hi,
        "range_from": range_src,
        "increment_kg": inc,
        "target_rpe": TARGET_RPE,
        "e1rm_kg": e1,
        "stalled": "yes" if stall.stalled else "no",
    }
    facts: dict[str, float | int | str] = {
        "last_load_kg": load,
        "min_reps": min_reps,
        "rep_low": lo,
        "rep_high": hi,
        "target_rpe": TARGET_RPE,
    }
    if rpe is not None:
        facts["last_rpe"] = rpe
    if e1 is not None:
        facts["e1rm_kg"] = round(e1, 1)
    prev_ws = working_sets(hist[-2], False) if len(hist) >= 2 else []
    formula = (
        f"Double progression in {lo}-{hi} reps at RPE {_fmt(TARGET_RPE)}: +1 rep per session "
        f"until every set reaches {hi}, then +{_fmt(inc or 0)} kg and back to {lo}."
    )

    def make(
        change: Change,
        reason: str,
        why: str,
        reps: int,
        weight: float,
        extra: dict[str, float | int | str] | None = None,
    ) -> Target:
        f = dict(facts)
        f.update({"target_reps": reps, "target_load_kg": round(weight, 2), "sets": sets})
        if extra:
            f.update(extra)
        return Target(
            kind="reps",
            sets=sets,
            reps=reps,
            seconds=None,
            weight_kg=round(weight, 2),
            rpe=TARGET_RPE,
            change=change,
            reason=reason,
            why=why,
            formula=formula,
            inputs=inputs,
            rep_range=(lo, hi),
            increment_kg=inc,
            e1rm=track,
            stall=stall,
            skill=skill,
            facts=f,
        )

    load_txt = f"{_fmt(load)} kg" if load > 0 else "body weight"

    if kept_at is not None and now - kept_at < timedelta(days=KEEP_DAYS):
        until = kept_at + timedelta(days=KEEP_DAYS)
        return make(
            "hold",
            "kept",
            f"You chose to keep your own numbers on {kept_at:%a %d %b}; "
            f"no new target until {until:%a %d %b}.",
            min_reps,
            load,
        )
    if stall.stalled and load > 0:
        new = round_down(load * RESET_FACTOR, step)
        return make(
            "reset",
            "stall_reset",
            f"No new e1RM best in {stall.sessions_flat} sessions (best "
            f"{_fmt(stall.cycle_best or 0)} kg). Reset 10% to {_fmt(new)} kg and build back up.",
            min_reps,
            new,
            {"sessions_flat": stall.sessions_flat, "cycle_best_kg": stall.cycle_best or 0},
        )
    if stall.stalled and load <= 0 and skill is None:
        return make(
            "hold",
            "stall_bodyweight",
            f"Stuck at {min_reps} reps for {stall.sessions_flat} sessions. Try a harder variation "
            "for lower reps, or add a little load.",
            min_reps,
            load,
            {"sessions_flat": stall.sessions_flat},
        )
    if min_reps < lo:
        prev_under = bool(prev_ws) and min(x.reps for x in prev_ws) < lo
        prev_load = top_load(hist[-2]) if len(hist) >= 2 else 0.0
        if prev_under and load > 0 and load >= prev_load:
            new = round_down(load * BELOW_FACTOR, step)
            if new >= load:
                new = max(0.0, load - step)
            return make(
                "down",
                "below_twice",
                f"Under {lo} reps two sessions running, so the load drops to {_fmt(new)} kg "
                f"(7.5% lighter).",
                lo,
                new,
            )
        return make(
            "hold",
            "below_range",
            f"{min_reps} reps is under the {lo}-{hi} range. Same {load_txt}, aim for {lo}.",
            lo,
            load,
        )
    if rpe is not None and rpe >= 9.5:
        return make(
            "hold",
            "too_hard",
            f"Last sets averaged RPE {_fmt(rpe)}, close to failure. Repeat {load_txt} x "
            f"{min_reps} before adding.",
            min_reps,
            load,
        )
    all_top = all(x.reps >= hi for x in ws)
    if skill is not None and not skill.is_hold and load <= 0 and all_top:
        if skill.sessions_met + 1 >= skill.confirm_sessions:
            why = (
                f"You met {skill.describe()} last time. One more session like it unlocks "
                f"{skill.step_name}."
            )
        else:
            why = f"{skill.describe()} reached. Repeat it to confirm {skill.step_name}."
        return make("hold", "criterion_confirm", why, skill.target, load)
    if all_top:
        if inc is None:
            # One rep past the top or past what was done, whichever is more: a set already
            # above the range must never get a lower "up" target (capped at 30 unless the
            # sets were already above that, then they are repeated).
            reps = min(max(hi, min_reps) + 1, max(MAX_BODYWEIGHT_REPS, min_reps))
            return make(
                "up_reps",
                "top_no_load",
                f"Every set reached {hi} with body weight. Keep adding reps, or add load (belt, "
                "vest) or a harder variation.",
                reps,
                load,
            )
        if load > 0 and inc / load > MAX_STEP_FRACTION and min_reps < hi + 2:
            reps = min_reps + 1
            return make(
                "up_reps",
                "micro_reps",
                f"+{_fmt(inc)} kg would be more than 10% of {_fmt(load)} kg, so add reps up to "
                f"{hi + 2} first.",
                reps,
                load,
                {"increment_kg": inc},
            )
        new = load + inc
        reps = lo
        if load > 0 and inc / load > MAX_STEP_FRACTION:
            # Smallest plate is a big jump: pick reps that keep the e1RM demand level. The
            # track can lag (sets past MAX_E1RM_REPS are left out of it), so the last sets
            # count too: 3 x 14 at 15.5 kg must not leave an older 13.3 kg e1RM asking for
            # 3 x 1 at 18 kg.
            rir = 0.0 if rpe is None else max(0.0, min(5.0, 10.0 - rpe))
            basis = max(e1 or 0.0, load * (1 + (min_reps + rir) / 30))
            reps = max(1, min(hi, int(30 * (basis / new - 1) - TARGET_RIR)))
        rated = f" at RPE {_fmt(rpe)}" if rpe is not None else ""
        return make(
            "up_load",
            "top_of_range",
            f"Every set hit {min_reps} reps{rated}: top of the {lo}-{hi} range, so "
            f"+{_fmt(inc)} kg and back to {reps}.",
            reps,
            new,
            {"increment_kg": inc},
        )
    rpe_max = max((x.rpe for x in ws if x.rpe is not None), default=None)
    if rpe_max is not None and rpe_max <= EASY_RPE and e1 is not None and load > 0:
        ideal = load_for(e1, min_reps)
        new = max(load + step, min(load * (1 + MAX_STEP_FRACTION), round_down(ideal, step)))
        new = round_down(min(new, load * (1 + MAX_STEP_FRACTION)), step)
        if new > load:
            return make(
                "up_load",
                "too_easy",
                f"Every set was RPE {_fmt(rpe_max)} or easier (3+ in reserve). Your e1RM "
                f"{_fmt(round(e1, 1))} kg puts {_fmt(new)} kg x {min_reps} near RPE "
                f"{_fmt(TARGET_RPE)}.",
                min_reps,
                new,
                {"ideal_load_kg": round(ideal, 1)},
            )
    reps = min(hi, min_reps + 1)
    why = (
        f"Last time {_sets_text(ws, False)} at {load_txt}. Same load, aim for {reps} on every set."
    )
    if skill is not None and not skill.is_hold:
        why = (
            f"Feeds {skill.skill_name}: {skill.step_name} needs {skill.describe()}. Last time "
            f"{_sets_text(ws, False)}; next {sets}x{reps}."
        )
    return make("up_reps", "add_rep" if skill is None else "skill_step", why, reps, load)


def _hold_target(
    ex: ExerciseInfo,
    hist: Sequence[SessionRec],
    now: datetime,
    track: E1rmTrack,
    stall: Stall,
    skill: SkillGoal | None,
    kept_at: datetime | None,
) -> Target:
    last = hist[-1]
    ws = working_sets(last, True)
    secs = [x.duration_s or 0 for x in ws]
    load = top_load(last)
    lo = ex.rep_low or 10
    hi = ex.rep_high or 30
    goal = skill.target if skill is not None and skill.is_hold else hi
    sets = max(len(ws), skill.sets if skill else 0) or 3
    min_s = min(secs)
    rpe = mean_rpe(ws)
    inputs: dict[str, float | int | str | None] = {
        "last_holds": _sets_text(ws, True),
        "added_load_kg": load,
        "last_rpe": rpe,
        "goal_s": goal,
        "range_s": f"{lo}-{hi}",
        "stalled": "yes" if stall.stalled else "no",
    }
    facts: dict[str, float | int | str] = {"min_seconds": min_s, "goal_s": goal}
    formula = f"Hold progression: +10% (at least 2 s) per session up to {goal} s, then advance."

    def make(change: Change, reason: str, why: str, seconds: int, weight: float) -> Target:
        f = dict(facts)
        f.update({"target_seconds": seconds, "target_load_kg": weight, "sets": sets})
        return Target(
            kind="hold",
            sets=sets,
            reps=None,
            seconds=seconds,
            weight_kg=round(weight, 2),
            rpe=TARGET_RPE,
            change=change,
            reason=reason,
            why=why,
            formula=formula,
            inputs=inputs,
            rep_range=(lo, hi),
            increment_kg=2.5 if load > 0 else None,
            e1rm=track,
            stall=stall,
            skill=skill,
            facts=f,
        )

    if kept_at is not None and now - kept_at < timedelta(days=KEEP_DAYS):
        return make(
            "hold",
            "kept",
            f"You chose to keep your own numbers on {kept_at:%a %d %b}.",
            min_s,
            load,
        )
    if rpe is not None and rpe >= 9.5 and len(hist) >= 2:
        prev = [x.duration_s or 0 for x in working_sets(hist[-2], True)]
        if prev and min_s < min(prev):
            return make(
                "hold",
                "too_hard",
                f"Holds got shorter at RPE {_fmt(rpe)}. Repeat {min_s} s before adding time.",
                min_s,
                load,
            )
    if min_s >= goal:
        if skill is not None and skill.is_hold:
            return make(
                "hold",
                "criterion_confirm",
                f"You held {skill.describe()} last time. One more session like it unlocks "
                f"{skill.step_name}.",
                goal,
                load,
            )
        if load > 0:
            return make(
                "up_load",
                "hold_add_load",
                f"Every hold reached {goal} s with +{_fmt(load)} kg: add 2.5 kg and restart at "
                f"{lo} s.",
                lo,
                load + 2.5,
            )
        return make(
            "advance",
            "hold_advance",
            f"Every hold reached {goal} s. Time for the next, harder variation (or add load).",
            goal,
            load,
        )
    step = max(2, round(0.1 * min_s))
    target = min(goal, min_s + step)
    why = f"Last holds {_sets_text(ws, True)}. +{step} s toward {goal} s: {sets}x{target} s."
    if skill is not None and skill.is_hold:
        why = (
            f"Feeds {skill.skill_name}: {skill.step_name} needs {skill.describe()}. Last holds "
            f"{_sets_text(ws, True)}; next {sets}x{target} s."
        )
    return make("up_time", "add_time", why, target, load)


def _held_for_recovery(
    t: Target, last: SessionRec, hold: bool, readiness: float, muscle: str | None
) -> Target:
    ws = working_sets(last, hold)
    pct = round(readiness * 100)
    who = muscle or "The muscles this works"
    why = (
        f"{who} {'is' if muscle else 'are'} only {pct}% recovered, so the System holds last "
        "time's numbers today."
    )
    facts = dict(t.facts)
    facts["readiness_pct"] = pct
    if hold:
        seconds = min(x.duration_s or 0 for x in ws)
        facts["target_seconds"] = seconds
        return _replace(
            t, change="hold", reason="hold_recovering", why=why, seconds=seconds, facts=facts
        )
    reps = min(x.reps for x in ws)
    load = top_load(last)
    facts.update({"target_reps": reps, "target_load_kg": load})
    return _replace(
        t,
        change="hold",
        reason="hold_recovering",
        why=why,
        reps=reps,
        weight_kg=round(load, 2),
        facts=facts,
    )


def _replace(t: Target, **kw: object) -> Target:
    from dataclasses import replace

    return replace(t, **kw)  # type: ignore[arg-type]
