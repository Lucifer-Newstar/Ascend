r"""Pure-Python inference for the trainer-chat intent model (no numpy, no sklearn).

The model is trained in ml/intent (TF-IDF word 1-2-grams + char_wb 2-5-grams, multinomial
logistic regression) and exported as one gzipped JSON file. This module re-implements the
exact feature extraction of scikit-learn's TfidfVectorizer (lowercase, token pattern
\b\w\w+\b, char_wb padding, sublinear tf, smooth idf, l2 norm per vectoriser) so the app
needs no ML library. ml/tests/test_intent_export.py checks this file against scikit-learn
on every eval text (the parity gate), and the export keeps it under ml/ as the reference.

This file must stay standard-library only: ml/ imports it by path.
"""

from __future__ import annotations

import gzip
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FORMAT = "ascend-intent-v1"
_TOKEN = re.compile(r"(?u)\b\w\w+\b")
_WS = re.compile(r"\s\s+")


@dataclass(frozen=True)
class Prediction:
    intent: str
    confidence: float
    top: list[tuple[str, float]]


def word_ngrams(text: str, lo: int, hi: int) -> list[str]:
    tokens = _TOKEN.findall(text.lower())
    out: list[str] = []
    for n in range(lo, hi + 1):
        for i in range(len(tokens) - n + 1):
            out.append(" ".join(tokens[i : i + n]))
    return out


def char_wb_ngrams(text: str, lo: int, hi: int) -> list[str]:
    """scikit-learn's _char_wb_ngrams, after its lowercase preprocessing."""
    text = _WS.sub(" ", text.lower())
    out: list[str] = []
    for w in text.split():
        w = " " + w + " "
        wlen = len(w)
        for n in range(lo, hi + 1):
            offset = 0
            out.append(w[offset : offset + n])
            while offset + n < wlen:
                offset += 1
                out.append(w[offset : offset + n])
            if offset == 0:  # count a short word (w_len < n) only once
                break
    return out


class _Block:
    """One vectoriser: vocabulary -> (idf, sparse class weights)."""

    def __init__(self, spec: dict[str, Any]) -> None:
        self.kind: str = spec["analyzer"]
        self.lo, self.hi = spec["ngram_range"]
        self.sublinear: bool = spec["sublinear_tf"]
        self.terms: dict[str, tuple[float, list[list[float]]]] = {
            t: (v[0], v[1]) for t, v in spec["terms"].items()
        }

    def grams(self, text: str) -> list[str]:
        if self.kind == "word":
            return word_ngrams(text, self.lo, self.hi)
        return char_wb_ngrams(text, self.lo, self.hi)

    def add_scores(self, text: str, scores: list[float]) -> None:
        counts: dict[str, int] = {}
        for g in self.grams(text):
            if g in self.terms:
                counts[g] = counts.get(g, 0) + 1
        if not counts:
            return
        vals: dict[str, float] = {}
        for g, c in counts.items():
            tf = 1.0 + math.log(c) if self.sublinear else float(c)
            vals[g] = tf * self.terms[g][0]
        norm = math.sqrt(sum(v * v for v in vals.values())) or 1.0
        for g, v in vals.items():
            x = v / norm
            for cls, w in self.terms[g][1]:
                scores[int(cls)] += x * w


class IntentModel:
    def __init__(self, data: dict[str, Any]) -> None:
        if data.get("format") != FORMAT:
            raise ValueError(f"not an {FORMAT} file")
        self.version: str = data["version"]
        self.labels: list[str] = data["labels"]
        self.intercept: list[float] = data["intercept"]
        self.blocks = [_Block(b) for b in data["blocks"]]
        self.meta: dict[str, Any] = data.get("meta", {})

    @classmethod
    def load(cls, path: Path) -> IntentModel:
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8") as f:
            return cls(json.load(f))

    def logits(self, text: str) -> list[float]:
        scores = list(self.intercept)
        for b in self.blocks:
            b.add_scores(text, scores)
        return scores

    def proba(self, text: str) -> list[float]:
        z = self.logits(text)
        m = max(z)
        e = [math.exp(v - m) for v in z]
        s = sum(e)
        return [v / s for v in e]

    def predict(self, text: str, k: int = 3) -> Prediction:
        p = self.proba(text)
        order = sorted(range(len(p)), key=lambda i: -p[i])
        top = [(self.labels[i], round(p[i], 4)) for i in order[:k]]
        return Prediction(top[0][0], p[order[0]], top)
