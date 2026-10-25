"""Package a gated food model for release: ml/release/food-<version>/

    python food/src/publish_food.py

Copies food_clf.onnx, writes models-manifest.json (the export manifest plus the gate result
and each class's food name from labels.json, which the app needs), the evaluation metrics
and the model card. Refuses when the gate did not pass. Upload the folder to Hugging Face
with the commands in food/README.md; the app reads the same three files from
%APPDATA%\\ASCEND\\data\\models\\food.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ML = Path(__file__).resolve().parents[2]
MODELS = ML / "models"
CARD = ML / "food" / "MODEL_CARD.md"


def publish(models: Path = MODELS, out_root: Path = ML / "release") -> Path:
    gate = json.loads((models / "food-gate.json").read_text())
    if not gate.get("passed"):
        raise SystemExit("gate did not pass: " + "; ".join(gate.get("reasons", [])))
    manifest = json.loads((models / "models-manifest.json").read_text())
    labels = json.loads((ML / "labels.json").read_text(encoding="utf-8"))["classes"]
    manifest["food_names"] = {
        c: labels[c]["food_name"] for c in manifest["classes"] if labels.get(c, {}).get("food_name")
    }
    manifest["gate"] = gate
    out = out_root / f"food-{manifest['version']}"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copy2(models / manifest["file"], out / manifest["file"])
    (out / "models-manifest.json").write_text(json.dumps(manifest, indent=2))
    shutil.copy2(ML / "metrics.json", out / "metrics.json")
    shutil.copy2(CARD, out / "README.md")  # Hugging Face shows README.md as the model card
    return out


if __name__ == "__main__":
    print(publish())
    sys.exit(0)
