"""Train the intent router: TF-IDF (word 1-2 + char_wb 2-5 n-grams) + logistic regression.

Small on purpose: it trains on a laptop CPU in about a minute and its exported weights run
in the sidecar with the standard library alone (app/modules/ml/intent_runtime.py). C is
picked on val by macro-F1; the final model is fitted on train only, so val stays a clean
model-selection set. Runs are logged to MLflow (experiment "ascend-intent").
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import joblib
import yaml
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.pipeline import FeatureUnion, Pipeline

ROOT = Path(__file__).resolve().parents[1]
ML = ROOT.parent
sys.path.insert(0, str(ML / "src"))


def read(path: Path) -> tuple[list[str], list[str]]:
    rows = [json.loads(x) for x in path.open(encoding="utf-8")]
    return [r["text"] for r in rows], [r["label"] for r in rows]


def make_pipeline(p: dict[str, Any], c: float) -> Pipeline:
    common = {"lowercase": True, "sublinear_tf": p["sublinear_tf"], "min_df": p["min_df"]}
    features = FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(
                    analyzer="word",
                    ngram_range=tuple(p["word_ngrams"]),
                    max_features=p["max_word_features"],
                    **common,
                ),
            ),
            (
                "char",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=tuple(p["char_ngrams"]),
                    max_features=p["max_char_features"],
                    **common,
                ),
            ),
        ]
    )
    clf = LogisticRegression(C=c, max_iter=3000, class_weight="balanced")
    return Pipeline([("features", features), ("clf", clf)])


def mlflow_or_none() -> Any:
    try:
        from train import mlflow_or_none as food_mlflow  # same store as the food pipeline
    except Exception:
        return None
    m = food_mlflow()
    if m is not None:
        try:
            m.set_experiment("ascend-intent")
        except Exception as e:  # tracking must never block training
            print(f"MLflow unavailable, continuing without it: {e}")
            return None
    return m


def train(
    dataset: Path = ROOT / "dataset", models: Path = ML / "models", reports: Path = ML / "reports"
) -> dict[str, Any]:
    params = yaml.safe_load((ML / "params.yaml").read_text())["intent"]
    p = params["train"]
    xtr, ytr = read(dataset / "train.jsonl")
    xva, yva = read(dataset / "val.jsonl")
    mlflow = mlflow_or_none()
    run = mlflow.start_run(run_name="intent-tfidf-lr") if mlflow else None
    grid = []
    best: tuple[float, float, Pipeline] | None = None
    t0 = time.time()
    for c in p["c_grid"]:
        pipe = make_pipeline(p, float(c)).fit(xtr, ytr)
        pred = pipe.predict(xva)
        f1 = float(f1_score(yva, pred, average="macro"))
        acc = float(accuracy_score(yva, pred))
        grid.append({"C": c, "val_macro_f1": round(f1, 4), "val_accuracy": round(acc, 4)})
        print(f"C={c}: val macro-F1 {f1:.4f}, accuracy {acc:.4f}")
        if best is None or f1 > best[0]:
            best = (f1, float(c), pipe)
    assert best is not None
    models.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    joblib.dump(best[2], models / "intent_clf.joblib")
    out = {
        "best_C": best[1],
        "val_macro_f1": round(best[0], 4),
        "grid": grid,
        "train_rows": len(xtr),
        "val_rows": len(xva),
        "labels": sorted(set(ytr)),
        "seconds": round(time.time() - t0, 1),
        "features": {
            name: len(vec.vocabulary_)
            for name, vec in best[2].named_steps["features"].transformer_list
        },
    }
    (reports / "intent_train.json").write_text(json.dumps(out, indent=2))
    if mlflow:
        mlflow.log_params({f"intent.{k}": v for k, v in p.items() if k != "c_grid"})
        mlflow.log_params({"intent.best_C": best[1], "intent.train_rows": len(xtr)})
        mlflow.log_metrics({"val_macro_f1": best[0]})
        mlflow.log_artifact(str(reports / "intent_train.json"))
        mlflow.end_run()
    del run
    return out


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
