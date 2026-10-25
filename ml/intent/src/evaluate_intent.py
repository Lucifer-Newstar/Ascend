"""evaluate: the SHIPPED runtime file (models/intent_model.json.gz) on every test set.

Internal sets (built by build_dataset.py, never trained on):
  test_templates   held-out app-command templates (synthetic phrasing, unseen templates)
  test_clinc       CLINC150 test split: out-of-scope recall + mapped intents
  test_se_hand     200 hand-checked Fitness Stack Exchange titles

External sets (--external DIR, optional; not in the repo because part of the text has no
licence to redistribute, see DATA_CARD.md):
  real160_labels.json  the 160 real dataset questions of the trainer harness
  app343_labels.json   the trainer stress-test messages (written by the test author)

Per set: accuracy, macro-F1 (over the labels present in that set), route accuracy (the
predicted intent leads to the same handling as the true one, e.g. nutrition vs training
question both go to the knowledge base) and, at the sidecar's confidence threshold,
coverage (share of messages the model is trusted on) and accuracy on those.
The gate in params.yaml fails the stage (exit 1) when a floor is missed.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml
from sklearn.metrics import f1_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_intent import load_runtime  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ML = ROOT.parent


def routes() -> dict[str, str]:
    spec = yaml.safe_load((ROOT / "intents.yaml").read_text())["intents"]
    return {
        k: v["route"].split(":")[0] if v["route"] == "action" else v["route"]
        for k, v in spec.items()
    }


def score(model: Any, rows: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    route = routes()
    y = [r["label"] for r in rows]
    preds = [model.predict(r["text"]) for r in rows]
    yhat = [p.intent for p in preds]
    conf = [p.confidence for p in preds]
    n = len(rows)
    acc = sum(a == b for a, b in zip(y, yhat, strict=True)) / max(1, n)
    racc = sum(route[a] == route[b] for a, b in zip(y, yhat, strict=True)) / max(1, n)
    present = sorted(set(y))
    f1 = f1_score(y, yhat, labels=present, average="macro", zero_division=0)
    sure = [(a, b) for a, b, c in zip(y, yhat, conf, strict=True) if c >= threshold]
    errors = Counter(f"{a} -> {b}" for a, b in zip(y, yhat, strict=True) if a != b)
    out: dict[str, Any] = {
        "n": n,
        "accuracy": round(acc, 4),
        "macro_f1": round(float(f1), 4),
        "route_accuracy": round(racc, 4),
        "coverage_at_threshold": round(len(sure) / max(1, n), 4),
        "accuracy_at_threshold": round(sum(a == b for a, b in sure) / max(1, len(sure)), 4),
        "top_errors": dict(errors.most_common(8)),
    }
    if "out_of_scope" in y:
        oos = [b for a, b in zip(y, yhat, strict=True) if a == "out_of_scope"]
        out["oos_recall"] = round(sum(b == "out_of_scope" for b in oos) / len(oos), 4)
    return out


def evaluate(
    dataset: Path = ROOT / "dataset", models: Path = ML / "models", external: Path | None = None
) -> dict[str, Any]:
    params = yaml.safe_load((ML / "params.yaml").read_text())["intent"]
    th = float(params["threshold"])
    model = load_runtime().IntentModel.load(models / "intent_model.json.gz")
    sets: dict[str, list[dict[str, Any]]] = {}
    for name in ("test_templates", "test_clinc", "test_se_hand"):
        sets[name] = [json.loads(x) for x in (dataset / f"{name}.jsonl").open(encoding="utf-8")]
    if external is not None:
        for name in ("real160", "app343"):
            f = external / f"{name}_labels.json"
            if f.exists():
                sets[name] = json.loads(f.read_text(encoding="utf-8"))
    metrics: dict[str, Any] = {"model_version": model.version, "threshold": th}
    for name, rows in sets.items():
        metrics[name] = score(model, rows, th)
    g = params["gate"]
    checks = {
        "templates_macro_f1": metrics["test_templates"]["macro_f1"] >= g["min_templates_macro_f1"],
        "se_hand_accuracy": metrics["test_se_hand"]["accuracy"] >= g["min_se_hand_accuracy"],
        "oos_recall": metrics["test_clinc"].get("oos_recall", 0) >= g["min_oos_recall"],
    }
    metrics["gate"] = {"passed": all(checks.values()), "checks": checks}
    return metrics


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--external", type=Path, help="folder with real160/app343 label files")
    a = ap.parse_args()
    m = evaluate(external=a.external)
    reports = ML / "reports"
    reports.mkdir(exist_ok=True)
    # The DVC-tracked metrics file holds the internal sets only; a run with --external
    # writes its own file so `dvc metrics` stays reproducible on any machine.
    name = "intent_metrics_external.json" if a.external else "intent_metrics.json"
    (reports / name).write_text(json.dumps(m, indent=2))
    for name, s in m.items():
        if isinstance(s, dict) and "accuracy" in s:
            print(
                f"{name:15} n={s['n']:5} acc={s['accuracy']:.3f} macroF1={s['macro_f1']:.3f} "
                f"route={s['route_accuracy']:.3f} cov@th={s['coverage_at_threshold']:.3f} "
                f"acc@th={s['accuracy_at_threshold']:.3f}"
                + (f" oos_recall={s['oos_recall']:.3f}" if "oos_recall" in s else "")
            )
    print("gate:", m["gate"])
    if not m["gate"]["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
