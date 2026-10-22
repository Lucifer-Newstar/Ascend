"""muscle-map-v1 (ADR-0021): golden mappings, reachability and the v7 translation."""

import pytest

from app.modules.progress import muscle_map as mm
from app.modules.progress.taxonomy import LEGACY_REGIONS, MUSCLE_BY_KEY, MUSCLES
from app.modules.workouts import library

GOLDEN = [
    # (free-exercise-db name, primary, secondary, expected heads at weight 1.0, must include)
    ("Barbell Bench Press - Medium Grip", ["chest"], ["shoulders", "triceps"],
     {"pec_major_sternal"}, {"pec_major_clavicular", "deltoid_anterior", "triceps_lateral"}),
    ("Incline Dumbbell Press", ["chest"], ["shoulders", "triceps"],
     {"pec_major_clavicular"}, {"pec_major_sternal", "deltoid_anterior"}),
    ("Side Lateral Raise", ["shoulders"], [], {"deltoid_lateral"}, {"supraspinatus"}),
    ("Hammer Curls", ["biceps"], ["forearms"], {"brachialis", "brachioradialis"}, {"biceps_long"}),
    ("Triceps Pushdown", ["triceps"], [], {"triceps_lateral", "triceps_medial"}, {"triceps_long"}),
    ("Seated Calf Raise", ["calves"], [], {"soleus"}, {"gastrocnemius"}),
    ("Leg Extensions", ["quadriceps"], [],
     {"rectus_femoris", "vastus_lateralis", "vastus_medialis", "vastus_intermedius"}, set()),
    ("Pullups", ["lats"], ["biceps", "middle back"],
     {"latissimus_dorsi"}, {"teres_major", "rhomboids"}),
    ("Lying Leg Curls", ["hamstrings"], [],
     {"biceps_femoris", "semitendinosus", "semimembranosus"}, set()),
    ("Barbell Shrug", ["traps"], [], {"trap_upper"}, set()),
]  # fmt: skip


@pytest.mark.parametrize(("name", "primary", "secondary", "heads", "also"), GOLDEN)
def test_golden_mappings(name, primary, secondary, heads, also):
    got = mm.map_detailed(name, primary, secondary)
    assert {k for k, w in got.items() if w >= 1.0} == heads, got
    assert also <= set(got), got
    assert set(got) <= set(MUSCLE_BY_KEY)
    assert all(0.2 <= w <= 1.0 for w in got.values())


def test_mapping_is_deterministic():
    a = mm.map_detailed("Barbell Full Squat", ["quadriceps"], ["glutes", "hamstrings"])
    assert a == mm.map_detailed("Barbell Full Squat", ["quadriceps"], ["glutes", "hamstrings"])


def test_every_trainable_muscle_is_reachable_from_the_library():
    reach: dict[str, int] = {}
    for e in library.fedb_entries():
        for k, w in e.muscles.items():
            if w >= 0.5:
                reach[k] = reach.get(k, 0) + 1
    for m in MUSCLES:
        if not m.readiness_only:
            assert reach.get(m.key, 0) >= 3, m.key
    # the one muscle no library exercise loads still has a route: a custom exercise
    assert mm.refine_legacy({"calves": 1.0}, "Tibialis Raise") == {"tibialis_anterior": 1.0}


def test_translate_copies_the_weight_and_folds_back():
    v2 = mm.translate_legacy({"quads": 1.0, "glutes": 0.5})
    assert {k: v2[k] for k in ("vastus_lateralis", "vastus_medialis", "vastus_intermedius")} == {
        "vastus_lateralis": 1.0, "vastus_medialis": 1.0, "vastus_intermedius": 1.0,
    }  # fmt: skip
    assert v2["gluteus_maximus"] == 0.5
    assert mm.to_legacy(v2) == {"quads": 1.0, "glutes": 0.5}


def test_every_v7_region_has_a_v2_home():
    for region in LEGACY_REGIONS:
        v2 = mm.translate_legacy({region: 1.0})
        assert v2 and max(v2.values()) == 1.0, region
        assert set(v2) <= set(MUSCLE_BY_KEY)


def test_taxonomy_shape():
    assert len(MUSCLES) == 54
    assert len({m.key for m in MUSCLES}) == 54
    assert {m.region for m in MUSCLES} == {
        "Chest", "Back", "Neck", "Shoulders", "Arms", "Core", "Hips", "Thighs", "Lower legs",
    }  # fmt: skip
    for m in MUSCLES:
        assert m.map_slug == m.key
        if m.readiness_only:
            assert (m.weekly_low, m.weekly_high) == (0, 0), m.key
