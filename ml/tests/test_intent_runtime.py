"""The sidecar's pure-Python intent runtime must reproduce scikit-learn exactly.

A small pipeline is trained on made-up texts, exported WITHOUT pruning or rounding, and the
runtime's probabilities are compared with predict_proba. Edge cases for the char_wb
analyser are in the texts on purpose: one-letter words, repeated spaces, tabs, digits,
punctuation, Tamil script and emoji.
"""

from __future__ import annotations

import gzip
import json

import pytest
from export_intent import load_runtime, parity, to_runtime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

TEXTS = [
    ("3x10 pushups da", "log_set"),
    ("10 push ups", "log_set"),
    ("pullups 7", "log_set"),
    ("plank 60s", "log_hold"),
    ("plank for a minute", "log_hold"),
    ("dead hang 45 sec", "log_hold"),
    ("weight 42.5 kg", "log_weight"),
    ("i weigh 42", "log_weight"),
    ("ate 2 idli", "log_meal"),
    ("had  pongal\tand chutney", "log_meal"),
    ("how much protein in eggs?", "nutrition_question"),
    ("is rice good for bulking", "nutrition_question"),
    ("what is my streak", "ask_progress"),
    ("how many calories today", "ask_progress"),
]
PROBES = [
    "a b c",
    "3*10 PUSHUPS!!",
    "இட்லி 2",
    "plank   1 min 💪",
    "x",
    "",
    "protein protein protein",
    "unknown words zzz qqq",
]


def _pipe(sublinear: bool) -> Pipeline:
    feats = FeatureUnion(
        [
            ("word", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=sublinear)),
            (
                "char",
                TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=sublinear),
            ),
        ]
    )
    pipe = Pipeline([("features", feats), ("clf", LogisticRegression(C=5.0, max_iter=2000))])
    return pipe.fit([t for t, _ in TEXTS], [y for _, y in TEXTS])


@pytest.mark.parametrize("sublinear", [True, False])
def test_runtime_matches_sklearn_without_pruning(tmp_path, sublinear: bool) -> None:
    pipe = _pipe(sublinear)
    data = to_runtime(pipe, "test", prune=0.0, decimals=12)
    path = tmp_path / "m.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(data, f)
    model = load_runtime().IntentModel.load(path)
    texts = [t for t, _ in TEXTS] + PROBES
    check = parity(pipe, model, texts)
    assert check["argmax_agreement"] == 1.0
    assert check["max_prob_diff"] < 1e-6


def test_pruning_keeps_the_decision_on_training_texts(tmp_path) -> None:
    pipe = _pipe(True)
    data = to_runtime(pipe, "test", prune=0.02, decimals=3)
    assert data["meta"]["weights_kept"] < data["meta"]["weights_total"]
    path = tmp_path / "m.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(data, f)
    model = load_runtime().IntentModel.load(path)
    for text, label in TEXTS:
        assert model.predict(text).intent == label


def test_prediction_shape() -> None:
    pipe = _pipe(True)
    model = load_runtime().IntentModel(to_runtime(pipe, "1.2.3", 0.0, 6))
    p = model.predict("10 pushups", k=3)
    assert p.intent == "log_set"
    assert len(p.top) == 3 and p.top[0][0] == "log_set"
    assert 0.0 < p.confidence <= 1.0
    assert abs(sum(model.proba("anything")) - 1.0) < 1e-9
    assert model.version == "1.2.3"


def test_runtime_rejects_other_formats() -> None:
    with pytest.raises(ValueError):
        load_runtime().IntentModel({"format": "something-else"})
