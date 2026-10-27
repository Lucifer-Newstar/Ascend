"""Evaluate retrieval with the sidecar's own BM25 code on the freshly built corpus.

  app_questions.yaml   team-written regression set: hit@3 must reach gate.min_hit_at_3
  --external DIR       hand-judged real questions, kept outside the repo (see KB_CARD.md):
    real160_labels.json + kb_judgments_test.json   the 80 test-half questions of the trainer
                       harness, judged once per question (frozen marks, kb-v1)
    kb_passage_judgments.json (optional)   judgments per question AND passage, so a changed
                       corpus is scored on its own ranking: {"real160": {idx: {passage_id:
                       "Y"|"N"}}, "gap120": {key: {...}}}. Top-3 passages with no judgment are
                       counted as not relevant and reported as `unjudged`.
    gap120_labels.json (optional)   the held-out gap questions (v1.4): real questions from the
                       topics the gap analysis found uncovered; only split "test" is scored.
  --build DIR / --intent-model FILE   score another corpus build or intent model (to compare
                       before and after a change on the same judgments)

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


def retriever(build: Path, intent_model: Path | None = None) -> tuple[ModuleType, Any]:
    kn = _load("kb_knowledge", SIDECAR_ML / "knowledge.py")
    kn.CORPUS_FILE = build / "knowledge.jsonl.gz"
    kn.SOURCES_FILE = build / "knowledge-sources.json"
    kn._index.cache_clear()
    rt = _load("intent_runtime", SIDECAR_ML / "intent_runtime.py")
    model = rt.IntentModel.load(intent_model or SIDECAR_ML / "assets" / "intent_model.json.gz")
    return kn, model


def search(kn: ModuleType, model: Any, q: str) -> list[Any]:
    return kn.retrieve(q, 3, intent=model.predict(q).intent)


def judged_scores(
    kn: ModuleType, model: Any, items: list[tuple[str, str]], marks: dict[str, dict[str, str]]
) -> dict[str, int]:
    """Score the live top 3 of each (key, question) against per-passage judgments."""
    out = {"n": len(items), "relevant_top1": 0, "relevant_top3": 0, "answered_at_gate": 0}
    out.update({"relevant_among_answered": 0, "unjudged": 0})
    for key, text in items:
        top = search(kn, model, text)
        seen = marks.get(key, {})
        rel = [seen.get(p.id) == "Y" for p in top]
        out["unjudged"] += sum(p.id not in seen for p in top)
        out["relevant_top1"] += bool(rel[:1] and rel[0])
        out["relevant_top3"] += any(rel)
        if top and top[0].confident:
            out["answered_at_gate"] += 1
            out["relevant_among_answered"] += bool(rel[0])
    return out


def evaluate(
    build: Path = KB / "build", external: Path | None = None, intent_model: Path | None = None
) -> dict[str, Any]:
    params = yaml.safe_load((ML / "params.yaml").read_text())["knowledge"]
    kn, model = retriever(build, intent_model)
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
        per_passage_file = external / "kb_passage_judgments.json"
        if per_passage_file.exists():
            pj = json.loads(per_passage_file.read_text(encoding="utf-8"))
            items = [(idx, real[int(idx)]["text"]) for idx in marks]
            m["real_test_half"] = judged_scores(kn, model, items, pj.get("real160", {}))
            gap_file = external / "gap120_labels.json"
            if gap_file.exists():
                gap = json.loads(gap_file.read_text(encoding="utf-8"))
                test = [g for g in gap if g["split"] == "test"]
                inside = [(g["key"], g["text"]) for g in test if g.get("in_scope", True)]
                m["gap_test"] = judged_scores(kn, model, inside, pj.get("gap120", {}))
                outside = [g["text"] for g in test if not g.get("in_scope", True)]
                declined = 0
                for text in outside:
                    top = search(kn, model, text)
                    declined += not (top and top[0].confident)
                m["gap_test_out_of_scope"] = {"n": len(outside), "declined": declined}
        else:
            answered = relevant_answered = 0
            for idx, mark in marks.items():
                top = search(kn, model, real[int(idx)]["text"])
                if top and top[0].confident:
                    answered += 1
                    relevant_answered += mark[0] == "Y"
            m["real_test_half"] = {
                "n": len(marks),
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
    ap.add_argument("--build", type=Path, default=KB / "build")
    ap.add_argument("--intent-model", type=Path)
    ap.add_argument("--out", type=Path, help="write the metrics here instead of reports/")
    a = ap.parse_args()
    m = evaluate(build=a.build, external=a.external, intent_model=a.intent_model)
    name = "kb_metrics_external.json" if a.external else "kb_metrics.json"
    out = a.out or ML / "reports" / name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(m, indent=2))
    print(json.dumps(m, indent=2))
    if not m["gate"]["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
