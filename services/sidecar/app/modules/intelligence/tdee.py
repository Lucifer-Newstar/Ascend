"""Adaptive TDEE (algo tdee-v1, ADR-0018): a two-state Kalman filter on trend weight and
energy expenditure, fed by daily weigh-ins and logged intake.

State ``x = [W, T]``: trend weight (kg) and total daily energy expenditure (kcal/day).

- Predict, overnight from a day with logged intake ``I``: ``W' = W + (I - T) / rho`` and
  ``T' = T``,
  with ``rho = 7700 kcal/kg`` (an approximation, fine over weeks, not for long-range
  forecasts). Process noise: a small trend term, the intake logging error and a slow random
  walk on ``T``.
- Predict, on a day with no usable intake (nothing logged, or under 800 kcal, which reads as
  a partly logged day): weight is carried as if in balance and its uncertainty grows; ``T``
  only drifts. Missing days never stop the filter.
- Update, on a day with a weigh-in (several are averaged; read as a morning weigh-in, after
  the previous day's intake): ``z = W + noise`` with a scale noise SD of 0.8 kg.
- Prior (cold start): Mifflin-St Jeor BMR x activity factor with SD 450 kcal, so a range is
  shown from day 1 and narrows as weigh-ins and intake accumulate.

Weekly target (MacroFactor-style, adherence neutral): the calorie target changes at most
once a week, on Monday, from the filter state at the end of Sunday, and only when that
week had intake logged on at least 6 of 7 days and 4 or more weigh-ins, and the estimate is
settled (SD <= 200 kcal, 14+ days since the first weigh-in). Otherwise last week's target
stands and the reason is given. A single weekly change is capped at 150 kcal (both rules
from docs/planning/features.md N3). The noise values and the caps are tunable choices, not
measured constants (marked [U] in the ADR); the noise values were picked on a tuning seed
(eval/diet_tune.py).

Pure Python, deterministic, no I/O: the service layer reads the database and passes days in.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import cast

from app.modules.nutrition import tdee as msj

ALGO_VERSION = "tdee-v1"

RHO_KCAL_PER_KG = 7700.0
SCALE_SD_KG = 0.8
TREND_Q_KG2 = 0.0004
INTAKE_SD_KCAL = 350.0
UNLOGGED_SD_KCAL = 600.0
TDEE_Q_KCAL2 = 100.0
PRIOR_SD_KCAL = 450.0
PRIOR_WEIGHT_VAR_KG2 = 1.0
MIN_LOGGED_KCAL = 800.0
GATE_DAYS = 6
WEIGH_IN_GATE = 4  # weigh-ins in the week before a target change (features.md N3)
SETTLED_SD_KCAL = 200.0
SETTLED_DAYS = 14
MAX_WEEKLY_CHANGE_KCAL = 150  # docs/planning/features.md N3
TDEE_MIN, TDEE_MAX = 800.0, 6000.0
MAX_DAYS = 400


@dataclass(frozen=True)
class DayInput:
    day: date
    weight_kg: float | None = None
    intake_kcal: float | None = None


@dataclass(frozen=True)
class Profile:
    sex: str
    age: int
    height_cm: float
    weight_kg: float
    activity: str
    goal: str


@dataclass(frozen=True)
class DayState:
    day: date
    weight_kg: float | None
    intake_kcal: float | None
    intake_used: bool
    trend_kg: float
    tdee_kcal: float
    sd_kcal: float


@dataclass(frozen=True)
class WeekTarget:
    week_start: date
    target_kcal: int
    tdee_kcal: float
    sd_kcal: float
    intake_days: int
    changed: bool
    reason: str
    from_estimate: bool = False


@dataclass(frozen=True)
class TdeeResult:
    algo_version: str
    status: str  # cold_start | learning | adaptive
    prior_tdee_kcal: float
    formula_target_kcal: int
    tdee_kcal: float
    sd_kcal: float
    trend_kg: float | None
    days_of_data: int
    weigh_ins: int
    intake_days_7: int
    weigh_ins_7: int
    target_kcal: int
    target_week_start: date
    target_source: str  # formula | adaptive
    paused: bool
    reason: str
    series: list[DayState] = field(default_factory=list)
    weeks: list[WeekTarget] = field(default_factory=list)

    @property
    def low_kcal(self) -> float:
        return self.tdee_kcal - self.sd_kcal

    @property
    def high_kcal(self) -> float:
        return self.tdee_kcal + self.sd_kcal


def prior_tdee(p: Profile) -> float:
    sex: msj.Sex = "female" if p.sex == "female" else "male"
    bmr = msj.bmr_mifflin_st_jeor(sex, p.weight_kg, p.height_cm, p.age)
    activity = cast(msj.Activity, p.activity if p.activity in msj.ACTIVITY_FACTORS else "moderate")
    return msj.tdee(bmr, activity)


def goal_target(tdee_kcal: float, goal: str) -> int:
    """Adaptive weekly target: expenditure + the goal adjustment, to the nearest 10 kcal."""
    adj = msj.GOAL_ADJUSTMENT.get(goal, 0)
    return int(max(1200, round((tdee_kcal + adj) / 10) * 10))


def formula_target(prior_kcal: float, goal: str) -> int:
    """The Mifflin-St Jeor target exactly as the profile shows it (no rounding to 10)."""
    adj = msj.GOAL_ADJUSTMENT.get(goal, 0)
    return int(max(1200, round(prior_kcal + adj)))


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def _finite(v: float | None) -> float | None:
    if v is None or not math.isfinite(v):
        return None
    return v


def run_filter(days: list[DayInput], prior_kcal: float, start_weight_kg: float) -> list[DayState]:
    """One state per calendar day from the first to the last input day (gaps included).

    A day's state is the morning one: its weigh-in is applied after the overnight predict
    that used the previous day's intake, so a day's own (possibly unfinished) intake only
    enters tomorrow's state.
    """
    if not days:
        return []
    by_day: dict[date, DayInput] = {}
    for d in days:
        by_day[d.day] = d
    first, last = min(by_day), max(by_day)
    if (last - first).days >= MAX_DAYS:
        first = last - timedelta(days=MAX_DAYS - 1)
    first_weight = next(
        (
            w
            for d in sorted(by_day)
            if d >= first and (w := _finite(by_day[d].weight_kg)) is not None and w > 0
        ),
        start_weight_kg,
    )
    w, t = first_weight, _clamp(prior_kcal, TDEE_MIN, TDEE_MAX)
    pww, pwt, ptt = PRIOR_WEIGHT_VAR_KG2, 0.0, PRIOR_SD_KCAL**2
    out: list[DayState] = []
    day = first
    prev_intake: float | None = None
    while day <= last:
        inp = by_day.get(day, DayInput(day))
        if day > first:
            # Predict overnight with yesterday's intake (a morning weigh-in follows it).
            if prev_intake is not None and prev_intake >= MIN_LOGGED_KCAL:
                # W' = W + (I - T)/rho ; F = [[1, -1/rho], [0, 1]]
                a = -1.0 / RHO_KCAL_PER_KG
                w = w + (prev_intake - t) / RHO_KCAL_PER_KG
                pww, pwt, ptt = (
                    pww
                    + 2 * a * pwt
                    + a * a * ptt
                    + TREND_Q_KG2
                    + (INTAKE_SD_KCAL / RHO_KCAL_PER_KG) ** 2,
                    pwt + a * ptt,
                    ptt + TDEE_Q_KCAL2,
                )
            else:
                pww = pww + TREND_Q_KG2 + (UNLOGGED_SD_KCAL / RHO_KCAL_PER_KG) ** 2
                ptt = ptt + TDEE_Q_KCAL2
        z = _finite(inp.weight_kg)
        if z is not None and z > 0:
            s = pww + SCALE_SD_KG**2
            kw, kt = pww / s, pwt / s
            y = z - w
            w, t = w + kw * y, t + kt * y
            pww, pwt, ptt = (1 - kw) * pww, (1 - kw) * pwt, ptt - kt * pwt
        t = _clamp(t, TDEE_MIN, TDEE_MAX)
        ptt = _clamp(ptt, 1.0, PRIOR_SD_KCAL**2)
        pww = max(pww, 1e-6)
        intake = _finite(inp.intake_kcal)
        used = intake is not None and intake >= MIN_LOGGED_KCAL
        out.append(
            DayState(
                day=day,
                weight_kg=round(z, 2) if z is not None and z > 0 else None,
                intake_kcal=round(intake) if intake is not None else None,
                intake_used=used,
                trend_kg=round(w, 2),
                tdee_kcal=round(t, 1),
                sd_kcal=round(math.sqrt(ptt), 1),
            )
        )
        prev_intake = intake
        day += timedelta(days=1)
    return out


def _settled(s: DayState, first_weigh_in: date | None) -> bool:
    return (
        first_weigh_in is not None
        and (s.day - first_weigh_in).days >= SETTLED_DAYS
        and s.sd_kcal <= SETTLED_SD_KCAL
    )


def weekly_targets(
    series: list[DayState], goal: str, start_target: int, today: date
) -> list[WeekTarget]:
    """Targets for every week from the first full week of data to the current week."""
    if not series:
        return []
    first_weigh_in = next((s.day for s in series if s.weight_kg is not None), None)
    by_day = {s.day: s for s in series}
    weeks: list[WeekTarget] = []
    current = start_target
    monday = _monday(series[0].day) + timedelta(days=7)
    last_monday = _monday(today)
    while monday <= last_monday:
        prev = [
            by_day[monday - timedelta(days=i)]
            for i in range(1, 8)
            if monday - timedelta(days=i) in by_day
        ]
        intake_days = sum(1 for s in prev if s.intake_used)
        weighed = sum(1 for s in prev if s.weight_kg is not None)
        end = by_day.get(monday - timedelta(days=1))
        if end is None:
            reason = "no data last week"
            weeks.append(WeekTarget(monday, current, 0.0, 0.0, intake_days, False, reason))
        elif intake_days < GATE_DAYS:
            reason = f"intake logged on {intake_days} of 7 days (needs {GATE_DAYS})"
            weeks.append(
                WeekTarget(monday, current, end.tdee_kcal, end.sd_kcal, intake_days, False, reason)
            )
        elif weighed < WEIGH_IN_GATE:
            reason = f"{weighed} weigh-ins last week (needs {WEIGH_IN_GATE})"
            weeks.append(
                WeekTarget(monday, current, end.tdee_kcal, end.sd_kcal, intake_days, False, reason)
            )
        elif not _settled(end, first_weigh_in):
            reason = "estimate not settled yet (needs 14 days of weigh-ins and SD <= 200 kcal)"
            weeks.append(
                WeekTarget(monday, current, end.tdee_kcal, end.sd_kcal, intake_days, False, reason)
            )
        else:
            wanted = goal_target(end.tdee_kcal, goal)
            step = int(_clamp(wanted - current, -MAX_WEEKLY_CHANGE_KCAL, MAX_WEEKLY_CHANGE_KCAL))
            new = current + step
            changed = new != current
            reason = "updated from last week's estimate" if changed else "estimate unchanged"
            if changed and step != wanted - current:
                reason = f"updated, capped at {MAX_WEEKLY_CHANGE_KCAL} kcal a week"
            current = new
            weeks.append(
                WeekTarget(
                    monday, current, end.tdee_kcal, end.sd_kcal, intake_days, changed, reason, True
                )
            )
        monday += timedelta(days=7)
    return weeks


def compute(days: list[DayInput], profile: Profile, today: date) -> TdeeResult:
    """The whole report for ``today``: series, current estimate, weekly target and status."""
    prior = prior_tdee(profile)
    start_target = formula_target(prior, profile.goal)
    usable = [d for d in days if d.day <= today]
    series = run_filter(usable, prior, profile.weight_kg)
    weeks = weekly_targets(series, profile.goal, start_target, today)
    weigh_ins = sum(1 for s in series if s.weight_kg is not None)
    last7 = [s for s in series if 1 <= (today - s.day).days <= 7]  # complete days only
    intake_7 = sum(1 for s in last7 if s.intake_used)
    weigh_7 = sum(1 for s in last7 if s.weight_kg is not None)
    first_weigh_in = next((s.day for s in series if s.weight_kg is not None), None)
    if not series:
        return TdeeResult(
            ALGO_VERSION, "cold_start", round(prior, 1), start_target, round(prior, 1),
            PRIOR_SD_KCAL, None, 0, 0, 0, 0, start_target, _monday(today), "formula", False,
            "no weigh-ins or meals yet: showing the formula estimate", [], [],
        )  # fmt: skip
    end = series[-1]
    if weigh_ins < 3 or len(series) < 7:
        status = "cold_start"
    elif _settled(end, first_weigh_in):
        status = "adaptive"
    else:
        status = "learning"
    this_week = weeks[-1] if weeks and weeks[-1].week_start == _monday(today) else None
    target = this_week.target_kcal if this_week else start_target
    source = "adaptive" if any(w.from_estimate for w in weeks) else "formula"
    paused = intake_7 < GATE_DAYS or weigh_7 < WEIGH_IN_GATE
    if status == "cold_start":
        reason = f"{weigh_ins} weigh-ins over {len(series)} days: the range is mostly the formula's"
    elif intake_7 < GATE_DAYS:
        reason = (
            f"intake logged on {intake_7} of the last 7 days (needs {GATE_DAYS}); the target holds"
        )
    elif paused:
        reason = f"{weigh_7} weigh-ins in the last 7 days (needs {WEIGH_IN_GATE}); the target holds"
    elif status == "learning":
        reason = f"still learning: SD {end.sd_kcal:.0f} kcal (settles at {SETTLED_SD_KCAL:.0f})"
    else:
        reason = this_week.reason if this_week else "estimate settled"
    return TdeeResult(
        algo_version=ALGO_VERSION,
        status=status,
        prior_tdee_kcal=round(prior, 1),
        formula_target_kcal=start_target,
        tdee_kcal=end.tdee_kcal,
        sd_kcal=end.sd_kcal,
        trend_kg=end.trend_kg,
        days_of_data=len(series),
        weigh_ins=weigh_ins,
        intake_days_7=intake_7,
        weigh_ins_7=weigh_7,
        target_kcal=target,
        target_week_start=_monday(today),
        target_source=source,
        paused=paused,
        reason=reason,
        series=series,
        weeks=weeks,
    )
