import pytest

from app.modules.io.matcher import ALIASES, ExerciseMatcher, normalise
from app.modules.workouts.activity_seed import ACTIVITIES
from app.modules.workouts.seed import EXERCISES

LIBRARY = [name for name, *_ in EXERCISES] + [name for name, *_ in ACTIVITIES]


@pytest.fixture(scope="module")
def matcher() -> ExerciseMatcher:
    return ExerciseMatcher(LIBRARY)


def test_normalise_folds_case_hyphens_and_plurals():
    assert normalise("Pull-Ups") == "pull up"
    assert normalise("  Cable Crossovers ") == "cable crossover"
    assert normalise("Bench Press") == "bench press"  # "press" keeps its double s


@pytest.mark.parametrize(
    ("source", "ascend"),
    [
        ("Bench Press (Barbell)", "Barbell Bench Press"),  # alias
        ("Squat (Barbell)", "Back Squat"),
        ("Triceps Pushdown (Cable - Straight Bar)", "Triceps Pushdown"),
        ("Pull Up", "Pull-up"),
        ("Lat Pulldown (Cable)", "Lat Pulldown"),
        ("Bicep Curl (Dumbbell)", "Dumbbell Curl"),
        ("Hip Thrust (Barbell)", "Hip Thrust"),
        ("Treadmill", "Running"),
        ("Overhead Press (Barbell)", "Overhead Press"),
        ("Front Squat (Barbell)", "Front Squat"),  # equipment-first rule
        ("Barbell Rows", "Barbell Row"),  # plural
        ("Leg Extensions", "Leg Extension"),
        ("Deadlifts", "Deadlift"),
    ],
)
def test_maps_common_strong_and_hevy_names(matcher, source, ascend):
    assert matcher.match(source) == ascend


@pytest.mark.parametrize("source", ["Zercher Good Morning (Barbell)", "Sled Push", "", "   "])
def test_unknown_movements_stay_unmatched(matcher, source):
    assert matcher.match(source) is None


def test_every_alias_points_at_a_real_library_exercise():
    missing = sorted({v for v in ALIASES.values() if v not in LIBRARY})
    assert missing == []


def test_lookups_are_cached(matcher):
    first = matcher.match("Bench Press (Barbell)")
    assert matcher._cache["Bench Press (Barbell)"] == first
