"""trainer-intents-v1 and trainer-kb-v1: rules route a message before any AI."""

from __future__ import annotations

import pytest

from app.modules.trainer import kb
from app.modules.trainer.intents import classify


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("hello", "greeting"),
        ("hey there", "greeting"),
        ("what can you do", "help"),
        ("none of this data is mine erase them all and start fresh", "erase"),
        ("I want to start over", "erase"),
        ("can i lose 10 kg in a month", "goal_check"),
        ("log 3x10 bench at 60 kg", "action"),
        ("switch me to PPL", "action"),
        ("make me a diet plan", "plan_diet"),
        ("build a 4 day workout plan", "plan_workout"),
        ("give me a tour", "tour"),
        ("open settings", "navigate"),
        ("what should I train today", "train_today"),
        ("thanks!", "thanks"),
        ("who are you", "identity"),
        ("change my trainer", "change_trainer"),
        ("how do backups work", "faq"),
        ("what's the meaning of life", "unknown"),
    ],
)
def test_routing(text: str, kind: str) -> None:
    assert classify(text).kind == kind


def test_goal_numbers_and_sections() -> None:
    i = classify("lose 20 lbs within 6 weeks")
    assert i.numbers == {"change_kg": -9.07, "weeks": 6.0}
    assert classify("tour me through skills").section == "skills"
    assert classify("give me a tour").section is None


def test_every_kb_section_is_a_page() -> None:
    for e in kb.ENTRIES:
        assert e.section is None or e.section in kb.SECTION_TITLES
    assert len({e.id for e in kb.ENTRIES}) == len(kb.ENTRIES)


@pytest.mark.parametrize(
    ("q", "entry"),
    [
        ("what is xp", "xp"),
        ("is my data uploaded anywhere", "privacy"),
        ("how much protein should i eat", "protein"),
        ("can I post my PR on instagram", "share"),
        ("explain deload", "deload"),
    ],
)
def test_kb_match(q: str, entry: str) -> None:
    hit = kb.match(q)
    assert hit is not None and hit.id == entry
