"""Food rules (v1.2): Indian food guidance from the ICMR-NIN Dietary Guidelines for Indians
(2024), and a simple check of the day's logged meals against it.

The guidance is a short, plain-words summary of the guidelines (variety on "My Plate for the
Day", whole grains and millets, pulses for protein, salt about 5 g a day, little added sugar,
fewer ultra-processed HFSS foods, water, no protein supplements needed to build muscle). The
day check groups each logged food by keywords in its name, so it is a rough guide: it says
which groups are on the plate today, which are missing, and how many HFSS items there were.
It is guidance, not medical advice; nothing here changes calorie or protein targets.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

ALGO_VERSION = "foodrules-v1"
SOURCE = "Dietary Guidelines for Indians, ICMR-NIN 2024"

GUIDELINES: tuple[tuple[str, str], ...] = (
    (
        "Fill half the plate with vegetables and fruit",
        "My Plate for the Day: about half vegetables (greens and roots too) and fruit; the rest "
        "cereals or millets, pulses, eggs, fish or meat, with some nuts, seeds and curd or milk.",
    ),
    (
        "Choose whole grains and millets",
        "Ragi, jowar, bajra, brown or less polished rice and whole-wheat atta over maida and "
        "highly polished rice, most days.",
    ),
    (
        "Get protein from food",
        "Dal, chana, rajma, sprouts, curd, paneer, eggs, fish or chicken at most meals. Protein "
        "powders are not needed to build muscle for most people.",
    ),
    (
        "Keep salt to about 5 g a day",
        "About one teaspoon in all, counting pickles, papad, chips and namkeen.",
    ),
    (
        "Go easy on added sugar",
        "Sweets, sugary tea and coffee, soft drinks and packed juices add up fast. Keep "
        "added sugar low (under about 25 g a day).",
    ),
    (
        "Go easy on foods high in fat, salt or sugar",
        "Chips, instant noodles, biscuits, fried snacks and bakery items (HFSS foods) are "
        "for once in a while.",
    ),
    (
        "Use oils in moderation, and don't reuse frying oil",
        "Rotate a few oils, keep visible fat modest, and avoid reheating the same oil for frying.",
    ),
    ("Drink enough water", "About 8 glasses a day, more on hot days and after training."),
    ("Read the label", "Check serving size, sugar, salt and fat on packed foods before you buy."),
)

# Keyword groups for the day check (lower-case substrings of food names).
GROUPS: dict[str, tuple[str, ...]] = {
    "cereals_millets": (
        "rice",
        "roti",
        "chapati",
        "phulka",
        "paratha",
        "idli",
        "dosa",
        "upma",
        "poha",
        "oats",
        "bread",
        "ragi",
        "jowar",
        "bajra",
        "millet",
        "pongal",
        "khichdi",
        "biryani",
        "pulao",
        "daliya",
        "puttu",
        "appam",
        "noodles",
        "pasta",
        "uttapam",
        "idiyappam",
        "naan",
        "parotta",
        "muesli",
        "cornflakes",
        "corn",
        "chawal",
        "bhature",
        "pav",
        "sandwich",
        "momos",
        "pizza",
        "burger",
    ),
    "pulses": (
        "dal",
        "sambar",
        "chana",
        "rajma",
        "chole",
        "moong",
        "sprout",
        "lentil",
        "besan",
        "chickpea",
        "lobia",
        "dhokla",
        "pesarattu",
        "soya",
        "sundal",
    ),
    "vegetables": (
        "sabzi",
        "salad",
        "palak",
        "spinach",
        "bhindi",
        "gobi",
        "aloo",
        "carrot",
        "beans",
        "cabbage",
        "poriyal",
        "thoran",
        "avial",
        "vegetable",
        "veg",
        "cucumber",
        "tomato",
        "rasam",
        "methi",
        "baingan",
        "lauki",
        "kootu",
        "brinjal",
        "sweet potato",
    ),
    "fruit": (
        "banana",
        "apple",
        "orange",
        "papaya",
        "mango",
        "guava",
        "grapes",
        "watermelon",
        "fruit",
        "pomegranate",
        "chikoo",
        "sapota",
        "pineapple",
        "dates",
        "raisin",
    ),
    "milk_curd": (
        "milk",
        "curd",
        "dahi",
        "buttermilk",
        "chaas",
        "lassi",
        "paneer",
        "raita",
        "yogurt",
        "cheese",
        "kheer",
        "payasam",
    ),
    "eggs_fish_meat": (
        "egg",
        "omelette",
        "chicken",
        "fish",
        "mutton",
        "prawn",
        "meat",
        "keema",
        "tuna",
    ),
    "nuts_seeds": (
        "almond",
        "badam",
        "peanut",
        "groundnut",
        "walnut",
        "cashew",
        "seeds",
        "chikki",
        "nuts",
        "flax",
    ),
}
HFSS: tuple[str, ...] = (
    "chips",
    "namkeen",
    "instant noodles",
    "maggi",
    "biscuit",
    "cookie",
    "samosa",
    "pakora",
    "bhaji",
    "vada",
    "puri",
    "bhatura",
    "cake",
    "pastry",
    "jalebi",
    "gulab jamun",
    "ladoo",
    "soft drink",
    "cola",
    "fries",
    "pizza",
    "burger",
    "mixture",
    "kachori",
    "chocolate",
    "ice cream",
    "bonda",
    "murukku",
    "rasgulla",
    "kesari",
    "mysore pak",
    "laddu",
    "kheer",
    "payasam",
    "pickle",
)
GROUP_LABEL = {
    "cereals_millets": "Cereals and millets",
    "pulses": "Pulses",
    "vegetables": "Vegetables",
    "fruit": "Fruit",
    "milk_curd": "Milk and curd",
    "eggs_fish_meat": "Eggs, fish or meat",
    "nuts_seeds": "Nuts and seeds",
}
# Eggs, fish and meat are optional (vegetarians get their protein from pulses and milk).
CORE = ("cereals_millets", "pulses", "vegetables", "fruit", "milk_curd", "nuts_seeds")


def _pattern(words: Iterable[str]) -> re.Pattern[str]:
    # A keyword matches at the start of a word, so "sprout" finds "sprouts" but "roti"
    # does not find "protein bar".
    return re.compile(r"\b(?:" + "|".join(re.escape(w) for w in words) + ")", re.IGNORECASE)


_GROUP_RE = {g: _pattern(words) for g, words in GROUPS.items()}
_HFSS_RE = _pattern(HFSS)


def groups_of(name: str) -> set[str]:
    return {g for g, rx in _GROUP_RE.items() if rx.search(name)}


def is_hfss(name: str) -> bool:
    return bool(_HFSS_RE.search(name))


@dataclass
class DayCheck:
    counts: dict[str, int] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    hfss: list[str] = field(default_factory=list)
    tips: list[str] = field(default_factory=list)
    foods: int = 0


def check_day(food_names: Iterable[str]) -> DayCheck:
    """Group the day's logged foods and turn the gaps into at most three tips."""
    names = list(food_names)
    out = DayCheck(counts={g: 0 for g in GROUPS}, foods=len(names))
    for n in names:
        for g in groups_of(n):
            out.counts[g] += 1
        if is_hfss(n):
            out.hfss.append(n)
    if not names:
        out.tips.append("Log your meals and I'll check them against India's food guidelines.")
        return out
    out.missing = [g for g in CORE if out.counts[g] == 0]
    no_veg, no_fruit = "vegetables" in out.missing, "fruit" in out.missing
    if no_veg and no_fruit:
        out.tips.append("Add a vegetable or a piece of fruit: half the plate is the target.")
    elif no_veg:
        out.tips.append("No vegetables yet: a sabzi, salad or poriyal fills half the plate.")
    elif no_fruit:
        out.tips.append("No fruit yet: a banana, guava or orange is an easy add.")
    if "pulses" in out.missing and out.counts["eggs_fish_meat"] == 0:
        out.tips.append("No pulses yet: a katori of dal, chana or sprouts adds protein and fibre.")
    if len(out.hfss) >= 2:
        out.tips.append(
            f"{len(out.hfss)} foods high in fat, salt or sugar today; swap the next one for "
            "fruit, curd or nuts."
        )
    if not out.tips:
        out.tips.append("A varied plate today. Keep the salt and added sugar low.")
    return out
