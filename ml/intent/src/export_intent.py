"""export: models/intent_clf.joblib -> models/intent_model.json.gz + intent-manifest.json.

The runtime file holds, per vectoriser, every vocabulary term with its idf and its
non-negligible class weights (|w| >= prune_below, rounded). Pruning shrinks the file
several times over; the parity gate measures what it costs: the exported file, run through
the sidecar's own runtime (services/sidecar/app/modules/ml/intent_runtime.py), must pick
the same intent as scikit-learn on at least `min_parity_argmax` of all test texts.
"""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import joblib
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
ML = ROOT.parent
REPO = ML.parent
RUNTIME = REPO / "services" / "sidecar" / "app" / "modules" / "ml" / "intent_runtime.py"


def load_runtime() -> ModuleType:
    """The sidecar's runtime, imported by path (it is standard-library only)."""
    spec = importlib.util.spec_from_file_location("intent_runtime", RUNTIME)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["intent_runtime"] = mod  # dataclasses look the module up while it loads
    spec.loader.exec_module(mod)
    return mod


def to_runtime(pipe: Any, version: str, prune: float, decimals: int) -> dict[str, Any]:
    clf = pipe.named_steps["clf"]
    coef = clf.coef_  # (n_classes, n_features)
    blocks = []
    offset = 0
    kept = total = 0
    for name, vec in pipe.named_steps["features"].transformer_list:
        n = len(vec.vocabulary_)
        terms: dict[str, list[Any]] = {}
        for term, j in vec.vocabulary_.items():
            col = coef[:, offset + j]
            ws = [[int(c), round(float(w), decimals)] for c, w in enumerate(col) if abs(w) >= prune]
            total += len(col)
            kept += len(ws)
            terms[term] = [round(float(vec.idf_[j]), 5), ws]
        blocks.append(
            {
                "name": name,
                "analyzer": vec.analyzer,
                "ngram_range": list(vec.ngram_range),
                "sublinear_tf": bool(vec.sublinear_tf),
                "terms": terms,
            }
        )
        offset += n
    return {
        "format": "ascend-intent-v1",
        "version": version,
        "labels": [str(c) for c in clf.classes_],
        "intercept": [round(float(b), 5) for b in clf.intercept_],
        "blocks": blocks,
        "meta": {"weights_kept": kept, "weights_total": total, "prune_below": prune},
    }


def parity(pipe: Any, runtime_model: Any, texts: list[str]) -> dict[str, float]:
    ref = pipe.predict_proba(texts)
    labels = list(pipe.named_steps["clf"].classes_)
    agree = 0
    max_diff = 0.0
    for text, row in zip(texts, ref, strict=True):
        p = runtime_model.proba(text)
        agree += int(labels[int(np.argmax(row))] == runtime_model.labels[int(np.argmax(p))])
        max_diff = max(max_diff, float(np.max(np.abs(np.asarray(p) - row))))
    return {
        "texts": len(texts),
        "argmax_agreement": round(agree / max(1, len(texts)), 4),
        "max_prob_diff": round(max_diff, 4),
    }


def export(dataset: Path = ROOT / "dataset", models: Path = ML / "models") -> dict[str, Any]:
    params = yaml.safe_load((ML / "params.yaml").read_text())["intent"]
    pe = params["export"]
    pipe = joblib.load(models / "intent_clf.joblib")
    data = to_runtime(pipe, pe["version"], pe["prune_below"], pe["decimals"])
    out = models / "intent_model.json.gz"
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with gzip.GzipFile(out, "wb", mtime=0) as f:  # mtime=0: same weights, same bytes
        f.write(raw)

    rt = load_runtime()
    model = rt.IntentModel.load(out)
    texts: list[str] = []
    for name in ("test_templates", "test_clinc", "test_se_hand", "val"):
        texts += [json.loads(x)["text"] for x in (dataset / f"{name}.jsonl").open(encoding="utf-8")]
    check = parity(pipe, model, texts)
    gate = params["gate"]["min_parity_argmax"]
    manifest = {
        "name": "ascend-intent",
        "version": pe["version"],
        "file": out.name,
        "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        "bytes": out.stat().st_size,
        "labels": data["labels"],
        "threshold": params["threshold"],
        "parity": check,
        "weights_kept": data["meta"]["weights_kept"],
        "weights_total": data["meta"]["weights_total"],
        "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (models / "intent-manifest.json").write_text(json.dumps(manifest, indent=2))
    if check["argmax_agreement"] < gate:
        raise SystemExit(f"parity gate: {check['argmax_agreement']} < {gate}")
    return manifest


if __name__ == "__main__":
    m = export()
    print(
        json.dumps(
            {k: m[k] for k in ("file", "bytes", "sha256", "parity", "weights_kept")}, indent=2
        )
    )
