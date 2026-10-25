"""resolve-v2: a typed name -> the food or exercise the user means.

v1.2 picked the shortest name containing the words, so "2 egg" became Egg biryani and
"had milk" Badam milk. v1.3 ranks candidates: an alias the app knows ("egg" is a boiled
egg, "tea" is masala chai), then the exact name, then the plain/base dish ("Milk" for
"Milk (toned)"), then names starting with the words, then names holding every word. When
two or more different dishes are equally good ("biryani"), it asks instead of guessing.
Typos get one forgiving pass (difflib), and exercises respect the user's equipment.
"""

from __future__ import annotations

import difflib
import re
from collections.abc import Callable, Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.nutrition.models import Food
from app.modules.workouts.models import Exercise

RESOLVE_VERSION = "resolve-v2"


class NotFoundError(Exception):
    """Nothing in the table fits the name."""


class AmbiguousError(Exception):
    """More than one different thing fits equally well; the user picks."""

    def __init__(self, query: str, options: Sequence[str]) -> None:
        self.query = query
        self.options = list(options)
        super().__init__(f"Which {query} do you mean: {_or_list(self.options)}?")


def _or_list(names: Sequence[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " or " + names[-1]


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _singular(w: str) -> str:
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("es") and w[-3] in "sxh":
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def _words(s: str) -> list[str]:
    return [_singular(w) for w in norm(s).split()]


def base_name(name: str) -> str:
    """'Milk (toned)' -> 'milk'; 'Bajji / pakora' -> 'bajji'."""
    return norm(re.split(r"[(/]", name)[0])


# Everyday words -> the food table's name. A tuple means "these items together".
FOOD_ALIASES: dict[str, str | tuple[str, ...]] = {
    "egg": "Boiled egg",
    "boiled egg": "Boiled egg",
    "anda": "Boiled egg",
    "muttai": "Boiled egg",
    "omelette": "Omelette (2 eggs)",
    "omelet": "Omelette (2 eggs)",
    "milk": "Milk (toned)",
    "paal": "Milk (toned)",
    "rice": "Steamed rice",
    "white rice": "Steamed rice",
    "plain rice": "Steamed rice",
    "sadam": "Steamed rice",
    "saadam": "Steamed rice",
    "chawal": "Steamed rice",
    "tea": "Masala chai (milk, sugar)",
    "chai": "Masala chai (milk, sugar)",
    "milk tea": "Masala chai (milk, sugar)",
    "coffee": "Filter coffee (with milk, sugar)",
    "kaapi": "Filter coffee (with milk, sugar)",
    "dosa": "Plain dosa",
    "dosai": "Plain dosa",
    "thosai": "Plain dosa",
    "plain dosai": "Plain dosa",
    "vada": "Medu vada",
    "vadai": "Medu vada",
    "medhu vada": "Medu vada",
    "idly": "Idli",
    "iddli": "Idli",
    "chapathi": "Chapati",
    "chappathi": "Chapati",
    "chapatti": "Chapati",
    "chappati": "Chapati",
    "roti": "Chapati",
    "rotis": "Chapati",
    "phulka": "Phulka (no oil)",
    "parota": "Parotta",
    "porotta": "Parotta",
    "barotta": "Parotta",
    "paratha": "Plain paratha",
    "pongal": "Ven pongal",
    "khara pongal": "Ven pongal",
    "sweet pongal": "Sakkarai pongal",
    "chutney": "Coconut chutney",
    "chatni": "Coconut chutney",
    "coconut chatni": "Coconut chutney",
    "upma": "Rava upma",
    "poriyal": "Mixed veg poriyal",
    "dal": "Toor dal",
    "dhal": "Toor dal",
    "daal": "Toor dal",
    "paruppu": "Toor dal",
    "dal rice": ("Toor dal", "Steamed rice"),
    "sambar rice": ("Sambar", "Steamed rice"),
    "rasam rice": ("Rasam", "Steamed rice"),
    "curd": "Curd (plain)",
    "thayir": "Curd (plain)",
    "dahi": "Curd (plain)",
    "yogurt": "Curd (plain)",
    "paneer": "Paneer (plain)",
    "oats": "Oats (cooked in water)",
    "oatmeal": "Oats (cooked in water)",
    "maggi": "Maggi noodles (masala)",
    "noodles": "Maggi noodles (masala)",
    "kichadi": "Khichdi",
    "kichdi": "Khichdi",
    "khichadi": "Khichdi",
    "poori": "Puri",
    "puri": "Puri",
    "bread": "Bread (white)",
    "brown bread": "Bread (whole wheat)",
    "chickpea": "Chickpeas (boiled)",
    "chana": "Chickpeas (boiled)",
    "sprouts": "Moong sprouts salad",
    "soya": "Soya chunks (boiled)",
    "peanut": "Peanuts (roasted)",
    "groundnut": "Peanuts (roasted)",
    "nuts": "Mixed nuts",
    "badam": "Almonds",
    "biscuit": "Marie biscuits",
    "chips": "Potato chips",
    "fries": "French fries",
    "pizza": "Veg pizza",
    "shawarma": "Chicken shawarma roll",
    "salad": "Green salad",
    "soup": "Vegetable soup",
    "whey": "Whey protein (in water)",
    "protein shake": "Whey protein (in water)",
    "whey shake": "Whey protein (in water)",
    "juice": "Orange juice (fresh)",
    "coke": "Cola (soft drink)",
    "cola": "Cola (soft drink)",
    "pepsi": "Cola (soft drink)",
    "coconut water": "Tender coconut water",
    "elaneer": "Tender coconut water",
    "kheer": "Payasam / kheer",
    "payasam": "Payasam / kheer",
    "pakora": "Bajji / pakora",
    "bajji": "Bajji / pakora",
    "ragi": "Ragi ball (mudde)",
    "ragi mudde": "Ragi ball (mudde)",
    "kali": "Ragi ball (mudde)",
    "sweet potato": "Sweet potato (boiled)",
    "corn": "Sweet corn (boiled)",
    "chikoo": "Sapota (chikoo)",
    "sapota": "Sapota (chikoo)",
    "laddu": "Besan laddu",
    "ice cream": "Ice cream (vanilla)",
    "chocolate": "Dark chocolate",
    "tuna": "Tuna (canned in water)",
    "sundal": "Sundal (chickpea)",
    "momo": "Veg momos (steamed)",
    "veg momo": "Veg momos (steamed)",
    "chicken momo": "Chicken momos (steamed)",
}
# Grams lines lean on the plain cut ("chicken 200g" is grilled breast, not Chicken 65).
GRAM_ALIASES: dict[str, str] = {
    "chicken": "Chicken breast (grilled)",
    "chicken breast": "Chicken breast (grilled)",
    "rice": "Steamed rice",
    "paneer": "Paneer (plain)",
    "oats": "Oats (cooked in water)",
    "fish": "Fish fry",
}


def _foods(db: Session) -> list[Food]:
    return list(db.scalars(select(Food).order_by(Food.id)))


def _by_name(foods: Iterable[Food]) -> dict[str, Food]:
    return {norm(f.name): f for f in foods}


def resolve_foods(db: Session, query: str, grams: bool = False) -> list[Food]:
    """The food(s) a typed name means. One entry, or several for a combo alias ("dal rice").
    Raises NotFoundError or AmbiguousError."""
    foods = _foods(db)
    names = _by_name(foods)
    q = norm(query)
    if not q:
        raise NotFoundError(query)
    qs = " ".join(_words(q))
    for key in (q, qs):
        target = (GRAM_ALIASES.get(key) if grams else None) or FOOD_ALIASES.get(key)
        if target:
            wanted = (target,) if isinstance(target, str) else target
            hits = [names[norm(t)] for t in wanted if norm(t) in names]
            if len(hits) == len(wanted):
                return hits
    # 1. exact name; 2. the base dish ("milk" -> "Milk (toned)"); 3. starts with; 4. words
    for key in (q, qs):
        if key in names:
            return [names[key]]
    base = [f for f in foods if " ".join(_words(base_name(f.name))) == qs]
    if base:
        return [_one(query, base)]
    qw = qs.split()
    starts = [f for f in foods if " ".join(_words(f.name)).startswith(qs + " ")]
    if starts:
        return [_one(query, starts)]
    words = [f for f in foods if all(w in _words(f.name) for w in qw)]
    if words:
        return [_one(query, words)]
    # 5. forgiving pass for typos ("chapathi", "idlly"): one close name, or ask.
    close = difflib.get_close_matches(qs, list(names), n=3, cutoff=0.82)
    close += [
        n
        for n in names
        if any(difflib.SequenceMatcher(None, qs, b).ratio() >= 0.85 for b in [base_name(n)])
    ]
    seen: list[Food] = []
    for n in close:
        if names[n] not in seen:
            seen.append(names[n])
    if seen:
        return [_one(query, seen)]
    alias = difflib.get_close_matches(qs, list(FOOD_ALIASES), n=1, cutoff=0.85)
    if alias:
        return resolve_foods(db, alias[0], grams)
    raise NotFoundError(query)


def _one(query: str, cands: list[Food]) -> Food:
    """One candidate, or the default of one dish's variants; ask between different dishes."""
    if len(cands) == 1:
        return cands[0]
    bases = {base_name(f.name) for f in cands}
    if len(bases) == 1:
        return cands[0]  # e.g. Chicken breast (grilled) / (boiled): the table's first
    raise AmbiguousError(query, [f.name for f in cands[:4]])


def strict_food(db: Session, query: str, exact_only: bool = False) -> list[Food] | None:
    """A bare line ("ven pongal", "chutney") is food only when it names one exactly or
    through an alias; "water" or "rest" never become a log."""
    q = norm(query)
    if not q or len(q.split()) > 4:
        return None
    names = _by_name(_foods(db))
    qs = " ".join(_words(q))
    if exact_only:
        return [names[q]] if q in names and len(q.split()) >= 2 else None
    for key in (q, qs):
        target = FOOD_ALIASES.get(key)
        if target:
            wanted = (target,) if isinstance(target, str) else target
            if all(norm(t) in names for t in wanted):
                return [names[norm(t)] for t in wanted]
        if key in names:
            return [names[key]]
    base = [f for f in names.values() if base_name(f.name) == q]
    return base[:1] or None


# --- exercises ---------------------------------------------------------------------------

# Everyday names -> library names, best first; the first one the user's kit allows wins.
EXERCISE_ALIASES: dict[str, tuple[str, ...]] = {
    "bench": ("Barbell Bench Press", "Dumbbell Bench Press", "Push-up"),
    "bench press": ("Barbell Bench Press", "Dumbbell Bench Press", "Dumbbell Floor Press"),
    "db bench": ("Dumbbell Bench Press", "Dumbbell Floor Press"),
    "db bench press": ("Dumbbell Bench Press", "Dumbbell Floor Press"),
    "dumbbell bench": ("Dumbbell Bench Press", "Dumbbell Floor Press"),
    "floor press": ("Dumbbell Floor Press", "Floor Press"),
    "squat": ("Back Squat", "Goblet Squat", "Bodyweight Squat"),
    "bodyweight squat": ("Bodyweight Squat",),
    "air squat": ("Bodyweight Squat",),
    "deadlift": ("Deadlift", "Stiff-Legged Dumbbell Deadlift"),
    "ohp": ("Overhead Press", "Seated Dumbbell Shoulder Press", "Pike Push-up"),
    "shoulder press": ("Overhead Press", "Seated Dumbbell Shoulder Press", "Pike Push-up"),
    "pullup": ("Pull-up",),
    "ring pullup": ("Pull-up",),
    "chinup": ("Chin-up",),
    "pushup": ("Push-up",),
    "situp": ("Sit-Up",),
    "crunch": ("Crunches",),
    "dip": ("Ring Dip", "Chest Dip", "Bench Dips"),
    "ring dip": ("Ring Dip",),
    "ring row": ("Inverted Row",),
    "row": ("Barbell Row", "One-arm Dumbbell Row", "Inverted Row"),
    "curl": ("Barbell Curl", "Dumbbell Curl"),
    "db curl": ("Dumbbell Curl",),
    "bicep curl": ("Barbell Curl", "Dumbbell Curl"),
    "lunge": ("Walking Lunge", "Bodyweight Walking Lunge"),
    "calf raise": (
        "Standing Calf Raise",
        "Standing Dumbbell Calf Raise",
        "Calf Raise On A Dumbbell",
        "Rocking Standing Calf Raise",
    ),
    "hang": ("Dead Hang",),
    "bar hang": ("Dead Hang",),
    "plank": ("Plank",),
    "leg raise": ("Hanging Leg Raise", "Lying Leg Raise"),
    "burpee": ("Burpee",),
    "jumping jack": ("Jumping Jack",),
    "star jump": ("Jumping Jack", "Star Jump"),
    "wall sit": ("Wall Sit",),
    "skipping": ("Jump Rope",),
    "pike pushup": ("Pike Push-up",),
    "diamond pushup": ("Diamond Push-up",),
    "knee pushup": ("Incline Push-up",),
}


def compact(s: str) -> str:
    """'Push-ups' / 'push ups' / 'pushup' -> 'pushup' (words singular, no spaces). The
    joined form is made singular too: "ups" is too short for the word rule."""
    return _singular("".join(_words(s)))


def pick_exercise(
    query: str,
    rows: Sequence[Exercise],
    fits: Callable[[Exercise], bool],
    strict: bool = False,
) -> Exercise:
    """The exercise a typed name means among library rows; `fits(row)` says whether the
    user's kit allows it (a fitting row wins over a closer name). Raises NotFoundError."""
    q = norm(query)
    c = compact(q)
    by_compact: dict[str, list[Exercise]] = {}
    for r in rows:
        by_compact.setdefault(compact(r.name), []).append(r)

    def first_fit(cands: Sequence[Exercise]) -> Exercise:
        return next((h for h in cands if fits(h)), cands[0])

    alias_by_compact = {compact(k): v for k, v in EXERCISE_ALIASES.items()}
    names = EXERCISE_ALIASES.get(q) or alias_by_compact.get(c)
    if names:
        hits = [by_compact[compact(n)][0] for n in names if compact(n) in by_compact]
        if hits:
            return first_fit(hits)
    if c in by_compact:
        return first_fit(by_compact[c])
    for r in rows:
        if any(compact(a) == c for a in r.aliases):
            return r
    if strict:
        raise NotFoundError(query)
    hits = [r for k, rs in by_compact.items() if c and c in k for r in rs]
    if not hits:  # one forgiving pass for typos ("pushpus", "pusups")
        close = difflib.get_close_matches(c, [*alias_by_compact, *by_compact], n=1, cutoff=0.8)
        if not close:
            raise NotFoundError(query)
        if close[0] in alias_by_compact:
            hits = [
                by_compact[compact(n)][0]
                for n in alias_by_compact[close[0]]
                if compact(n) in by_compact
            ]
            if hits:
                return first_fit(hits)
            raise NotFoundError(query)
        return first_fit(by_compact[close[0]])

    def rank(r: Exercise) -> tuple[int, int, int, int]:
        name = compact(r.name)
        return (
            0 if fits(r) else 1,
            0 if name.endswith(c) or name.startswith(c) else 1,
            0 if r.section in ("calisthenics", "gym") else 1,
            len(name),
        )

    return min(hits, key=rank)
