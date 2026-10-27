"""retrieve(query, k): BM25 search over the bundled knowledge base, with citations.

The corpus (assets/knowledge.jsonl.gz, ~1.5k passages, ~0.25 MB) is built in ml/knowledge
from free-exercise-db, the 2018 Physical Activity Guidelines for Americans, USDA
FoodData Central, ASCEND's food table and short notes written in our own words. Every
passage carries its source; assets/knowledge-sources.json holds each source's name,
licence and link, which the app shows under the answer.

BM25 (Okapi, k1=1.2, b=0.75) needs no model download and runs in milliseconds. Words are
lower-cased, stop words dropped and light suffixes stripped ("pushups" = "push-up" =
"push ups"), and a few Indian food spellings are folded (idly = idli, chapathi = chapati).
"""

from __future__ import annotations

import gzip
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

ASSETS = Path(__file__).with_name("assets")
CORPUS_FILE = ASSETS / "knowledge.jsonl.gz"
SOURCES_FILE = ASSETS / "knowledge-sources.json"

K1 = 1.2
B = 0.75
# A passage is offered as an answer only above both floors (picked from the precision table
# on the real-question test half in ml/knowledge/KB_CARD.md). Below them the trainer says it
# has no note instead of showing an unrelated passage.
MIN_SCORE = 12.0
MIN_COVERAGE = 0.4

_STOP = set(
    """a an the and or but if then so of to in on at by for with from into over under about
    is are was were be been being am do does did doing have has had having i me my mine we our
    you your he she it its they them their this that these those what which who whom whose
    when where why how can could should would will shall may might must not no yes than too
    very just also only any some more most much many such own same both each few other all
    there here up down out off again further once ever get got make made way thing things
    like really need want know think good best better bad one two lot lots kind sort im ive
    dont doesnt isnt cant wont us please tell give show am pm etc vs via per it's i'm""".split()
)
_COMPOUND = re.compile(r"\b(push|pull|chin|sit|muscle|step)[\s-]?ups?\b")
_FOLD = {
    "idly": "idli",
    "idlis": "idli",
    "chapathi": "chapati",
    "chappati": "chapati",
    "chapatis": "chapati",
    "roti": "chapati",
    "dhal": "dal",
    "daal": "dal",
    "paruppu": "dal",
    "dahi": "curd",
    "yoghurt": "yogurt",
    "keerai": "spinach",
    "palak": "spinach",
    "chana": "chickpea",
    "channa": "chickpea",
    "kadalai": "chickpea",
    "rajma": "kidney",
    "moong": "mung",
    "verkadalai": "peanut",
    "groundnut": "peanut",
    "badam": "almond",
    "jowar": "sorghum",
    "ragi": "millet",
    "kambu": "millet",
    "abs": "abdominal",
    "ab": "abdominal",
    "stomach": "abdominal",
    "belly": "abdominal",
    "cardio": "aerobic",
    "kg": "weight",
    "kgs": "weight",
    "sore": "soreness",
    "muscular": "muscle",
    "gains": "muscle",
    "bulk": "gain",
    "bulking": "gain",
    "hamstring": "hamstrings",
    "glute": "glutes",
    "trap": "traps",
}

# How much each source counts for each kind of question (the intent model's label). The
# short notes are written for app users, so they lead; food tables only answer food
# questions; exercise instructions mostly answer how-to questions.
PRIORS: dict[str, dict[str, float]] = {
    "exercise_howto": {
        "free_exercise_db": 1.3,
        "ascend_library": 1.2,
        "ascend_notes": 1.3,
        "usda_fdc_sr": 0.3,
        "ascend_food_table": 0.3,
    },
    "nutrition_question": {
        "ascend_notes": 1.4,
        "usda_fdc_sr": 1.2,
        "ascend_food_table": 1.2,
        "pag_2018": 0.7,
        "free_exercise_db": 0.4,
        "ascend_library": 0.4,
    },
    "default": {
        "ascend_notes": 1.5,
        "who_pa_2020": 1.2,
        "free_exercise_db": 0.9,
        "ascend_library": 0.9,
        "usda_fdc_sr": 0.5,
        "ascend_food_table": 0.5,
    },
}


