"""BM25 retrieval over the bundled knowledge base (app/modules/ml/knowledge.py)."""

from __future__ import annotations

from app.modules.ml import knowledge


def test_tokens_fold_plurals_compounds_and_aliases() -> None:
    assert knowledge.tokens("Push-ups and pushups!") == knowledge.tokens("push up and pushup")
    assert "the" not in knowledge.tokens("the squat")


def test_focus_keeps_the_question_of_a_long_post() -> None:
    long = (
        "I have been training for two years and my routine has five days of lifting with "
        "some running on the weekend and a lot of walking. Is creatine safe for teenagers? "
        "Thanks in advance for any help with this."
    )
    assert knowledge.focus(long) == "Is creatine safe for teenagers?"
    assert knowledge.focus("is creatine safe") == "is creatine safe"


def test_food_questions_find_the_food_table() -> None:
    hits = knowledge.retrieve("protein in idli", 3, intent="nutrition_question")
    assert hits[0].id == "food:idli" and hits[0].confident


def test_exercise_howto_finds_instructions() -> None:
    ids = [h.id for h in knowledge.retrieve("how to do a plank", 3, intent="exercise_howto")]
    assert "fedb:Plank" in ids or "note:training_basics:plank-and-core-holds" in ids


def test_unrelated_text_is_not_confident() -> None:
    hits = knowledge.retrieve("garmin watch battery replacement", 3)
    assert not hits or not hits[0].confident


def test_citation_names_source_licence_and_place() -> None:
    hit = knowledge.retrieve("how much activity should adults do per week", 1)[0]
    c = knowledge.citation(hit)
    assert set(c) == {"passage_id", "title", "source", "licence", "url", "ref"}
    assert c["source"] and c["licence"] and c["url"].startswith("https://")


def test_sources_only_filters() -> None:
    hits = knowledge.retrieve("squat", 5, sources_only={"free_exercise_db"})
    assert hits and all(h.source == "free_exercise_db" for h in hits)


def test_k_is_clamped() -> None:
    assert len(knowledge.retrieve("squat", 50)) == 10
