"""Diet engines evaluation: tdee-v1 against the Mifflin-St Jeor formula, insights-v1 on
injected patterns, and latency on a one-year history. Synthetic users only; see
docs/ai/evaluation.md for the method, the numbers and their limits.

    cd services/sidecar && uv run python -m eval.diet_eval --users 100 --seed 2026

The simulator (all values are modelling choices, not measured human data):

- Each user gets sex, age, height, a start weight and an activity level, so the formula
  (Mifflin-St Jeor x activity) has a value; their true starting expenditure is that value
  times a personal factor f ~ N(1, 0.12), clipped to [0.75, 1.30].
- True expenditure falls or rises with weight: T(t) = T0 + 22 kcal x (W(t) - W0), a crude
  stand-in for metabolic adaptation [U].
- Intake: T0 + the goal's adjustment (cut -500, maintain 0, bulk +300) + a personal offset
  N(0, 150) + daily noise N(0, 250). Weight follows W' = W + (I - T) / 7700.
- The scale reads W + water + noise, where water is AR(1) (0.8, SD 0.3 kg) and noise
  N(0, 0.2 kg). Each user weighs in on a share of days drawn from U(0.5, 0.95) and logs
  meals on a share drawn from U(0.7, 1.0).
- Scenario "honest": logged intake = true intake. Scenario "under-reporting": each user
  logs only (1 - b) of what they eat, b ~ U(0, 0.15).
"""

from __future__ import annotations

import argparse
import functools
import json
import math
import random
import statistics
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from app.modules.intelligence import insights as ins
from app.modules.intelligence import tdee as td
from app.modules.nutrition import tdee as msj

START = date(2026, 1, 5)  # a Monday
RHO = td.RHO_KCAL_PER_KG
ADAPT_KCAL_PER_KG = 22.0
CHECK_DAYS = (7, 14, 28, 56, 90, 119)
GOAL_ADJ = {"cut": -500.0, "maintain": 0.0, "bulk": 300.0}


@dataclass
class SimUser:
    profile: td.Profile
    formula_tdee: float
    true_tdee: list[float]
    true_weight: list[float]
    true_intake: list[float]
    inputs: list[td.DayInput]


def make_user(rng: random.Random, days: int, under_report: bool) -> SimUser:
    sex = rng.choice(["male", "female"])
    age = rng.randint(18, 45)
    height = rng.gauss(174, 7) if sex == "male" else rng.gauss(161, 6)
    w0 = rng.uniform(58, 95) if sex == "male" else rng.uniform(48, 85)
    activity = rng.choice(["sedentary", "light", "moderate", "moderate", "active"])
    goal = rng.choice(["cut", "maintain", "bulk"])
    profile = td.Profile(sex, age, round(height, 1), round(w0, 1), activity, goal)
    formula = td.prior_tdee(profile)
    f = min(1.30, max(0.75, rng.gauss(1.0, 0.12)))
    t0 = formula * f
    offset = rng.gauss(0, 150)
    p_weigh, p_log = rng.uniform(0.5, 0.95), rng.uniform(0.7, 1.0)
    bias = rng.uniform(0.0, 0.15) if under_report else 0.0
    w, water = w0, 0.0
    tt, tw, ti, inputs = [], [], [], []
    for i in range(days):
        t = t0 + ADAPT_KCAL_PER_KG * (w - w0)
        water = 0.8 * water + rng.gauss(0, 0.3)
        scale = w + water + rng.gauss(0, 0.2)
        intake = max(800.0, t0 + GOAL_ADJ[goal] + offset + rng.gauss(0, 250))
        tt.append(t)
        tw.append(w)
        ti.append(intake)
        inputs.append(
            td.DayInput(
                START + timedelta(days=i),
                round(scale, 1) if rng.random() < p_weigh else None,
                round(intake * (1 - bias)) if rng.random() < p_log else None,
            )
        )
        w = w + (intake - t) / RHO
    return SimUser(profile, formula, tt, tw, ti, inputs)


