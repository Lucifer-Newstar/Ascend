"""retrieve(query, k): BM25F search over the bundled knowledge base, with citations.

The corpus (assets/knowledge.jsonl.gz, ~1.8k passages, ~0.3 MB) is built in ml/knowledge
from free-exercise-db, the 2018 Physical Activity Guidelines for Americans, USDA
FoodData Central, ASCEND's food table and short notes written in our own words. Every
passage carries its source; assets/knowledge-sources.json holds each source's name,
licence and link, which the app shows under the answer.

kb-v2 (trainer answers, 2026-10-27): no model download, still milliseconds, pure Python.
* Words are lower-cased, stop words dropped and suffixes stripped ("running" = "run",
  "meditating" = "meditation"); a few names stay one word ("box breathing", "front crawl",
  "bear crawl", "Muay Thai") so "boxing" no longer meets box breathing.
* The title is its own field (BM25F): a word in the title counts double, and the share of
  the question's meaning found in the title lifts the passage; a title that names more
  than the question (a variant such as "Archer Pull-up" for "pull up") ranks a bit lower.
* Synonyms (SYNONYMS plus every library move's "Also called" names) stand in for a word at
  half weight; two question words side by side in a passage add a little.
* Topic: the question's topic words (boxing, running, meditation...) lift passages of that
  topic and lower team notes of another topic; the intent label weights the sources.
* Coverage is weighted by how rare each word is, and a word the corpus has never seen
  counts as the rarest, so "Why doesn't aikido have kicks?" is not answered with a kick drill.
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
# A passage is offered as THE answer only above both floors and with a question word in its
# title (kb-v2: picked on the dev questions, then measured once on the test questions; see
# ml/knowledge/KB_CARD.md). Below them the trainer does not answer with it: it offers the
# closest note as "the closest I have" with one clarifying question (the CLOSE floors), or
# says it has no note.
MIN_SCORE = 12.0
MIN_COVERAGE = 0.35
CLOSE_SCORE = 8.0
CLOSE_COVERAGE = 0.3

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


# Two-word names that must stay one term, so "boxing" never meets "box breathing" and a
# swimming "front crawl" never meets a "bear crawl".
_PHRASES = [
    (re.compile(r"\bbox[\s-]+breath\w*"), " boxbreathing "),
    (re.compile(r"\bfront[\s-]+crawl\b"), " frontcrawl "),
    (re.compile(r"\bpre[\s-]?workouts?\b"), " preworkout "),
    (re.compile(r"\bbear[\s-]+crawls?\b"), " bearcrawl "),
    (re.compile(r"\bspider[\s-]+crawls?\b"), " spidercrawl "),
    (re.compile(r"\bshadow[\s-]?box\w*"), " shadowboxing "),
    (re.compile(r"\bmuay[\s-]+thai\b"), " muaythai "),
    (re.compile(r"\bjiu[\s-]?jitsu\b"), " jiujitsu "),
    (re.compile(r"\bbody[\s-]?fat\b"), " bodyfat "),
    (re.compile(r"\bbody[\s-]?weight\b"), " bodyweight "),
    (re.compile(r"\brest[\s-]+days?\b"), " restday "),
    (re.compile(r"\bwarm[\s-]?ups?\b|\bwarming[\s-]?up\b"), " warmup "),
    (re.compile(r"\bcool[\s-]?downs?\b"), " cooldown "),
    (re.compile(r"\bheart[\s-]+rate\b"), " heartrate "),
    (re.compile(r"\bhand[\s-]+wraps?\b"), " handwrap "),
    (re.compile(r"\bfoam[\s-]+roll\w*"), " foamroll "),
    (re.compile(r"\b4[\s-]7[\s-]8\b"), " breath478 "),
]
_KEEP = {"boxing", "running", "swimming", "breathing", "kickboxing", "sparring", "fasting"}


def _stem(w: str) -> str:
    if w in _KEEP:
        return {"running": "run", "swimming": "swim", "breathing": "breath"}.get(w, w)
    if len(w) > 5 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 5 and w.endswith("ing"):
        w = w[:-3]
        return w[:-1] if len(w) > 3 and w[-1] == w[-2] and w[-1] not in "lsz" else w
    if len(w) > 4 and w.endswith("ed") and not w.endswith("eed"):
        w = w[:-2]
        return w[:-1] if len(w) > 3 and w[-1] == w[-2] and w[-1] not in "lsz" else w
    if len(w) > 3 and w.endswith("s") and not w.endswith(("ss", "us", "is")):
        w = w[:-1]
    if len(w) > 6 and w.endswith("ation"):
        return w[:-3]
    if len(w) > 5 and w.endswith("ate"):
        return w[:-1]
    if len(w) > 4 and w.endswith("e") and not w.endswith(("ee", "ie")):
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
    for rx, sub in _PHRASES:
        t = rx.sub(sub, t)
    out = []
    for w in re.findall(r"\w+", t):
        w = _FOLD.get(w, w)
        if w in _STOP or len(w) < 2 or w.isdigit():
            continue
        out.append(_FOLD.get(_stem(w), _stem(w)))
    return out


# Topic of a question and of a passage. A passage from a team-notes file (or a library
# move) belongs to one topic; a question names topics with these words. When the question
# names a topic, passages of that topic gain and passages of another named topic lose,
# so "boxing" stops matching a meditation note on box breathing and "5k time" stops
# matching "best time to meditate". General notes (training basics, safety, WHO) and the
# public-domain sources are neutral.
TOPIC_WORDS: dict[str, re.Pattern[str]] = {
    "martial": re.compile(
        r"\b(box(ing|er)?|kickbox\w*|muay ?thai|mma|martial|karate|taekwondo|judo|bjj|"
        r"jiu.?jitsu|kung ?fu|aikido|wing ?chun|krav|sparr\w*|dojo|sensei|kata|belt|"
        r"punch\w*|jab|hook|uppercut|kick\w*|elbow strike|teep|roundhouse|clinch|parry|"
        r"southpaw|orthodox|heavy bag|speed bag|gloves?|hand ?wraps?|shadow ?box\w*|"
        r"self.?defen[cs]e|fight\w*|grappl\w*|breakfall)\b",
        re.I,
    ),
    "cardio": re.compile(
        r"\b(run|runs|runner|running|jog\w*|sprint\w*|5k|10k|marathon|half.?marathon|pace|"
        r"cycl\w*|bike|biking|swim\w*|crawl|freestyle|breaststroke|rowing|rower|elliptical|"
        r"cardio|aerobic|hiit|intervals?|tabata|stamina|endurance|vo2|zone ?2|heart ?rate|"
        r"skipping|jump ?rope|treadmill|stairs|walk|walking|steps|hik\w*)\b",
        re.I,
    ),
    "calisthenics": re.compile(
        r"\b(calisthenics|push.?ups?|pull.?ups?|chin.?ups?|dips?|muscle.?ups?|handstands?|"
        r"planche|front lever|back lever|l.?sit|pistol|bodyweight|body weight|hollow|"
        r"planks?|archer|typewriter|human flag|dragon flag|skin the cat|parallettes|rings)\b",
        re.I,
    ),
    "gym": re.compile(
        r"\b(gym|bench|squats?|deadlifts?|overhead press|barbell|dumbbells?|kettlebells?|"
        r"lift|lifts|lifting|lifter|1rm|one rep max|hypertrophy|powerlift\w*|bodybuild\w*|"
        r"leg press|lat pulldown|rows?|plates?|rpe|trap bar|curls?|machines?|cable|"
        r"starting strength|5x5|sets?|reps?|split)\b",
        re.I,
    ),
    "mobility": re.compile(
        r"\b(mobility|stretch\w*|flexib\w*|yoga|asana|pose|splits?|foam roll\w*|posture|"
        r"tight|stiff\w*|hip flexors?|hamstrings? flexib\w*|toes|range of motion|"
        r"downward dog|cobra|pigeon|sun salutation)\b",
        re.I,
    ),
    "mind": re.compile(
        r"\b(meditat\w*|mindful\w*|breath\w*|pranayama|calm|stress\w*|anxi\w*|relax\w*|"
        r"focus|thoughts?|mantra|metta|vipassana|zen|body scan|sitting practice|jhana)\b",
        re.I,
    ),
    "sleep": re.compile(
        r"\b(sleep\w*|nap|naps|insomnia|recover\w*|rest days?|sore\w*|doms|overtrain\w*|"
        r"ice bath|sauna|massage|bed)\b",
        re.I,
    ),
    "nutrition": re.compile(
        r"\b(protein|calorie\w*|kcal|carb\w*|fats?|macros?|diet\w*|meals?|eat|eating|ate|"
        r"food\w*|shakes?|creatine|supplements?|whey|vitamins?|minerals?|fib(re|er)|sugar|"
        r"breakfast|lunch|dinner|snacks?|drink\w*|water|hydrat\w*|coffee|caffeine|tea|"
        r"fasting|vegetarian|vegan|rice|dal|idli|dosa|chapati|eggs?|chicken|milk|nuts|"
        r"bcaa\w*|carnitine|ashwagandha|electrolytes?|iron|deficit|surplus|bulk\w*|cut)\b",
        re.I,
    ),
}
NOTE_TOPIC: dict[str, str] = {
    "martial_arts": "martial",
    "cardio_running": "cardio",
    "calisthenics_skills": "calisthenics",
    "gym_strength": "gym",
    "mobility_yoga": "mobility",
    "meditation_breathing": "mind",
    "sleep_recovery": "sleep",
    "nutrition_basics": "nutrition",
    "supplements": "nutrition",
}
TOPIC_SAME = 1.3  # a passage in a topic the question names
TOPIC_OTHER = 0.7  # a topical passage when the question names other topics only

# Words people use for the same thing. A synonym counts at SYN_WEIGHT of a real match and
# covers the word it stands for. The library's own "Also called" names are added when the
# corpus loads (every move's aliases point at its name).
SYNONYMS: dict[str, str] = {
    "ripped": "muscle fat",
    "shredded": "fat",
    "toned": "muscle",
    "bigger": "muscle size",
    "skinny": "underweight gain",
    "underweight": "gain weight",
    "thin": "underweight",
    "manboob": "chest fat",
    "flexibility": "stretch",
    "flexible": "stretch",
    "limber": "stretch",
    "nap": "sleep",
    "tired": "fatigue",
    "exhausted": "fatigue",
    "jogging": "running",
    "jog": "run",
    "sprint": "interval",
    "dojo": "class martial",
    "novice": "beginner",
    "newbie": "beginner",
    "start": "beginner",
    "starting": "beginner",
    "lose": "loss",
    "losing": "loss",
    "trim": "fat loss",
    "cut": "fat loss",
    "cutting": "fat loss",
    "abs": "core",
    "core": "abdominal",
    "lats": "back pull",
    "pecs": "chest",
    "delts": "shoulder",
    "quads": "quadriceps",
    "ache": "pain",
    "hurt": "pain",
    "hurts": "pain",
    "anxious": "anxiety",
    "worried": "anxiety",
    "angry": "emotion",
    "anger": "emotion",
    "sad": "emotion",
    "mind": "thought",
    "breath": "breathing",
    "workout": "training exercise",
    "workouts": "training exercise",
    "exercise": "training",
    "kilo": "weight",
    "kilos": "weight",
    "pounds": "weight",
}
SYN_WEIGHT = 0.5
TITLE_WEIGHT = 2.0  # a word in the passage's title counts this many body words
B_TITLE = 0.5
B_BODY = 0.6
BIGRAM_WEIGHT = 0.6  # extra for two question words side by side in the passage
TITLE_COVER = 1.5  # extra weight for the share of the question's meaning in the title
GENERAL_TOPIC = 1.3  # general team notes (training basics, safety, WHO) for any topic
TITLE_EXTRA = 0.5  # a title naming more than the question (a variant) ranks lower


# Words too general to name what a question is about: a title that shares only these with
# the question ("Tabata workouts" for "which workout is best?") is not the answer.
GENERIC = frozenset(
    tokens(
        "workout workouts exercise exercises training train fitness fit routine program "
        "programme best good healthy body diet food eat often time way start beginner"
    )
)


def _topics(text: str) -> set[str]:
    return {name for name, rx in TOPIC_WORDS.items() if rx.search(text)}


def passage_topic(passage_id: str) -> str | None:
    kind, _, rest = passage_id.partition(":")
    head = rest.split(":", 1)[0]
    if kind == "note":
        return NOTE_TOPIC.get(head, "general")
    if kind == "lib":
        return {"kai": "martial", "dario": "calisthenics", "idris": "gym"}.get(head)
    if kind in ("food", "usda"):
        return "nutrition"
    return None


@dataclass(frozen=True)
class Passage:
    id: str
    source: str
    title: str
    text: str
    ref: str
    score: float
    coverage: float  # share of the query's meaning (idf-weighted) found in the passage
    title_hit: bool = False  # a question word (not a GENERIC one) is in the passage's title
    margin: float = 1.0  # this score over the next passage's (1.0 when it is alone)

    @property
    def confident(self) -> bool:
        return self.score >= MIN_SCORE and self.coverage >= MIN_COVERAGE and self.title_hit

    @property
    def close(self) -> bool:
        """Near enough to offer as "the closest note I have", never as the answer."""
        return self.score >= CLOSE_SCORE and self.coverage >= CLOSE_COVERAGE


class Index:
    def __init__(self, passages: list[dict[str, Any]]) -> None:
        self.passages = passages
        self.title: list[Counter[str]] = []
        self.body: list[Counter[str]] = []
        self.bigrams: list[set[tuple[str, str]]] = []
        self.syn: dict[str, list[str]] = {k: tokens(v) for k, v in SYNONYMS.items()}
        for p in passages:
            tt = tokens(p["title"])
            bt = tokens(p["text"])
            self.title.append(Counter(tt))
            self.body.append(Counter(bt))
            pairs = set(zip(tt, tt[1:], strict=False)) | set(zip(bt, bt[1:], strict=False))
            self.bigrams.append(pairs)
            m = re.search(r"Also called: ([^.]*)\.", p["text"])
            if m:
                name = tokens(p.get("ref") or p["title"])
                for alias in m.group(1).split(","):
                    at = tokens(alias)
                    if len(at) == 1 and at[0] not in name:
                        self.syn.setdefault(at[0], name)
        self.lt = [sum(d.values()) for d in self.title]
        self.lb = [sum(d.values()) for d in self.body]
        n = len(passages)
        self.avglt = sum(self.lt) / max(1, n)
        self.avglb = sum(self.lb) / max(1, n)
        df: Counter[str] = Counter()
        for t, b in zip(self.title, self.body, strict=True):
            df.update(set(t) | set(b))
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.unseen = math.log(1 + (n + 0.5) / 0.5)
        self.post: dict[str, list[int]] = {}
        for i, (t, b) in enumerate(zip(self.title, self.body, strict=True)):
            for w in set(t) | set(b):
                self.post.setdefault(w, []).append(i)

    def _tf(self, i: int, t: str) -> float:
        ft = self.title[i].get(t, 0)
        fb = self.body[i].get(t, 0)
        if not ft and not fb:
            return 0.0
        nt = 1 - B_TITLE + B_TITLE * self.lt[i] / self.avglt
        nb = 1 - B_BODY + B_BODY * self.lb[i] / self.avglb
        return TITLE_WEIGHT * ft / nt + fb / nb

    def search(
        self,
        query: str,
        k: int = 3,
        sources: set[str] | None = None,
        prior: dict[str, float] | None = None,
    ) -> list[Passage]:
        raw = tokens(query)
        q = list(dict.fromkeys(raw))
        if not q:
            return []
        # Each question word, with the synonyms that may stand in for it.
        alts = {t: [a for a in self.syn.get(t, []) if a != t and a in self.idf] for t in q}
        # A word the corpus has never seen counts as the rarest word: the question is about
        # something the notes do not cover, which must lower the coverage.
        weight = {t: self.idf.get(t, self.unseen) for t in q}
        total = sum(weight.values()) or 1.0
        qset = set(q) | {a for t in q for a in alts[t]}
        pairs = {(a, b) for a, b in zip(raw, raw[1:], strict=False) if a != b}
        qtop = _topics(query)
        cand: set[int] = set()
        for t in q:
            cand.update(self.post.get(t, ()))
            for alt in alts[t]:
                cand.update(self.post.get(alt, ()))
        scored: list[tuple[float, int, float, bool]] = []
        for i in cand:
            p = self.passages[i]
            if sources is not None and p["source"] not in sources:
                continue
            s = 0.0
            cov = 0.0
            for t in q:
                f = self._tf(i, t)
                w = 1.0
                if not f:
                    best = max(((self._tf(i, a), a) for a in alts[t]), default=(0.0, ""))
                    if not best[0]:
                        continue
                    f, w = best[0], SYN_WEIGHT
                    s += w * self.idf[best[1]] * f * (K1 + 1) / (f + K1)
                else:
                    s += self.idf[t] * f * (K1 + 1) / (f + K1)
                cov += w * weight[t]
            if s <= 0:
                continue
            for a, b in pairs:
                if (a, b) in self.bigrams[i]:
                    s += BIGRAM_WEIGHT * (self.idf.get(a, 0) + self.idf.get(b, 0)) / 2
            s *= prior.get(p["source"], 1.0) if prior else 1.0
            pt = passage_topic(p["id"])
            if qtop and pt == "general":
                s *= GENERAL_TOPIC
            elif qtop and pt:
                s *= TOPIC_SAME if pt in qtop else TOPIC_OTHER
            tcov = sum(weight[t] for t in q if t in self.title[i]) / total
            named = any(t in self.title[i] for t in q if t not in GENERIC)
            tw = sum(self.idf.get(t, 0.0) for t in self.title[i])
            extra = sum(self.idf.get(t, 0.0) for t in self.title[i] if t not in qset)
            s /= 1 + TITLE_EXTRA * (extra / tw if tw else 0.0)
            s *= 1 + TITLE_COVER * tcov
            scored.append((s, i, cov / total, named))
        scored.sort(key=lambda x: (-x[0], x[1]))
        out = []
        top = scored[:k]
        for j, (s, i, cov, th) in enumerate(top):
            nxt = scored[j + 1][0] if j + 1 < len(scored) else 0.0
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
                    th,
                    round(s / nxt, 3) if nxt else 1.0,
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


def passage(passage_id: str) -> dict[str, Any] | None:
    """One passage of the corpus by id (title, text, source), or None."""
    idx = _index()
    if idx is None:
        return None
    if not hasattr(idx, "by_id"):
        idx.by_id = {p["id"]: p for p in idx.passages}  # type: ignore[attr-defined]
    found: dict[str, Any] | None = idx.by_id.get(passage_id)  # type: ignore[attr-defined]
    return found


def share(query: str, text: str) -> float:
    """How much of a question's meaning (idf-weighted, unseen words count as the rarest) a
    piece of text covers, 0..1. The trainer uses it to choose between a help note and a
    knowledge passage, and to pick a passage's most relevant sentence."""
    idx = _index()
    q = list(dict.fromkeys(tokens(query)))
    if idx is None or not q:
        return 0.0
    have = set(tokens(text))
    for t in list(have):
        have.update(idx.syn.get(t, []))
    weight = {t: idx.idf.get(t, idx.unseen) for t in q}
    total = sum(weight.values()) or 1.0
    return sum(w for t, w in weight.items() if t in have or set(idx.syn.get(t, [])) & have) / total


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
