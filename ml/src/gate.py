"""gate stage: may this food model ship? Decided on the team's OWN photos only.

Reads metrics.json (evaluate stage) and writes models/food-gate.json:
  passed       every check below holds AND the model is not a smoke/synthetic build
  checks       each check with its value and limit
  reasons      what failed, in words

Checks (params.yaml food_gate):
  * every food class in labels.json has at least min_own_per_class own photos in test
  * own-photo top-1 >= min_own_top1 and top-3 >= min_own_top3
  * the run used ImageNet-pretrained weights (pretrained: true), so the number is from the
    real recipe

The stage never fails the pipeline: a failed gate is a result, recorded and shown. The
publish step (food/src/publish_food.py) refuses to package a model whose gate did not pass,
and the app refuses to load one (app/modules/ml/food_photo.py).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from common import ML_DIR, MODELS_DIR, load_params

NON_FOOD = {"not_food"}


def decide(
    metrics: dict[str, Any], labels: dict[str, Any], params: dict[str, Any]
) -> dict[str, Any]:
    g = params["food_gate"]
    version = str(params.get("export", {}).get("version", ""))
    own = metrics["test_own"]
    classes: list[str] = metrics["classes"]
    per_class = {
        c: int(sum(row)) for c, row in zip(classes, own.get("confusion", []), strict=False)
    }
    food = sorted(c for c in labels["classes"] if c not in NON_FOOD)
    short = {c: per_class.get(c, 0) for c in food if per_class.get(c, 0) < g["min_own_per_class"]}
    checks = {
        "own_photos_per_class": {"min": g["min_own_per_class"], "short": short},
        "own_top1": {"value": own.get("top1"), "min": g["min_own_top1"]},
        "own_top3": {"value": own.get("top3"), "min": g["min_own_top3"]},
        "pretrained": {"value": bool(params["train"].get("pretrained"))},
    }
    reasons: list[str] = []
    if short:
        reasons.append(f"{len(short)} classes have fewer than {g['min_own_per_class']} own photos")
    if not own.get("n"):
        reasons.append("no own photos in the test set")
    if (own.get("top1") or 0) < g["min_own_top1"]:
        reasons.append(f"own-photo top-1 {own.get('top1')} < {g['min_own_top1']}")
    if (own.get("top3") or 0) < g["min_own_top3"]:
        reasons.append(f"own-photo top-3 {own.get('top3')} < {g['min_own_top3']}")
    if not checks["pretrained"]["value"]:
        reasons.append("trained without pretrained weights (smoke recipe)")
    if "smoke" in version:
        reasons.append(f"version {version} is a smoke build")
    return {
        "passed": not reasons,
        "version": version,
        "own_photos": own.get("n", 0),
        "checks": checks,
        "reasons": reasons,
        "checked_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def main(models: Path = MODELS_DIR) -> dict[str, Any]:
    metrics = json.loads((ML_DIR / "metrics.json").read_text())
    labels = json.loads((ML_DIR / "labels.json").read_text(encoding="utf-8"))
    result = decide(metrics, labels, load_params())
    (models / "food-gate.json").write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    r = main()
    print(json.dumps({k: r[k] for k in ("passed", "version", "own_photos", "reasons")}, indent=2))
