"""Weekly diet insights (algo insights-v1, ADR-0019): fixed rules over the last 7 and 14
days of logged intake, protein and the adaptive TDEE's trend weight.

Every finding carries the numbers it was computed from and a "Why?" (formula plus every
input), the same pattern as the v6 engines. Each rule has a minimum-data guard and stays
silent below it; at most three findings are shown, ranked by size of effect. Nothing here
is learned or random: the same history always gives the same findings.

Rules (thresholds are ASCEND's choices, marked [U] in the ADR):

- ``intake_vs_target``: mean logged intake over the last 7 days is 10 % or more above or
  below the calorie target (needs 5 logged days).
- ``protein_short``: mean protein is under 85 % of the protein target (needs 5 logged days).
- ``weekend_gap``: weekend days average at least 300 kcal more than weekdays over 14 days
  (needs 2 weekend and 4 weekday logs).
- ``trend_vs_goal``: the least-squares slope of the last 14 days' weigh-ins disagrees with
  the goal by more than its standard error: a cut not losing at least 0.1 kg a week, a cut
  losing over 1 % of body weight a week, a bulk not gaining at least 0.05 kg a week, or
  maintenance drifting over 0.25 kg a week (needs 6 weigh-ins in 14 days).
- ``tdee_vs_formula``: once the adaptive estimate has settled, it differs from the
  Mifflin-St Jeor estimate by at least 150 kcal and two standard deviations.
- ``logging_gap``: fewer than 6 of the last 7 days have intake, so the weekly target holds.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.modules.intelligence.tdee import GATE_DAYS, MIN_LOGGED_KCAL, TdeeResult

ALGO_VERSION = "insights-v1"
MAX_FINDINGS = 3

INTAKE_MIN_DAYS = 5
INTAKE_REL_THRESHOLD = 0.10
PROTEIN_RATIO_THRESHOLD = 0.85
WEEKEND_MIN_GAP_KCAL = 300.0
TREND_MIN_WEIGH_INS = 6
TREND_SE_MARGIN = 1.0
CUT_MIN_LOSS_KG_WEEK = 0.1
CUT_MAX_LOSS_PCT_WEEK = 1.0
BULK_MIN_GAIN_KG_WEEK = 0.05
MAINTAIN_MAX_DRIFT_KG_WEEK = 0.25
FORMULA_MIN_GAP_KCAL = 150.0


@dataclass(frozen=True)
class NutritionDay:
    day: date
    kcal: float | None
    protein_g: float | None


@dataclass(frozen=True)
class Finding:
    code: str
    title: str
    text: str
    severity: float
    numbers: dict[str, float | int | str]
    formula: str
    inputs: dict[str, float | int | str | None]


@dataclass(frozen=True)
class RuleCheck:
    code: str
    outcome: str  # fired | quiet | not_enough_data
    detail: str


@dataclass(frozen=True)
class InsightReport:
    algo_version: str
    week_end: date
    findings: list[Finding] = field(default_factory=list)
    checks: list[RuleCheck] = field(default_factory=list)


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def _window(days: list[NutritionDay], end: date, n: int) -> list[NutritionDay]:
    start = end - timedelta(days=n - 1)
    return [d for d in days if start <= d.day <= end]


def _logged(days: list[NutritionDay]) -> list[NutritionDay]:
    return [d for d in days if d.kcal is not None and d.kcal >= MIN_LOGGED_KCAL]


def _intake_vs_target(last7: list[NutritionDay], target: int) -> Finding | RuleCheck:
    logged = _logged(last7)
    if len(logged) < INTAKE_MIN_DAYS:
        return RuleCheck(
            "intake_vs_target",
            "not_enough_data",
            f"{len(logged)} logged days of {INTAKE_MIN_DAYS} needed",
        )
    mean = _mean([d.kcal or 0.0 for d in logged])
    diff = mean - target
    rel = diff / target
    inputs: dict[str, float | int | str | None] = {
        "logged_days": len(logged),
        "mean_intake_kcal": round(mean),
        "target_kcal": target,
        "difference_kcal": round(diff),
        "difference_pct": round(rel * 100, 1),
    }
    if abs(rel) < INTAKE_REL_THRESHOLD:
        return RuleCheck("intake_vs_target", "quiet", f"{rel * 100:+.1f} % vs target")
    word = "above" if diff > 0 else "below"
    return Finding(
        code="intake_vs_target",
        title=f"Eating {abs(round(rel * 100))}% {word} target",
        text=(
            f"Your logged intake averaged {round(mean)} kcal over {len(logged)} days, "
            f"{abs(round(diff))} kcal {word} your {target} kcal target."
        ),
        severity=round(abs(rel), 3),
        numbers={
            "mean_intake_kcal": round(mean),
            "target_kcal": target,
            "difference_kcal": round(diff),
        },
        formula=(
            "difference = mean(logged intake, last 7 days) - target; "
            "shown when |difference| >= 10 % of target"
        ),
        inputs=inputs,
    )


def _protein_short(last7: list[NutritionDay], protein_target: int) -> Finding | RuleCheck:
    logged = [d for d in _logged(last7) if d.protein_g is not None]
    if protein_target <= 0:
        return RuleCheck("protein_short", "not_enough_data", "no protein target")
    if len(logged) < INTAKE_MIN_DAYS:
        return RuleCheck(
            "protein_short",
            "not_enough_data",
            f"{len(logged)} logged days of {INTAKE_MIN_DAYS} needed",
        )
    mean = _mean([d.protein_g or 0.0 for d in logged])
    ratio = mean / protein_target
    hit = sum(1 for d in logged if (d.protein_g or 0) >= protein_target)
    if ratio >= PROTEIN_RATIO_THRESHOLD:
        return RuleCheck("protein_short", "quiet", f"{ratio * 100:.0f} % of target")
    gap = protein_target - mean
    return Finding(
        code="protein_short",
        title=f"Protein at {round(ratio * 100)}% of target",
        text=(
            f"Protein averaged {round(mean)} g a day against {protein_target} g, "
            f"{round(gap)} g short; the target was met on {hit} of {len(logged)} logged days."
        ),
        severity=round(1 - ratio, 3),
        numbers={
            "mean_protein_g": round(mean),
            "protein_target_g": protein_target,
            "gap_g": round(gap),
        },
        formula=(
            "ratio = mean(logged protein, last 7 days) / protein target; shown when ratio < 0.85"
        ),
        inputs={
            "logged_days": len(logged),
            "mean_protein_g": round(mean, 1),
            "protein_target_g": protein_target,
            "ratio": round(ratio, 3),
            "days_target_met": hit,
        },
    )


def _weekend_gap(last14: list[NutritionDay], target: int) -> Finding | RuleCheck:
    logged = _logged(last14)
    weekend = [d.kcal or 0.0 for d in logged if d.day.weekday() >= 5]
    weekday = [d.kcal or 0.0 for d in logged if d.day.weekday() < 5]
    if len(weekend) < 2 or len(weekday) < 4:
        return RuleCheck(
            "weekend_gap",
            "not_enough_data",
            f"{len(weekend)} weekend and {len(weekday)} weekday logs (needs 2 and 4)",
        )
    we, wd = _mean(weekend), _mean(weekday)
    gap = we - wd
    if gap < WEEKEND_MIN_GAP_KCAL:
        return RuleCheck("weekend_gap", "quiet", f"weekend {gap:+.0f} kcal vs weekdays")
    return Finding(
        code="weekend_gap",
        title=f"Weekends run {round(gap)} kcal higher",
        text=(
            f"Over the last 14 days weekend days averaged {round(we)} kcal and weekdays "
            f"{round(wd)} kcal, a gap of {round(gap)} kcal."
        ),
        severity=round(gap / max(target, 1), 3),
        numbers={
            "weekend_mean_kcal": round(we),
            "weekday_mean_kcal": round(wd),
            "gap_kcal": round(gap),
        },
        formula=(
            "gap = mean(weekend intake) - mean(weekday intake), last 14 days; "
            "shown when gap >= 300 kcal"
        ),
        inputs={
            "weekend_days": len(weekend),
            "weekday_days": len(weekday),
            "weekend_mean_kcal": round(we),
            "weekday_mean_kcal": round(wd),
            "gap_kcal": round(gap),
        },
    )


def _trend_vs_goal(tdee: TdeeResult, goal: str, end: date) -> Finding | RuleCheck:
    window = [s for s in tdee.series if 0 <= (end - s.day).days < 15]
    points = [((s.day - end).days, s.weight_kg) for s in window if s.weight_kg is not None]
    weigh_ins = len(points)
    if len(window) < 15 or weigh_ins < TREND_MIN_WEIGH_INS:
        return RuleCheck(
            "trend_vs_goal",
            "not_enough_data",
            f"{weigh_ins} weigh-ins in 14 days (needs {TREND_MIN_WEIGH_INS})",
        )
    # Least-squares slope of the raw weigh-ins and its standard error: one water-heavy
    # morning moves the slope little, and the error says how sure the slope is.
    n = len(points)
    mx = sum(x for x, _ in points) / n
    my = sum(y for _, y in points) / n
    sxx = sum((x - mx) ** 2 for x, _ in points)
    slope = sum((x - mx) * (y - my) for x, y in points) / sxx
    resid = sum((y - (my + slope * (x - mx))) ** 2 for x, y in points)
    se = math.sqrt(resid / (n - 2) / sxx)
    rate, rate_se = slope * 7, se * 7  # kg per week
    pct, pct_se = rate / my * 100, rate_se / my * 100
    margin = TREND_SE_MARGIN * rate_se
    problem = ""
    if goal == "cut" and rate - (-CUT_MIN_LOSS_KG_WEEK) > margin:
        problem = "not_losing"
    elif goal == "cut" and -pct - CUT_MAX_LOSS_PCT_WEEK > TREND_SE_MARGIN * pct_se:
        problem = "losing_fast"
    elif goal == "bulk" and BULK_MIN_GAIN_KG_WEEK - rate > margin:
        problem = "not_gaining"
    elif goal == "maintain" and abs(rate) - MAINTAIN_MAX_DRIFT_KG_WEEK > margin:
        problem = "drifting"
    inputs: dict[str, float | int | str | None] = {
        "goal": goal,
        "weigh_ins_14d": weigh_ins,
        "mean_weight_kg": round(my, 2),
        "rate_kg_per_week": round(rate, 2),
        "rate_se_kg_per_week": round(rate_se, 2),
        "rate_pct_per_week": round(pct, 2),
        "margin_se": TREND_SE_MARGIN,
    }
    if not problem:
        return RuleCheck(
            "trend_vs_goal", "quiet", f"{rate:+.2f} ± {rate_se:.2f} kg/week fits a {goal}"
        )
    titles = {
        "not_losing": "Cut, but the trend isn't falling",
        "losing_fast": "Losing faster than 1% a week",
        "not_gaining": "Bulk, but the trend isn't rising",
        "drifting": "Maintenance is drifting",
    }
    bands = {
        "not_losing": f"a cut aims to lose at least {CUT_MIN_LOSS_KG_WEEK} kg a week",
        "losing_fast": f"a cut is kept under {CUT_MAX_LOSS_PCT_WEEK:g}% of body weight a week",
        "not_gaining": f"a bulk aims to gain at least {BULK_MIN_GAIN_KG_WEEK} kg a week",
        "drifting": f"maintenance stays within ±{MAINTAIN_MAX_DRIFT_KG_WEEK} kg a week",
    }
    excess = abs(pct) - CUT_MAX_LOSS_PCT_WEEK if problem == "losing_fast" else 0.0
    gap = {
        "not_losing": rate + CUT_MIN_LOSS_KG_WEEK,
        "not_gaining": BULK_MIN_GAIN_KG_WEEK - rate,
        "drifting": abs(rate) - MAINTAIN_MAX_DRIFT_KG_WEEK,
    }.get(problem, excess * my / 100)
    severity = min(1.0, gap / max(my * 0.01, 0.1))
    return Finding(
        code="trend_vs_goal",
        title=titles[problem],
        text=(
            f"Your weigh-ins over 14 days move {rate:+.2f} kg a week (± {rate_se:.2f}); "
            f"{bands[problem]}."
        ),
        severity=round(severity * 0.2 + 0.05, 3),
        numbers={
            "rate_kg_per_week": round(rate, 2),
            "rate_se_kg_per_week": round(rate_se, 2),
            "weigh_ins": weigh_ins,
        },
        formula=(
            "rate = least-squares slope of the last 14 days' weigh-ins x 7; shown only when "
            f"it is outside the goal's band by more than {TREND_SE_MARGIN:g} standard errors"
        ),
        inputs=inputs,
    )


def _tdee_vs_formula(tdee: TdeeResult) -> Finding | RuleCheck:
    if tdee.status != "adaptive":
        return RuleCheck(
            "tdee_vs_formula", "not_enough_data", f"estimate is {tdee.status.replace('_', ' ')}"
        )
    gap = tdee.tdee_kcal - tdee.prior_tdee_kcal
    if abs(gap) < FORMULA_MIN_GAP_KCAL or abs(gap) < 2 * tdee.sd_kcal:
        return RuleCheck("tdee_vs_formula", "quiet", f"{gap:+.0f} kcal vs the formula")
    word = "higher" if gap > 0 else "lower"
    return Finding(
        code="tdee_vs_formula",
        title=f"You burn about {abs(round(gap))} kcal {word} than the formula",
        text=(
            f"From your weigh-ins and logged meals, expenditure is about {round(tdee.tdee_kcal)} "
            f"± {round(tdee.sd_kcal)} kcal a day; the Mifflin-St Jeor formula said "
            f"{round(tdee.prior_tdee_kcal)}."
        ),
        severity=round(abs(gap) / tdee.prior_tdee_kcal, 3),
        numbers={
            "tdee_kcal": round(tdee.tdee_kcal),
            "sd_kcal": round(tdee.sd_kcal),
            "formula_tdee_kcal": round(tdee.prior_tdee_kcal),
        },
        formula=(
            "gap = adaptive TDEE - Mifflin-St Jeor TDEE; shown when |gap| >= 150 kcal and >= 2 SD"
        ),
        inputs={
            "tdee_kcal": round(tdee.tdee_kcal),
            "sd_kcal": round(tdee.sd_kcal),
            "formula_tdee_kcal": round(tdee.prior_tdee_kcal),
            "gap_kcal": round(gap),
        },
    )


def _logging_gap(last7: list[NutritionDay]) -> Finding | RuleCheck:
    n = len(_logged(last7))
    if n >= GATE_DAYS:
        return RuleCheck("logging_gap", "quiet", f"intake on {n} of 7 days")
    return Finding(
        code="logging_gap",
        title=f"Meals logged on {n} of 7 days",
        text=(
            f"Intake was logged on {n} of the last 7 days. The expenditure estimate keeps running, "
            f"but the weekly calorie target only changes after a week with {GATE_DAYS} or more."
        ),
        severity=0.02 + 0.01 * (GATE_DAYS - n),
        numbers={"logged_days": n, "needed_days": GATE_DAYS},
        formula=(
            f"logged days = days in the last 7 with at least {int(MIN_LOGGED_KCAL)} kcal logged; "
            f"shown when fewer than {GATE_DAYS}"
        ),
        inputs={"logged_days": n, "needed_days": GATE_DAYS},
    )


def weekly(
    days: list[NutritionDay],
    tdee: TdeeResult,
    goal: str,
    target_kcal: int,
    protein_target_g: int,
    end: date,
) -> InsightReport:
    """Findings for the 7 days ending ``end`` (inclusive), at most three, largest first."""
    last7 = _window(days, end, 7)
    last14 = _window(days, end, 14)
    results = [
        _intake_vs_target(last7, target_kcal),
        _protein_short(last7, protein_target_g),
        _weekend_gap(last14, target_kcal),
        _trend_vs_goal(tdee, goal, end),
        _tdee_vs_formula(tdee),
        _logging_gap(last7),
    ]
    found = [r for r in results if isinstance(r, Finding)]
    found.sort(key=lambda f: (-f.severity, f.code))
    checks = [RuleCheck(r.code, "fired", r.title) if isinstance(r, Finding) else r for r in results]
    return InsightReport(ALGO_VERSION, end, found[:MAX_FINDINGS], checks)
