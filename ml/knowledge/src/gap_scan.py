"""Gap scan: which topics of real user questions the knowledge base can answer.

    python knowledge/src/gap_scan.py --questions DIR [--build DIR] [--intent-model FILE]
                                     [--out reports/gap_scan.json]

DIR holds one JSON-lines file per Stack Exchange site (fitness, martialarts, buddhism,
health, sports; fields site, id, title, tags), extracted from the archive.org data dumps
(CC BY-SA 4.0). They are used only to find WHAT is missing and stay outside the repo
(git-ignored like intent/raw/): this script writes counts per topic, never question text.

A question is "covered" when the top passage passes the sidecar's confidence gate
(knowledge.py min_score / min_coverage). That is a retrieval signal, not a judgment of the
answer: the hand-judged numbers are in kb_metrics_external.json (see KB_CARD.md).
Topics are keyword rules on the title and tags, first match wins, in the order below.
Buddhism-site questions count only when they are about meditation practice.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evaluate_kb as ev  # noqa: E402

TOPICS: list[tuple[str, str]] = [
    ("meditation", r"meditat|mindful|vipassana|zazen|samatha|jhana|metta|body scan"),
    ("breathing", r"breath|pranayama|kapalbhati|anulom|nadi shodhana|wim hof|hyperventil"),
    ("yoga", r"\byoga|asana|pose\b|surya namaskar|sun salutation"),
    (
        "boxing_kickboxing",
        r"box(ing|er)|kickbox|muay thai|\bpunch|\bjab\b|hook|uppercut|"
        r"heavy bag|punching bag|\bkick|shin|sparring|thai pad",
    ),
    (
        "traditional_martial_arts",
        r"karate|kung fu|taekwondo|judo|aikido|jiu.?jitsu|\bbjj\b|"
        r"wing chun|kata\b|dojo|belt|martial|sensei|kendo|wrestl|self.?defen",
    ),
    (
        "calisthenics_skills",
        r"muscle.?up|front lever|back lever|planche|handstand|l.?sit|"
        r"pistol squat|human flag|calisthenics|one.?arm (push|pull)|dragon flag",
    ),
    ("mobility_flexibility", r"stretch|flexib|mobility|split|posture|foam roll|tight"),
    (
        "cardio_running",
        r"\brun|jog|marathon|5k|10k|sprint|interval|hiit|tabata|cardio|"
        r"cycl|bike|swim|rowing|treadmill|elliptical|jump rope|skipping",
    ),
    ("sleep_recovery", r"sleep|nap|recover|sore|doms|rest day|overtrain|ice bath"),
    (
        "supplements",
        r"supplement|creatine|whey|caffeine|pre.?workout|bcaa|vitamin|"
        r"ashwagandha|beta.?alanine|electrolyte|mass gainer",
    ),
    ("nutrition", r"protein|calori|diet|eat|food|carb|fat loss|bulk|cut\b|meal|fasting"),
    (
        "gym_strength",
        r"bench|squat|deadlift|press|curl|barbell|dumbbell|kettlebell|machine|"
        r"\bgym|lift|rows?\b|pull.?up|chin.?up|dip",
    ),
    ("injury_pain", r"pain|injur|hurt|knee|shoulder|back|wrist|elbow|ankle|tendon|strain"),
]
_RX = [(name, re.compile(rx, re.I)) for name, rx in TOPICS]
SITES = ("fitness", "martialarts", "buddhism", "health", "sports")


def topic_of(title: str, tags: list[str]) -> str:
    text = f"{title} {' '.join(tags).replace('-', ' ')}"
    for name, rx in _RX:
        if rx.search(text):
            return name
    return "other"


def scan(questions: Path, build: Path, intent_model: Path | None = None) -> dict:
    kn, model = ev.retriever(build, intent_model)
    total: Counter[str] = Counter()
    covered: Counter[str] = Counter()
    per_site: Counter[str] = Counter()
    for site in SITES:
        path = questions / f"{site}_questions.jsonl"
        if not path.exists():
            continue
        for line in path.open(encoding="utf-8"):
            q = json.loads(line)
            t = topic_of(q["title"], q.get("tags") or [])
            if site == "buddhism" and t != "meditation":
                continue
            per_site[site] += 1
            total[t] += 1
            top = ev.search(kn, model, q["title"])
            covered[t] += bool(top and top[0].confident)
    topics = {
        t: {"questions": n, "covered": covered[t], "share": round(covered[t] / n, 3)}
        for t, n in total.most_common()
    }
    return {
        "questions": sum(total.values()),
        "per_site": dict(per_site),
        "covered": sum(covered.values()),
        "topics": topics,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", type=Path, required=True)
    ap.add_argument("--build", type=Path, default=ev.KB / "build")
    ap.add_argument("--intent-model", type=Path)
    ap.add_argument("--out", type=Path, default=ev.ML / "reports" / "gap_scan.json")
    a = ap.parse_args()
    m = scan(a.questions, a.build, a.intent_model)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(m, indent=2))
    print(json.dumps(m, indent=2))


if __name__ == "__main__":
    main()
