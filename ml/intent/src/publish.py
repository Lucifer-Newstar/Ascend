"""Copy a gated intent model into the app (services/sidecar/app/modules/ml/assets/).

Refuses unless reports/intent_metrics.json says the gate passed for the same model version
the manifest names, so an unevaluated or failing model can't be shipped by accident.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ML = Path(__file__).resolve().parents[2]
ASSETS = ML.parent / "services" / "sidecar" / "app" / "modules" / "ml" / "assets"


def publish(
    models: Path = ML / "models", reports: Path = ML / "reports", assets: Path = ASSETS
) -> dict:
    manifest = json.loads((models / "intent-manifest.json").read_text())
    metrics = json.loads((reports / "intent_metrics.json").read_text())
    ext = reports / "intent_metrics_external.json"
    if ext.exists():
        extra = json.loads(ext.read_text())
        if extra.get("model_version") == metrics.get("model_version"):
            metrics = {**extra, **metrics}
    if metrics.get("model_version") != manifest["version"]:
        raise SystemExit("metrics are for another model version: run evaluate first")
    if not metrics.get("gate", {}).get("passed"):
        raise SystemExit(f"gate failed: {metrics.get('gate')}")
    model = models / manifest["file"]
    if hashlib.sha256(model.read_bytes()).hexdigest() != manifest["sha256"]:
        raise SystemExit("model file does not match its manifest")
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copy2(model, assets / manifest["file"])
    keep = {k: v for k, v in manifest.items() if k != "created_at"} | {
        "created_at": manifest["created_at"],
        "metrics": {
            name: {k: s[k] for k in ("n", "accuracy", "macro_f1", "route_accuracy") if k in s}
            for name, s in metrics.items()
            if isinstance(s, dict) and "accuracy" in s
        },
    }
    (assets / "intent-manifest.json").write_text(json.dumps(keep, indent=2) + "\n")
    return keep


if __name__ == "__main__":
    m = publish()
    print(f"published {m['file']} v{m['version']} ({m['bytes']} bytes)")
