"""dietgen-v1: a day-by-day meal plan from the TDEE engine's targets and the food table.

The calorie and protein targets come from the energy engine (tdee-v1 / adaptive TDEE),
then pass goalcheck-v1 (a calorie floor, a protein band). Meals are built from fixed,
everyday South-Indian templates using only foods in ASCEND's food table, with portions in
the table's own units (pieces, katori, tbsp, glass), scaled to each meal's share of the
day. Deterministic: the same targets give the same week. The local model may reword the
notes, never the numbers.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

ALGO_VERSION = "dietgen-v1"

Diet = Literal["veg", "egg", "nonveg"]
Meal = Literal["breakfast", "lunch", "snack", "dinner"]

MEAL_SHARE: dict[str, float] = {"breakfast": 0.25, "lunch": 0.35, "snack": 0.1, "dinner": 0.3}
NON_VEG = {"Chicken biryani", "Chicken curry", "Fish curry"}
EGG = {"Boiled egg"}
# The first food of each template is its "base": its portion scales to hit the meal's share;
# the others are fixed sides (portion multiples of the table's unit).
TEMPLATES: dict[str, tuple[tuple[tuple[str, float], ...], ...]] = {
    "breakfast": (
        (("Idli", 3), ("Sambar", 1), ("Coconut chutney", 1)),
        (("Plain dosa", 2), ("Sambar", 1), ("Peanut chutney", 1)),
        (("Rava upma", 1), ("Boiled egg", 2)),
        (("Ven pongal", 1), ("Sambar", 1), ("Tomato chutney", 1)),
        (("Idli", 3), ("Sambar", 1), ("Boiled egg", 2)),
        (("Plain dosa", 2), ("Sambar", 1), ("Coconut chutney", 1)),
        (("Masala dosa", 1), ("Sambar", 1)),
    ),
    "lunch": (
        (("Steamed rice", 1), ("Toor dal", 1), ("Mixed veg poriyal", 1), ("Curd (plain)", 1)),
        (("Chapati", 2), ("Chicken curry", 1), ("Mixed veg poriyal", 1)),
        (("Steamed rice", 1), ("Sambar", 1), ("Mixed veg poriyal", 1), ("Curd (plain)", 1)),
        (("Chapati", 2), ("Rajma curry", 1), ("Curd (plain)", 1)),
        (("Steamed rice", 1), ("Fish curry", 1), ("Rasam", 1)),
        (("Chapati", 2), ("Palak paneer", 1), ("Mixed veg poriyal", 1)),
        (("Chicken biryani", 1), ("Curd (plain)", 1)),
    ),
    "snack": (
        (("Sundal (chickpea)", 1), ("Buttermilk", 1)),
        (("Banana", 1), ("Boiled egg", 1)),
        (("Curd (plain)", 1), ("Banana", 1)),
        (("Sundal (chickpea)", 1), ("Filter coffee (with milk, sugar)", 1)),
    ),
    "dinner": (
        (("Chapati", 2), ("Chana masala", 1), ("Curd (plain)", 1)),
        (("Chapati", 2), ("Chicken curry", 1)),
        (("Idli", 3), ("Sambar", 1), ("Peanut chutney", 1)),
        (("Chapati", 2), ("Palak paneer", 1)),
        (("Curd rice", 1), ("Mixed veg poriyal", 1)),
        (("Chapati", 2), ("Toor dal", 1), ("Mixed veg poriyal", 1)),
        (("Steamed rice", 1), ("Fish curry", 1), ("Mixed veg poriyal", 1)),
    ),
}
# Veg swaps for the non-veg/egg sides when the user doesn't eat them.
SWAPS: dict[str, dict[str, str]] = {
    "veg": {
        "Chicken curry": "Chana masala",
        "Fish curry": "Rajma curry",
        "Chicken biryani": "Veg biryani",
        "Boiled egg": "Curd (plain)",
    },
    "egg": {
        "Chicken curry": "Chana masala",
        "Fish curry": "Rajma curry",
        "Chicken biryani": "Veg biryani",
    },
    "nonveg": {},
}
PIECE_UNITS = ("piece", "medium", "tumbler", "glass")


@dataclass(frozen=True)
class FoodInfo:
    name: str
    portion_label: str
    kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float

    @property
    def counted(self) -> bool:
        return any(u in self.portion_label for u in PIECE_UNITS)


@dataclass(frozen=True)
class Item:
    food: str
    portions: float
    portion_label: str
    kcal: int
    protein_g: float


@dataclass(frozen=True)
class MealPlan:
    meal: str
    items: tuple[Item, ...]

    @property
    def kcal(self) -> int:
        return sum(i.kcal for i in self.items)

    @property
    def protein_g(self) -> float:
        return round(sum(i.protein_g for i in self.items), 1)


@dataclass(frozen=True)
class DayPlan:
    day: int  # 0 = Monday
    meals: tuple[MealPlan, ...]

    @property
    def kcal(self) -> int:
        return sum(m.kcal for m in self.meals)

    @property
    def protein_g(self) -> float:
        return round(sum(m.protein_g for m in self.meals), 1)


@dataclass(frozen=True)
class GeneratedDiet:
    kcal_target: int
    protein_target_g: int
    diet: Diet
    days: tuple[DayPlan, ...]
    notes: tuple[str, ...] = field(default=())
    algo_version: str = ALGO_VERSION


def _round_portion(x: float, counted: bool) -> float:
    step = 1.0 if counted else 0.5
    return max(step, round(x / step) * step)


def _item(f: FoodInfo, portions: float) -> Item:
    return Item(
        f.name,
        portions,
        f.portion_label,
        round(f.kcal * portions),
        round(f.protein_g * portions, 1),
    )


def build_meal(
    template: tuple[tuple[str, float], ...],
    target_kcal: float,
    foods: Mapping[str, FoodInfo],
    diet: Diet,
) -> MealPlan | None:
    swaps = SWAPS[diet]
    parts = [(swaps.get(n, n), p) for n, p in template]
    if diet == "veg" and any(n in NON_VEG | EGG for n, _ in parts):
        return None
    if diet == "egg" and any(n in NON_VEG for n, _ in parts):
        return None
    if any(n not in foods for n, _ in parts):
        return None
    base_name, base_p = parts[0]
    base = foods[base_name]
    sides = [_item(foods[n], p) for n, p in parts[1:]]
    side_kcal = sum(i.kcal for i in sides)
    want = max(target_kcal - side_kcal, base.kcal * 0.5) / base.kcal
    portions = _round_portion(max(want, base_p * 0.5), base.counted)
    portions = min(portions, base_p * 3)  # never more than 3x the usual serving
    return MealPlan("", (_item(base, portions), *sides))


def generate(
    kcal_target: int, protein_target_g: int, foods: Mapping[str, FoodInfo], diet: Diet = "nonveg"
) -> GeneratedDiet:
    days: list[DayPlan] = []
    for d in range(7):
        meals: list[MealPlan] = []
        for meal, share in MEAL_SHARE.items():
            options = TEMPLATES[meal]
            built = None
            for k in range(len(options)):
                built = build_meal(
                    options[(d + k) % len(options)], kcal_target * share, foods, diet
                )
                if built is not None:
                    break
            if built is not None:
                meals.append(MealPlan(meal, built.items))
        days.append(DayPlan(d, tuple(meals)))
    avg_kcal = round(sum(x.kcal for x in days) / len(days))
    avg_protein = round(sum(x.protein_g for x in days) / len(days))
    notes = [
        f"Plan averages {avg_kcal} kcal and {avg_protein} g protein a day "
        f"(targets {kcal_target} kcal, {protein_target_g} g)."
    ]
    if avg_protein < protein_target_g * 0.9:
        notes.append(
            f"About {protein_target_g - avg_protein} g of protein short: add a boiled egg, a "
            f"katori of curd or sundal, or paneer to reach {protein_target_g} g."
            if diet != "veg"
            else f"About {protein_target_g - avg_protein} g of protein short: add curd, sundal "
            f"or paneer to reach {protein_target_g} g."
        )
    return GeneratedDiet(kcal_target, protein_target_g, diet, tuple(days), tuple(notes))
