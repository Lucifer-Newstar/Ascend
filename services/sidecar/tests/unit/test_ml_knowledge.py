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


# kb-v2 (trainer answers): the neighbouring-topic failures from the gap-fill eval.


def test_suffixes_and_two_word_names() -> None:
    assert knowledge.tokens("running") == knowledge.tokens("run")
    assert knowledge.tokens("meditating") == knowledge.tokens("meditation")
    assert "box" not in knowledge.tokens("box breathing")
    assert knowledge.tokens("boxing") != knowledge.tokens("box breathing")
    assert knowledge.tokens("front crawl") != knowledge.tokens("bear crawl")


def test_boxing_does_not_meet_box_breathing() -> None:
    q = "What kind of stretching should I do before starting my boxing practice?"
    ids = [h.id for h in knowledge.retrieve(q, 3, intent="training_question")]
    assert "note:meditation_breathing:box-breathing" not in ids
    assert "note:training_basics:stretching-before-or-after-exercise" in ids


def test_topic_keeps_running_questions_away_from_meditation() -> None:
    hits = knowledge.retrieve("Realistic best time for 5k?", 3, intent="training_question")
    assert all(not h.id.startswith("note:meditation_breathing") for h in hits)


def test_front_crawl_is_swimming_not_a_bear_crawl() -> None:
    hits = knowledge.retrieve("Swimming: why can I not front crawl?", 3, intent="training_question")
    assert all("bear-crawl" not in h.id.lower() for h in hits)


def test_unseen_words_lower_the_coverage() -> None:
    hits = knowledge.retrieve("Why doesn't aikido have kicking techniques?", 3)
    assert hits and not hits[0].confident


def test_the_answer_needs_a_question_word_in_its_title() -> None:
    hit = knowledge.retrieve("how much water should i drink", 1)[0]
    assert hit.id == "note:nutrition_basics:water-and-hydration"
    assert hit.title_hit and hit.confident and hit.close


def test_close_is_looser_than_confident() -> None:
    assert knowledge.CLOSE_SCORE < knowledge.MIN_SCORE
    assert knowledge.CLOSE_COVERAGE < knowledge.MIN_COVERAGE


def test_library_aliases_stand_in_for_the_name() -> None:
    ids = [h.id for h in knowledge.retrieve("how to do a bar hang", 3, intent="exercise_howto")]
    assert "lib:dario:dead-hang" in ids
