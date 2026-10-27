"""v1.4 knowledge-gap tools: the topic rules and the held-out gap ids."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ML = Path(__file__).resolve().parents[1]


def _gap_scan():
    path = ML / "knowledge" / "src" / "gap_scan.py"
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("gap_scan", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_topic_rules_pick_the_specific_topic_first() -> None:
    gs = _gap_scan()
    assert gs.topic_of("How do I stop my mind wandering?", ["meditation"]) == "meditation"
    assert gs.topic_of("How to throw a proper hook", ["boxing"]) == "boxing_kickboxing"
    assert gs.topic_of("Is my karate kata stance right?", []) == "traditional_martial_arts"
    assert gs.topic_of("First muscle-up tips", []) == "calisthenics_skills"
    assert gs.topic_of("Best time to weigh yourself", []) == "other"


def test_gap_eval_ids_are_numeric_and_unique() -> None:
    lines = (ML / "intent" / "labels" / "gap_eval_ids.txt").read_text().splitlines()
    ids = [x.strip() for x in lines if x.strip() and not x.startswith("#")]
    assert ids and all(x.isdigit() for x in ids) and len(ids) == len(set(ids))