def _stem(w: str) -> str:
    if len(w) > 5 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 5 and w.endswith("ing"):
        return w[:-3]
    if len(w) > 4 and w.endswith("ed") and not w.endswith("eed"):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith(("ss", "us", "is")):
        return w[:-1]
    return w


def focus(question: str, long_words: int = 30) -> str:
    """The asking part of a long message: its question sentences (up to two), else its first
    sentence. Forum-style questions bury the question in a story, which drowns BM25."""
    if len(question.split()) <= long_words:
        return question
    sentences = [x.strip() for x in re.split(r"(?<=[.!?])\s+", question) if x.strip()]
    asked = [x for x in sentences if x.endswith("?")]
    return " ".join(asked[:2]) if asked else sentences[0]


def tokens(text: str) -> list[str]:
    t = _COMPOUND.sub(lambda m: f" {m.group(1)}up ", text.lower())
    t = t.replace("'", "")
    out = []
    for w in re.findall(r"\w+", t):
        w = _FOLD.get(w, w)
        if w in _STOP or len(w) < 2 or w.isdigit():
            continue
        out.append(_FOLD.get(_stem(w), _stem(w)))
    return out


@dataclass(frozen=True)
class Passage:
    id: str
    source: str
    title: str
    text: str
    ref: str
    score: float
    coverage: float  # share of the query's words found in the passage

    @property
    def confident(self) -> bool:
        return self.score >= MIN_SCORE and self.coverage >= MIN_COVERAGE


class Index:
    def __init__(self, passages: list[dict[str, Any]]) -> None:
        self.passages = passages
        self.docs: list[Counter[str]] = []
        for p in passages:
            toks = tokens(p["title"]) * 2 + tokens(p["text"])
            self.docs.append(Counter(toks))
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avgdl = sum(self.lengths) / max(1, len(self.lengths))
        df: Counter[str] = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(
        self,
        query: str,
        k: int = 3,
        sources: set[str] | None = None,
        prior: dict[str, float] | None = None,
    ) -> list[Passage]:
        q = list(dict.fromkeys(tokens(query)))
        if not q:
            return []
        scored: list[tuple[float, int, float]] = []
        for i, d in enumerate(self.docs):
            p = self.passages[i]
            if sources is not None and p["source"] not in sources:
                continue
            s = 0.0
            hit = 0
            for t in q:
                f = d.get(t)
                if not f:
                    continue
                hit += 1
                denom = f + K1 * (1 - B + B * self.lengths[i] / self.avgdl)
                s += self.idf[t] * f * (K1 + 1) / denom
            if s > 0:
                weight = prior.get(p["source"], 1.0) if prior else 1.0
                scored.append((s * weight, i, hit / len(q)))
        scored.sort(key=lambda x: (-x[0], x[1]))
        out = []
        for s, i, cov in scored[:k]:
            p = self.passages[i]
            out.append(
                Passage(
                    p["id"],
                    p["source"],
                    p["title"],
                    p["text"],
                    p["ref"],
                    round(s, 3),
                    round(cov, 3),
                )
            )
        return out


@lru_cache(maxsize=1)
def _index() -> Index | None:
    if not CORPUS_FILE.exists():
        return None
    with gzip.open(CORPUS_FILE, "rt", encoding="utf-8") as f:
        return Index([json.loads(line) for line in f if line.strip()])


@lru_cache(maxsize=1)
def sources() -> dict[str, dict[str, str]]:
    try:
        data = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def available() -> bool:
    return _index() is not None


def size() -> int:
    idx = _index()
    return len(idx.passages) if idx else 0


def retrieve(
    query: str,
    k: int = 3,
    sources_only: set[str] | None = None,
    intent: str | None = None,
) -> list[Passage]:
    """Top-k passages for a question (best first). `intent` (from the intent model) weights
    the sources. Empty when the corpus is missing."""
    idx = _index()
    if idx is None:
        return []
    prior = PRIORS.get(intent or "", PRIORS["default"])
    return idx.search(focus(query)[:500], max(1, min(k, 10)), sources_only, prior)


def citation(p: Passage) -> dict[str, str]:
    """What the UI shows under an answer: source name, licence, link and the location."""
    s = sources().get(p.source, {})
    return {
        "passage_id": p.id,
        "title": p.title,
        "source": s.get("name", p.source),
        "licence": s.get("licence", ""),
        "url": s.get("url", ""),
        "ref": p.ref,
    }
