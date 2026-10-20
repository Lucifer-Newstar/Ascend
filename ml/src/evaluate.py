"""evaluate stage: run the exported ONNX model on the test split -> metrics.json.

Metrics (docs/ai/evaluation-ai.md): top-1, top-3, macro-F1, per-class recall,
expected calibration error (15 bins) and the confusion matrix. The team-photo subset
(test-own) is reported separately because that is the number the gate uses.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from common import (
    ML_DIR,
    MODELS_DIR,
    PROCESSED_DIR,
    REPORTS_DIR,
    TEST_OWN,
    Row,
    preprocess,
    read_classes,
    read_manifest,
)


def softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def topk_accuracy(probs: np.ndarray, y: np.ndarray, k: int) -> float:
    k = min(k, probs.shape[1])
    top = np.argsort(-probs, axis=1)[:, :k]
    return float(np.mean([y[i] in top[i] for i in range(len(y))])) if len(y) else 0.0


def confusion(y: np.ndarray, pred: np.ndarray, n: int) -> np.ndarray:
    m = np.zeros((n, n), dtype=int)
    for t, p in zip(y, pred, strict=True):
        m[t, p] += 1
    return m


def macro_f1(cm: np.ndarray) -> float:
    f1s = []
    for c in range(cm.shape[0]):
        tp = cm[c, c]
        fp = cm[:, c].sum() - tp
        fn = cm[c, :].sum() - tp
        if tp + fp + fn == 0:
            continue
        f1s.append(2 * tp / (2 * tp + fp + fn))
    return float(np.mean(f1s)) if f1s else 0.0


def ece(probs: np.ndarray, y: np.ndarray, bins: int = 15) -> float:
    """Expected calibration error: |confidence - accuracy| averaged over confidence bins."""
    if not len(y):
        return 0.0
    conf = probs.max(axis=1)
    correct = probs.argmax(axis=1) == y
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        mask = (conf > lo) & (conf <= hi)
        if mask.any():
            total += mask.mean() * abs(conf[mask].mean() - correct[mask].mean())
    return float(total)


def summarise(probs: np.ndarray, y: np.ndarray, classes: list[str]) -> dict[str, Any]:
    cm = confusion(y, probs.argmax(axis=1), len(classes))
    recall = {
        c: (float(cm[i, i] / cm[i].sum()) if cm[i].sum() else None) for i, c in enumerate(classes)
    }
    return {
        "n": int(len(y)),
        "top1": round(topk_accuracy(probs, y, 1), 4),
        "top3": round(topk_accuracy(probs, y, 3), 4),
        "macro_f1": round(macro_f1(cm), 4),
        "ece": round(ece(probs, y), 4),
        "per_class_recall": recall,
        "confusion": cm.tolist(),
    }


def run_onnx(model: Path, rows: list[Row], root: Path) -> np.ndarray:
    import onnxruntime as ort

    sess = ort.InferenceSession(str(model), providers=["CPUExecutionProvider"])
    name = sess.get_inputs()[0].name
    out: list[np.ndarray] = []
    for i in range(0, len(rows), 32):
        batch = np.stack([preprocess(Image.open(root / r.path)) for r in rows[i : i + 32]])
        out.append(sess.run(None, {name: batch})[0])
    return np.concatenate(out) if out else np.zeros((0, 0), dtype=np.float32)


def evaluate(
    model: Path = MODELS_DIR / "food_clf.onnx", processed: Path = PROCESSED_DIR
) -> dict[str, Any]:
    classes = read_classes(processed / "classes.json")
    index = {c: i for i, c in enumerate(classes)}
    test = [r for r in read_manifest(processed / "manifest.csv") if r.split == "test"]
    probs = softmax(run_onnx(model, test, processed))
    y = np.array([index[r.label] for r in test])
    own = np.array([r.tag == TEST_OWN for r in test])
    metrics = {
        "model": model.name,
        "classes": classes,
        "test": summarise(probs, y, classes),
        "test_own": summarise(probs[own], y[own], classes),
    }
    (ML_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    rows = ["true\\pred," + ",".join(classes)]
    rows += [
        f"{c}," + ",".join(map(str, metrics["test"]["confusion"][i])) for i, c in enumerate(classes)
    ]
    (REPORTS_DIR / "confusion.csv").write_text("\n".join(rows) + "\n")
    return metrics


if __name__ == "__main__":
    m = evaluate()
    print(
        json.dumps(
            {
                k: {kk: v for kk, v in m[k].items() if kk != "confusion"}
                for k in ("test", "test_own")
            },
            indent=2,
        )
    )
