"""v1.4 gap fill: the new library entries are consistent with the library and the team."""

from __future__ import annotations

import re

from app.modules.progress.taxonomy import MUSCLES
from app.modules.trainer.team import AREAS, KEYWORDS, passage_area, topic
from app.modules.workouts.activity_seed import ACTIVITIES, SECTIONS
from app.modules.workouts.calisthenics_seed import CALISTHENICS
from app.modules.workouts.gap_fill_seed import ENTRIES, INSTRUCTIONS
from app.modules.workouts.library import fedb_entries
from app.modules.workouts.martial_arts_seed import DRILLS
from app.modules.workouts.seed import EXERCISES

KEYS = {m.key for m in MUSCLES}
SECTION_COACH = {
    "gym": {"idris"},
    "calisthenics": {"dario"},
    "cardio": {"kai"},
    "martial_arts": {"kai"},
    "flexibility": {"tara"},
    "meditation": {"tara"},
}


def test_entries_are_complete_and_owned_by_the_right_specialist() -> None:
    names = [e.name for e in ENTRIES]
    assert len(names) == len(set(names)) >= 60
    for e in ENTRIES:
        assert e.section in SECTIONS, e.name
        assert e.coach in AREAS and e.coach in SECTION_COACH[e.section], e.name
        assert e.measure in ("reps", "hold", "time"), e.name
        assert e.difficulty in ("beginner", "intermediate", "expert"), e.name
        assert len(e.instructions) >= 3, e.name
        assert set(e.muscles) <= KEYS, e.name
        assert all(w in (0.25, 0.5, 1.0) for w in e.muscles.values()), e.name


def test_new_names_do_not_clash_with_the_library() -> None:
    library = (
        {c["name"] for c in CALISTHENICS}
        | {d.name for d in DRILLS}
        | {a[0] for a in ACTIVITIES}
        | {e.name for e in fedb_entries()}
        | {name for name, _, _ in EXERCISES}
    )
    assert not {e.name.lower() for e in ENTRIES} & {n.lower() for n in library}


def test_written_steps_only_target_rows_that_exist() -> None:
    library = (
        {a[0] for a in ACTIVITIES}
        | {e.name for e in fedb_entries()}
        | {name for name, _, _ in EXERCISES}
    )
    assert set(INSTRUCTIONS) <= library
    assert {"Box Breathing", "Shadowboxing"} <= set(INSTRUCTIONS)
    assert all(len(steps) >= 3 for steps in INSTRUCTIONS.values())


def test_martial_arts_entries_stay_solo() -> None:
    banned = re.compile(r"\b(partner|spar\w*|opponent's (arm|neck)|choke|arm ?lock|takedown)\b")
    for e in ENTRIES:
        if e.section == "martial_arts":
            assert not banned.search(" ".join(e.instructions).lower()), e.name


def test_new_topics_route_to_the_specialist() -> None:
    assert topic("how do i throw a hook") == "kai"
    assert topic("best yoga poses for tight hips") == "tara"
    assert topic("how to start meditating") == "tara"
    assert topic("front lever progression") == "dario"
    assert passage_area("lib:kai:hook-shadow-drill") == "kai"
    assert passage_area("note:meditation_breathing:box-breathing") == "tara"
    assert passage_area("lib:nobody:x") is None
    assert set(KEYWORDS) == set(AREAS)
