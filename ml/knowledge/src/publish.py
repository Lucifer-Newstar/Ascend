"""Copy the built knowledge base into the app after its gate passed."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

KB = Path(__file__).resolve().parents[1]
ML = KB.parent
ASSETS = ML.parent / "services" / "sidecar" / "app" / "modules" / "ml" / "assets"


def publish(build: Path = KB / "build", assets: Path = ASSETS) -> None:
    metrics = json.loads((ML / "reports" / "kb_metrics.json").read_text())
    if not metrics.get("gate", {}).get("passed"):
        raise SystemExit(f"knowledge gate failed: {metrics.get('gate')}")
    assets.mkdir(parents=True, exist_ok=True)
    for name in ("knowledge.jsonl.gz", "knowledge-sources.json"):
        shutil.copy2(build / name, assets / name)
    print(f"published {metrics['passages']} passages")


if __name__ == "__main__":
    publish()
