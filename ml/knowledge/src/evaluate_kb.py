"""Evaluate retrieval with the sidecar's own BM25 code on the freshly built corpus.

  app_questions.yaml   team-written regression set: hit@3 must reach gate.min_hit_at_3
  --external DIR       real160_labels.json + kb_judgments_test.json (hand judgments of the
                       top-3 passages for the 80 test-half questions; see KB_CARD.md)

Writes reports/kb_metrics.json (and kb_metrics_external.json with --external).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

KB = Path(__file__).resolve().parents[1]
ML = KB.parent
SIDECAR_ML = ML.parent / "services" / "sidecar" / "app" / "modules" / "ml"


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def retriever(build: Path) -> tuple[ModuleType, Any]:
    kn = _load("kb_knowledge", SIDECAR_ML / "knowledge.py")
    kn.CORPUS_FILE = build / "knowledge.jsonl.gz"
    kn.SOURCES_FILE = build / "knowledge-sources.json"
    kn._index.cache_clear()
    rt = _load("intent_runtime", SIDECAR_ML / "intent_runtime.py")
    model = rt.IntentModel.load(SIDECAR_ML / "assets" / "intent_model.json.gz")
    return kn, model


def search(kn: ModuleType, model: Any, q: str) -> list[Any]:
    return kn.retrieve(q, 3, intent=model.predict(q).intent)


def evaluate(build: Path = KB / "build", external: Path | None = None) -> dict[str, Any]:
    params = yaml.safe_load((ML / "params.yaml").read_text())["knowledge"]
    kn, model = retriever(build)
    qs = yaml.safe_load((KB / "app_questions.yaml").read_text())["questions"]
    hits = [any(p.id in q["expect"] for p in search(kn, model, q["q"])) for q in qs]
    m: dict[str, Any] = {
        "passages": kn.size(),
        "app_questions": {"n": len(qs), "hit_at_3": round(sum(hits) / len(qs), 4)},
        "min_score": kn.MIN_SCORE,
        "min_coverage": kn.MIN_COVERAGE,
    }
    if external is not None:
        real = json.loads((external / "real160_labels.json").read_text(encoding="utf-8"))
        judged = json.loads((external / "kb_judgments_test.json").read_text(encoding="utf-8"))
        marks = judged["test_judgments"]
        answered = relevant_answered = 0
        for idx, mark in marks.items():
            top = search(kn, model, real[int(idx)]["text"])
            if top and top[0].confident:
                answered += 1
                relevant_answered += mark[0] == "Y"
        n = len(marks)
        m["real_test_half"] = {
            "n": n,
            "relevant_top1": sum(v[0] == "Y" for v in marks.values()),
            "relevant_top3": sum(v[1] == "Y" for v in marks.values()),
            "answered_at_gate": answered,
            "relevant_among_answered": relevant_answered,
        }
    gate = params["gate"]
    m["gate"] = {"passed": m["app_questions"]["hit_at_3"] >= gate["min_hit_at_3"]}
    return m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--external", type=Path)
    a = ap.parse_args()
    m = evaluate(external=a.external)
    (ML / "reports").mkdir(exist_ok=True)
    name = "kb_metrics_external.json" if a.external else "kb_metrics.json"
    (ML / "reports" / name).write_text(json.dumps(m, indent=2))
    print(json.dumps(m, indent=2))
    if not m["gate"]["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
