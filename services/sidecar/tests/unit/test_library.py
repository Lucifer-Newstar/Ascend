from app.modules.progress.taxonomy import LEGACY_REGIONS, MUSCLE_BY_KEY
from app.modules.workouts import library
from app.modules.workouts.calisthenics_seed import CALISTHENICS


def test_normalize_ignores_case_hyphens_plurals_and_word_order():
    assert library.normalize("Pull-Ups") == library.normalize("pullup") == "pull up"
    assert library.normalize("Curl, Barbell") == library.normalize("Barbell Curls")
    assert library.normalize("Lateral Raises") == library.normalize("lateral raise")
    assert library.normalize("Bench Press") != library.normalize("Bench Pres")


def test_search_matches_word_prefixes_and_aliases():
    assert library.matches_query("pullups", "Pull-up", [])
    assert library.matches_query("front lev", "Tuck Front Lever", [])
    assert library.matches_query("ohp", "Overhead Press", ["ohp"])
    assert not library.matches_query("squat", "Bench Press", [])


def test_shoulder_and_chest_heads_follow_the_name():
    # v7 coarse mapping, still used to seed the library rows migrations read
    assert library.map_muscles("Side Lateral Raise", ["shoulders"], []) == {"side_delts": 1.0}
    assert library.map_muscles("Reverse Flyes", ["shoulders"], []) == {"rear_delts": 1.0}
    press = library.map_muscles("Dumbbell Shoulder Press", ["shoulders"], ["triceps"])
    assert press == {"front_delts": 1.0, "side_delts": 0.5, "triceps": 0.5}
    incline = library.map_muscles("Incline Dumbbell Press", ["chest"], [])
    assert incline == {"upper_chest": 1.0, "lower_chest": 0.5}


def test_every_fedb_entry_maps_to_known_values():
    entries = library.fedb_entries()
    assert len(entries) > 800
    for e in entries:
        assert set(e.muscles) <= set(MUSCLE_BY_KEY), e.name
        assert all(0 < w <= 1 for w in e.muscles.values()), e.name
        assert e.measure in library.MEASURES
        assert e.pattern in library.PATTERNS
        assert e.difficulty in (*library.DIFFICULTIES, None)
        assert e.section in ("gym", "calisthenics", "cardio", "flexibility")
        if e.section == "flexibility":
            assert e.muscles == {}  # stretches load nothing, like the hand-made list
        if e.section == "cardio" and e.source_id not in library.FEDB_DUPLICATES:
            assert e.met and e.met > 1, e.name  # every cardio entry gets a calorie estimate


def test_static_holds_are_measured_in_seconds():
    plank = next(e for e in library.fedb_entries() if e.source_id == "Plank")
    assert plank.measure == "hold"
    assert library.default_range("hold") == (10, 30)


def test_calisthenics_rows_use_known_muscles_and_measures():
    names = [r["name"] for r in CALISTHENICS]
    assert len(names) == len(set(names))
    for row in CALISTHENICS:
        # the hand-made rows are written in the 19 v7 regions; migration 0018 translates them
        assert set(row["muscles"]) <= set(LEGACY_REGIONS), row["name"]
        assert row["measure"] in ("reps", "hold")
        assert row["instructions"], row["name"]


def test_duplicate_map_points_at_real_fedb_ids():
    ids = {e.source_id for e in library.fedb_entries()}
    assert set(library.FEDB_DUPLICATES) <= ids


def test_best_matches_ranks_exact_alias_then_fuzzy():
    cands = [(1, "Pull-up", ["pullups"]), (2, "Chin-up", []), (3, "Push-up", [])]
    assert library.best_matches("pull ups", cands)[0].via == "exact"
    fuzzy = library.best_matches("pul-up", cands)
    assert fuzzy[0].exercise_id == 1 and fuzzy[0].via == "fuzzy"
    assert library.best_matches("", cands) == []
