"""How tdee-v1's noise values and insights-v1's trend margin were picked: small grids on
tuning seeds (7, and 11 for the margin) that are not the evaluation seed (2026), so the
reported numbers are not fitted to the users they are measured on. One line per setting.

    cd services/sidecar && uv run python -m eval.diet_tune
"""

from __future__ import annotations

import argparse
import itertools

from app.modules.intelligence import insights as ins
from app.modules.intelligence import tdee as td
from eval import diet_eval


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=60)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    keep = (td.SCALE_SD_KG, td.TDEE_Q_KCAL2, td.INTAKE_SD_KCAL)
    try:
        for sd, q, isd in itertools.product([0.6, 0.8, 1.0], [50.0, 100.0], [250.0, 350.0]):
            td.SCALE_SD_KG, td.TDEE_Q_KCAL2, td.INTAKE_SD_KCAL = sd, q, isd
            r = diet_eval.eval_tdee(args.users, 120, args.seed, under_report=False)
            cal = r["calibration_from_day_28"]
            print(
                f"scale_sd={sd} q_T={q} intake_sd={isd}: within150 d28/56/90="
                f"{r['share_within_150_kcal']}, median err d28="
                f"{r['tdee_abs_error_kcal']['28']['tdee-v1']['median']}, "
                f"1sd={cal['share_truth_within_1sd']} 2sd={cal['share_truth_within_2sd']}"
            )
    finally:
        td.SCALE_SD_KG, td.TDEE_Q_KCAL2, td.INTAKE_SD_KCAL = keep
    # insights-v1's trend rule: how many standard errors outside the band before it speaks.
    margin = ins.TREND_SE_MARGIN
    try:
        for k in (0.0, 1.0, 1.64, 2.0):
            ins.TREND_SE_MARGIN = k
            r = diet_eval.eval_insights(300, args.seed + 4)
            print(
                f"trend margin={k} SE: {r['per_rule'].get('trend_vs_goal')}, overall={r['overall']}"
            )
    finally:
        ins.TREND_SE_MARGIN = margin


if __name__ == "__main__":
    main()
