"""Charts for docs/ai/evaluation.md from the JSON results in eval/results/.

cd services/sidecar && uv run --group eval python -m eval.charts [--only diet]
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).parent
RESULTS = HERE / "results"
OUT = HERE.parents[2] / "docs" / "ai" / "img"
COLORS = {
    "fixed 48 h": "#8b95a7",
    "recovery-v2 population": "#4da8ff",
    "recovery-v2 personal": "#a08cff",
}
POLICY_COLORS = ["#a08cff", "#4da8ff", "#8b95a7", "#ff6b6b", "#f5b83d"]
BG, INK, MUTED, LINE = "#0c1322", "#e8f0ff", "#9aa9c4", "#1e2d4a"


def style(ax) -> None:  # type: ignore[no-untyped-def]
    ax.set_facecolor(BG)
    for s in ax.spines.values():
        s.set_color(LINE)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.yaxis.label.set_color(MUTED)
    ax.xaxis.label.set_color(MUTED)
    ax.title.set_color(INK)
    ax.grid(color=LINE, linewidth=0.6, alpha=0.8)
    ax.set_axisbelow(True)


def fig(w: float, h: float, n: int = 1):  # type: ignore[no-untyped-def]
    f, axes = plt.subplots(1, n, figsize=(w, h), dpi=150)
    f.patch.set_facecolor(BG)
    return f, (axes if n > 1 else [axes])


def recovery_charts(r: dict) -> list[Path]:  # type: ignore[type-arg]
    out = []
    f, axes = fig(10, 4.4, 2)
    for ax, (cname, c) in zip(axes, r["cohorts"].items(), strict=True):
        style(ax)
        ax.plot(
            [0, 1], [0, 1], color=MUTED, linestyle="--", linewidth=1, label="perfect calibration"
        )
        for m, mv in c["methods"].items():
            xs = [b["mean_pred"] for b in mv["calibration"]["bins"]]
            ys = [b["mean_true"] for b in mv["calibration"]["bins"]]
            ax.plot(
                xs,
                ys,
                marker="o",
                markersize=4,
                color=COLORS[m],
                label=f"{m} (ECE {mv['calibration']['ece']:.3f})",
            )
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xlabel("predicted readiness (bin mean)")
        ax.set_ylabel("true readiness (bin mean)")
        ax.set_title(f"Calibration, {cname} users ({c['pairs']:,} muscle-sessions)", fontsize=10)
        leg = ax.legend(fontsize=7.5, facecolor=BG, edgecolor=LINE, loc="upper left")
        for t in leg.get_texts():
            t.set_color(INK)
    f.suptitle(
        "Recovery: predicted vs true readiness (synthetic users, simulated ground truth)",
        color=INK,
        fontsize=11,
    )
    f.tight_layout()
    p = OUT / "eval_recovery_calibration.png"
    f.savefig(p, facecolor=BG)
    out.append(p)
    plt.close(f)

    f, axes = fig(10, 4.2, 2)
    metrics = [
        ("pearson_r", "readiness vs true readiness, Pearson r"),
        ("capacity_pearson_r", "readiness vs true daily capacity, Pearson r"),
    ]
    for ax, (key, title) in zip(axes, metrics, strict=True):
        style(ax)
        cohorts = list(r["cohorts"])
        width = 0.26
        for i, m in enumerate(COLORS):
            vals = [r["cohorts"][c]["methods"][m][key] for c in cohorts]
            xs = [j + (i - 1) * width for j in range(len(cohorts))]
            bars = ax.bar(xs, vals, width, color=COLORS[m], label=m)
            for b, v in zip(bars, vals, strict=True):
                ax.text(
                    b.get_x() + b.get_width() / 2,
                    v + 0.015,
                    f"{v:.2f}",
                    ha="center",
                    color=INK,
                    fontsize=8,
                )
        ax.set_xticks(range(len(cohorts)), [f"{c} users" for c in cohorts])
        ax.set_ylim(0, 1.05)
        ax.set_title(title, fontsize=10)
        leg = ax.legend(
            fontsize=7.5,
            facecolor=BG,
            edgecolor=LINE,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.08),
            ncol=3,
        )
        for t in leg.get_texts():
            t.set_color(INK)
    f.suptitle("Recovery: recovery-v2 against a fixed 48-hour rule", color=INK, fontsize=11)
    f.tight_layout()
    p = OUT / "eval_recovery_correlation.png"
    f.savefig(p, facecolor=BG)
    out.append(p)
    plt.close(f)
    return out


def progression_charts(r: dict) -> list[Path]:  # type: ignore[type-arg]
    out = []
    pol = r["policies"]
    # The "no recovery input" run matched prog-v1 exactly (the 40 % hold never fired in
    # this simulation), so it is left out of the chart; it stays in the JSON.
    names = [n for n in pol if "no recovery input" not in n]
    f, axes = fig(11, 4.6, 2)
    ax = axes[0]
    style(ax)
    keys = [
        ("hit_within_1_rep", "hit within 1 rep"),
        ("too_hard_share", "too hard (beyond failure)"),
        ("too_easy_share", "too easy (>4 in reserve)"),
    ]
    width = 0.16
    for i, n in enumerate(names):
        vals = [pol[n][k] for k, _ in keys]
        xs = [j + (i - (len(names) - 1) / 2) * width for j in range(len(keys))]
        ax.bar(xs, vals, width, color=POLICY_COLORS[i % len(POLICY_COLORS)], label=n)
    ax.set_xticks(range(len(keys)), [lbl for _, lbl in keys], fontsize=8.5)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("share of prescribed sets / exposures")
    ax.set_title("Prescription outcomes", fontsize=10)
    leg = ax.legend(
        fontsize=7,
        facecolor=BG,
        edgecolor=LINE,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.1),
        ncol=2,
    )
    for t in leg.get_texts():
        t.set_color(INK)
    ax = axes[1]
    style(ax)
    mean = [pol[n]["rir_error_mean"] for n in names]
    mae = [pol[n]["rir_error_mae"] for n in names]
    xs = list(range(len(names)))
    ax.bar([x - 0.18 for x in xs], mean, 0.36, color="#4da8ff", label="mean (+ = too easy)")
    ax.bar([x + 0.18 for x in xs], mae, 0.36, color="#a08cff", label="mean absolute")
    ax.axhline(0, color=MUTED, linewidth=0.8)
    ax.set_xticks(
        xs, [n.replace(" (", "\n(").replace(" with", "\nwith") for n in names], fontsize=7.5
    )
    ax.set_ylabel("reps in reserve minus the target (RIR 2)")
    ax.set_title("Over/undershoot of the first prescribed set", fontsize=10)
    leg = ax.legend(fontsize=7.5, facecolor=BG, edgecolor=LINE)
    for t in leg.get_texts():
        t.set_color(INK)
    f.suptitle(
        f"Progression: prog-v1 against baselines ({r['users']} synthetic users, {r['days']} days)",
        color=INK,
        fontsize=11,
    )
    f.tight_layout()
    p = OUT / "eval_progression.png"
    f.savefig(p, facecolor=BG)
    out.append(p)
    plt.close(f)
    return out


def diet_charts(d: dict) -> list[Path]:  # type: ignore[type-arg]
    """Mean absolute TDEE error by day: tdee-v1 against the formula, both scenarios."""
    f, axes = fig(10, 4.2, 2)
    for ax, (key, title) in zip(
        axes,
        [("honest", "Honest logging"), ("under_reporting", "Under-reporting 0-15 %")],
        strict=True,
    ):
        style(ax)
        curve = d["tdee"][key]["error_curve_kcal"]
        days = list(range(len(curve["tdee-v1"])))
        ax.plot(
            days, curve["formula"], color="#8b95a7", linewidth=2, label="Mifflin-St Jeor x activity"
        )
        ax.plot(days, curve["tdee-v1"], color="#4da8ff", linewidth=2, label="tdee-v1 (Kalman)")
        ax.axhline(150, color=MUTED, linestyle="--", linewidth=1, label="150 kcal")
        ax.set_title(f"{title} ({d['tdee'][key]['users']} users)", fontsize=10)
        ax.set_xlabel("day")
        ax.set_ylabel("mean |estimate - true TDEE| (kcal)")
        ax.legend(facecolor=BG, edgecolor=LINE, labelcolor=INK, fontsize=8)
    f.tight_layout()
    p = OUT / "eval_diet_tdee.png"
    f.savefig(p, facecolor=BG)
    plt.close(f)
    return [p]


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["recovery", "progression", "diet"], default=None)
    only = ap.parse_args().only
    OUT.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    if only in (None, "recovery"):
        paths += recovery_charts(json.loads((RESULTS / "recovery.json").read_text()))
    if only in (None, "progression"):
        paths += progression_charts(json.loads((RESULTS / "progression.json").read_text()))
    if only in (None, "diet"):
        paths += diet_charts(json.loads((RESULTS / "diet.json").read_text()))
    for p in paths:
        print(p)


if __name__ == "__main__":
    main()
