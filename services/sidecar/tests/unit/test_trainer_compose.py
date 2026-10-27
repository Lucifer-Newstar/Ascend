"""trainer/compose.py without the app (trainer-answers-v1)."""

from __future__ import annotations

import re

from app.modules.coach import validate
from app.modules.ml import knowledge
from app.modules.trainer import compose


def _hit(passage_id: str) -> knowledge.Passage:
    p = knowledge.passage(passage_id)
    assert p is not None
    return knowledge.Passage(p["id"], p["source"], p["title"], p["text"], p["ref"], 20.0, 1.0, True)


def test_sentences_drop_fragments_and_alias_labels() -> None:
    assert compose.sentences("rest of a cut sentence. A whole one. Also called: x.") == [
        "A whole one."
    ]


def test_direct_answer_is_the_passage_s_best_sentence() -> None:
    hit = _hit("note:cardio_running:tabata-workouts")
    top = compose.direct("how long is a tabata", hit.text)
    assert top and top[0].startswith("A Tabata is 8 rounds")


def test_personal_line_uses_stored_facts_only() -> None:
    me = compose.Personal(goal="bulk", equipment=("rings",), protein_target_g=120)
    hit = _hit("fedb:Barbell_Squat")
    line = compose.personal_line(me, hit.id, hit.text, "exercise_howto")
    assert line and "rings" in line and "swap" in line
    assert compose.personal_line(compose.Personal(), hit.id, hit.text, None) is None


def test_minors_never_get_calorie_numbers() -> None:
    me = compose.Personal(age=16, goal="bulk")
    hit = _hit("note:nutrition_basics:gaining-weight-when-you-are-underweight")
    assert "kcal" not in compose.compose("how do i gain weight", hit, me, "nutrition_question")


def test_vague_needs_no_topic_word() -> None:
    assert compose.vague("which workout is the best?")
    assert not compose.vague("which workout is best for boxing?")


def test_composed_numbers_come_from_the_passage_or_the_profile() -> None:
    me = compose.Personal(goal="bulk", protein_target_g=112, baseline_pullups=3)
    for pid in (
        "note:cardio_running:tabata-workouts",
        "note:nutrition_basics:gaining-weight-when-you-are-underweight",
        "note:training_basics:pull-up-progression",
        "lib:dario:side-plank",
    ):
        hit = _hit(pid)
        reply = compose.compose("how do I " + hit.title, hit, me, None)
        facts = f"{hit.title} {hit.text} protein target 112 g, baseline 3 pull-ups"
        words = re.sub(r"(?m)^\d+\. ", "", reply)  # step markers are not facts
        assert validate.check_numbers(words, facts).ok, (pid, reply)