def pct(xs: list[float], q: float) -> float:
    s = sorted(xs)
    k = (len(s) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def summary(xs: list[float]) -> dict[str, float]:
    return {
        "median": round(statistics.median(xs), 1),
        "mean": round(statistics.fmean(xs), 1),
        "p90": round(pct(xs, 0.9), 1),
    }


def predicted_change(u: SimUser, day: int, tdee_est: float, horizon: int = 14) -> float:
    """Predicted true-weight change over the next `horizon` days from the logged intake
    (a missing day takes the mean of the previous 14 logged days) and a fixed TDEE."""
    past = [d.intake_kcal for d in u.inputs[max(0, day - 14) : day] if d.intake_kcal is not None]
    fill = statistics.fmean(past) if past else tdee_est
    total = 0.0
    for d in u.inputs[day : day + horizon]:
        total += (d.intake_kcal if d.intake_kcal is not None else fill) - tdee_est
    return total / RHO


def eval_tdee(users: int, days: int, seed: int, under_report: bool) -> dict:
    rng = random.Random(seed)
    err_adapt: dict[int, list[float]] = {d: [] for d in CHECK_DAYS}
    err_formula: dict[int, list[float]] = {d: [] for d in CHECK_DAYS}
    within_150 = {28: 0, 56: 0, 90: 0}
    converge: list[int | None] = []
    in_1sd = in_2sd = n_cal = 0
    pred_err: dict[str, dict[int, list[float]]] = {
        "tdee-v1": {28: [], 56: []},
        "formula": {28: [], 56: []},
    }
    changes: list[int] = []
    step_sizes: list[int] = []
    curve_a = [0.0] * days
    curve_f = [0.0] * days
    for _ in range(users):
        u = make_user(rng, days, under_report)
        series = td.run_filter(u.inputs, u.formula_tdee, u.profile.weight_kg)
        errs = [abs(s.tdee_kcal - u.true_tdee[i]) for i, s in enumerate(series)]
        for i in range(days):
            curve_a[i] += errs[i] / users
            curve_f[i] += abs(u.formula_tdee - u.true_tdee[i]) / users
        for d in CHECK_DAYS:
            err_adapt[d].append(errs[d])
            err_formula[d].append(abs(u.formula_tdee - u.true_tdee[d]))
        for d in within_150:
            within_150[d] += errs[d] <= 150
        conv = None
        for d in range(days):
            if all(e <= 150 for e in errs[d:]):
                conv = d
                break
        converge.append(conv)
        for i in range(28, days):
            n_cal += 1
            z = abs(series[i].tdee_kcal - u.true_tdee[i]) / series[i].sd_kcal
            in_1sd += z <= 1
            in_2sd += z <= 2
        for d in (28, 56):
            actual = u.true_weight[min(days - 1, d + 14)] - u.true_weight[d]
            pred_err["tdee-v1"][d].append(abs(predicted_change(u, d, series[d].tdee_kcal) - actual))
            pred_err["formula"][d].append(abs(predicted_change(u, d, u.formula_tdee) - actual))
        report = td.compute(u.inputs, u.profile, START + timedelta(days=days - 1))
        weeks = report.weeks
        changes.append(sum(1 for w in weeks if w.changed))
        prev = report.formula_target_kcal
        for w in weeks:
            if w.changed:
                step_sizes.append(abs(w.target_kcal - prev))
            prev = w.target_kcal
    conv_days = [c for c in converge if c is not None]
    mae = {k: {d: round(statistics.fmean(v[d]), 3) for d in v} for k, v in pred_err.items()}
    return {
        "users": users,
        "days": days,
        "scenario": "under-reporting (b ~ U(0, 0.15))" if under_report else "honest logging",
        "tdee_abs_error_kcal": {
            str(d): {"tdee-v1": summary(err_adapt[d]), "formula": summary(err_formula[d])}
            for d in CHECK_DAYS
        },
        "share_within_150_kcal": {str(d): round(n / users, 3) for d, n in within_150.items()},
        "days_to_converge_150": {
            "converged_share": round(len(conv_days) / users, 3),
            "median_days": statistics.median(conv_days) if conv_days else None,
        },
        "calibration_from_day_28": {
            "share_truth_within_1sd": round(in_1sd / n_cal, 3),
            "share_truth_within_2sd": round(in_2sd / n_cal, 3),
        },
        "weight_change_14d_mae_kg": {
            "tdee-v1": {str(d): v for d, v in mae["tdee-v1"].items()},
            "formula": {str(d): v for d, v in mae["formula"].items()},
            "improvement_pct": {
                str(d): round(100 * (1 - mae["tdee-v1"][d] / mae["formula"][d]), 1)
                for d in (28, 56)
            },
        },
        "weekly_target": {
            "changes_per_user_median": statistics.median(changes),
            "change_size_kcal_median": statistics.median(step_sizes) if step_sizes else None,
            "change_size_kcal_max": max(step_sizes) if step_sizes else None,
        },
        "error_curve_kcal": {
            "tdee-v1": [round(x, 1) for x in curve_a],
            "formula": [round(x, 1) for x in curve_f],
        },
    }


# --- insights ------------------------------------------------------------------------------

PATTERNS = ["none", "intake_high", "intake_low", "protein_short", "weekend_gap", "cut_not_losing"]
# The rule each injected pattern should fire. trend_vs_goal is judged against the true
# weight instead (true_trend_problem), because an intake pattern can also move the trend.
EXPECTED = {
    "intake_high": "intake_vs_target",
    "intake_low": "intake_vs_target",
    "protein_short": "protein_short",
    "weekend_gap": "weekend_gap",
}
# A finding that is also true of the injected pattern (eating at maintenance on a cut is
# also eating 500 kcal above target), so it is not counted as a false alarm.
ALSO_TRUE = {"cut_not_losing": {"intake_vs_target"}}
TREND = "trend_vs_goal"


Week = tuple[list[ins.NutritionDay], td.TdeeResult, str, int, int, date, list[float]]


def make_week(rng: random.Random, pattern: str) -> Week:
    """21 days of a user whose formula TDEE equals their true TDEE (f = 1), so on-plan
    eating produces the goal's trend; then one pattern (or none) injected."""
    sex = rng.choice(["male", "female"])
    w0 = rng.uniform(60, 90) if sex == "male" else rng.uniform(50, 80)
    goal = "cut" if pattern == "cut_not_losing" else rng.choice(["cut", "maintain", "bulk"])
    profile = td.Profile(
        sex, rng.randint(18, 40), 175.0 if sex == "male" else 162.0, round(w0, 1), "moderate", goal
    )
    tdee0 = td.prior_tdee(profile)
    target = td.formula_target(tdee0, goal)
    protein_target = msj.protein_target_g(profile.weight_kg, goal)  # type: ignore[arg-type]
    end = START + timedelta(days=20)
    days, inputs, true_w = [], [], []
    w, water = w0, 0.0
    for i in range(21):
        d = START + timedelta(days=i)
        plan = target if pattern != "cut_not_losing" else tdee0
        if pattern == "intake_high":
            plan = target * 1.18
        elif pattern == "intake_low":
            plan = target * 0.82
        if pattern == "weekend_gap" and d.weekday() >= 5:
            plan += 550
        kcal = max(900.0, plan * rng.gauss(1.0, 0.03) + rng.gauss(0, 120))
        ratio = rng.uniform(0.6, 0.75) if pattern == "protein_short" else rng.uniform(0.92, 1.15)
        days.append(ins.NutritionDay(d, round(kcal), round(protein_target * ratio, 1)))
        t = tdee0 + ADAPT_KCAL_PER_KG * (w - w0)
        water = 0.8 * water + rng.gauss(0, 0.3)
        inputs.append(
            td.DayInput(
                d,
                round(w + water + rng.gauss(0, 0.2), 1) if rng.random() < 0.85 else None,
                round(kcal),
            )
        )
        true_w.append(w)
        w += (kcal - t) / RHO
    report = td.compute(inputs, profile, end + timedelta(days=1))
    return days, report, goal, target, protein_target, end, true_w


def true_trend_problem(goal: str, true_w: list[float]) -> bool:
    """Ground truth for trend_vs_goal: the true (water-free) weight's 14-day rate against
    the same goal bands the rule uses, with no noise margin."""
    rate = (true_w[-1] - true_w[-15]) / 2
    pct = rate / true_w[-1] * 100
    if goal == "cut":
        return rate > -ins.CUT_MIN_LOSS_KG_WEEK or pct < -ins.CUT_MAX_LOSS_PCT_WEEK
    if goal == "bulk":
        return rate < ins.BULK_MIN_GAIN_KG_WEEK
    return abs(rate) > ins.MAINTAIN_MAX_DRIFT_KG_WEEK


def eval_insights(samples: int, seed: int) -> dict:
    rng = random.Random(seed)
    tp: dict[str, int] = {}
    fp: dict[str, int] = {}
    fn: dict[str, int] = {}
    injected: dict[str, int] = {p: 0 for p in PATTERNS}
    false_alarms = 0
    trend_truths = 0
    for _ in range(samples):
        pattern = "none" if rng.random() < 0.4 else rng.choice(PATTERNS[1:])
        injected[pattern] += 1
        days, report, goal, target, protein, end, true_w = make_week(rng, pattern)
        found = {f.code for f in ins.weekly(days, report, goal, target, protein, end).findings}
        expected = EXPECTED.get(pattern)
        ok = ({expected} if expected else set()) | ALSO_TRUE.get(pattern, set())
        truth_trend = true_trend_problem(goal, true_w)
        trend_truths += truth_trend
        for code in found:
            if code == TREND:
                bucket = tp if truth_trend else fp
                bucket[code] = bucket.get(code, 0) + 1
                false_alarms += not truth_trend
            elif code in ok:
                if code == expected:
                    tp[code] = tp.get(code, 0) + 1
            else:
                fp[code] = fp.get(code, 0) + 1
                false_alarms += 1
        if expected and expected not in found:
            fn[expected] = fn.get(expected, 0) + 1
        if truth_trend and TREND not in found:
            fn[TREND] = fn.get(TREND, 0) + 1
    codes = sorted(set(tp) | set(fp) | set(fn))
    per_code = {}
    for c in codes:
        t, f, n = tp.get(c, 0), fp.get(c, 0), fn.get(c, 0)
        per_code[c] = {
            "tp": t, "fp": f, "fn": n,
            "precision": round(t / (t + f), 3) if t + f else None,
            "recall": round(t / (t + n), 3) if t + n else None,
        }  # fmt: skip
    all_tp, all_fp, all_fn = sum(tp.values()), sum(fp.values()), sum(fn.values())
    return {
        "samples": samples,
        "injected": injected,
        "true_trend_problems": trend_truths,
        "per_rule": per_code,
        "overall": {
            "precision": round(all_tp / (all_tp + all_fp), 3) if all_tp + all_fp else None,
            "recall": round(all_tp / (all_tp + all_fn), 3) if all_tp + all_fn else None,
            "false_alarms_per_user_week": round(false_alarms / samples, 3),
        },
    }


# --- latency -------------------------------------------------------------------------------


def timed(fn: Callable[[], object], runs: int) -> dict[str, float]:
    xs = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn()
        xs.append((time.perf_counter() - t0) * 1000)
    return {"median_ms": round(statistics.median(xs), 2), "p95_ms": round(pct(xs, 0.95), 2)}


def eval_latency(runs: int, seed: int) -> dict:
    rng = random.Random(seed)
    u = make_user(rng, 365, under_report=False)
    today = START + timedelta(days=364)
    food = [
        ins.NutritionDay(d.day, d.intake_kcal, 120.0) for d in u.inputs if d.intake_kcal is not None
    ]
    report = td.compute(u.inputs, u.profile, today)
    engine = {
        "tdee-v1 compute (365 days)": timed(lambda: td.compute(u.inputs, u.profile, today), runs),
        "insights-v1 weekly": timed(
            lambda: ins.weekly(food, report, u.profile.goal, 2200, 120, today), runs
        ),
    }
    endpoints = endpoint_latency(u, today, runs)
    return {"runs": runs, "history_days": 365, "engine": engine, "endpoints": endpoints}


def endpoint_latency(u: SimUser, today: date, runs: int) -> dict:
    """The same year through the real app: SQLite, migrations, the HTTP layer (TestClient)."""
    from fastapi.testclient import TestClient

    from app.core.config import Settings
    from app.main import create_app
    from app.modules.nutrition.models import Food, Meal, MealItem
    from app.modules.progress.models import BodyMetric

    class Clock:
        def __call__(self) -> datetime:
            return datetime.combine(today, datetime.min.time()).replace(hour=20)

    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(
            data_dir=Path(tmp),
            db_url=f"sqlite:///{tmp}/lat.db",
            token="lat",
            ollama_host="http://127.0.0.1:9",
        )
        app = create_app(settings, clock=Clock(), outbox_interval=0)
        with TestClient(app, headers={"Authorization": "Bearer lat"}) as c:
            p = u.profile
            body = {"name": "Lat", "age": p.age, "sex": p.sex, "height_cm": p.height_cm}
            body |= {"weight_kg": p.weight_kg, "goal": p.goal, "activity": p.activity}
            c.put("/profile", json=body)
            factory = app.state.session_factory
            with factory() as db:
                food = db.query(Food).first()
                assert food is not None
                for d in u.inputs:
                    if d.weight_kg is not None:
                        db.add(
                            BodyMetric(
                                measured_at=datetime.combine(d.day, datetime.min.time()).replace(
                                    hour=7
                                ),
                                weight_kg=d.weight_kg,
                            )
                        )
                    if d.intake_kcal is not None:
                        for k, share in enumerate((0.25, 0.35, 0.4)):
                            meal = Meal(
                                day=d.day,
                                meal_type=["breakfast", "lunch", "dinner"][k],
                                logged_at=datetime.combine(d.day, datetime.min.time()).replace(
                                    hour=8 + 5 * k
                                ),
                            )
                            meal.items.append(
                                MealItem(
                                    food_id=food.id,
                                    food_name=food.name,
                                    portions=1,
                                    kcal=d.intake_kcal * share,
                                    protein_g=30,
                                    carbs_g=50,
                                    fat_g=15,
                                )
                            )
                            db.add(meal)
                db.commit()
            out = {}
            for path in ("/intelligence/tdee", "/intelligence/insights", "/meals/day"):
                assert c.get(path).status_code == 200
                out[f"GET {path}"] = timed(functools.partial(c.get, path), runs)
            return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=100)
    ap.add_argument("--days", type=int, default=120)
    ap.add_argument("--samples", type=int, default=300)
    ap.add_argument("--runs", type=int, default=30)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "results" / "diet.json")
    ap.add_argument("--no-latency", action="store_true")
    args = ap.parse_args()
    res = {
        "algo_versions": {"tdee": td.ALGO_VERSION, "insights": ins.ALGO_VERSION},
        "seed": args.seed,
        "tdee": {
            "honest": eval_tdee(args.users, args.days, args.seed, under_report=False),
            "under_reporting": eval_tdee(args.users, args.days, args.seed + 1, under_report=True),
        },
        "insights": eval_insights(args.samples, args.seed + 2),
    }
    if not args.no_latency:
        res["latency"] = eval_latency(args.runs, args.seed + 3)
    text = json.dumps(res, indent=2)
    args.out.write_text(text + "\n")
    print(text[:4000])


if __name__ == "__main__":
    main()
