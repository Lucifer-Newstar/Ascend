"""actions-parse-v2: text -> (action kind, params) by rules, no model.

The grammar the trainer chat reads log lines with. packages/shared/src/command-vectors.json
holds the lines both this parser and the app's tests agree on. v1.3 adds the everyday
forms people actually type: "pullups 7", "10 pushups done", "plank 1:30", "I'm 42.5 kg
today", number words, a few common typos and Tanglish/Hinglish fillers ("da", "machan",
"pannen", "kiye"), portion words (katori, cup, plate) and meals with several items
("2 idli and sambar for breakfast").
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

PARSE_VERSION = "actions-parse-v2"
LB = 0.45359237
NUM = r"(\d+(?:[.,]\d+)?)"
WORD_NUMS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "half": 0.5}
MEAL_WORDS = ("breakfast", "lunch", "dinner", "snack")

# Number words people type instead of digits ("ten pushups", "twenty squats").
NUMBER_WORDS: dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "twenty five": 25,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
}
# Words that carry no meaning in a log line: chat fillers (English, Tamil and Hindi typed
# in Latin letters) and time words. Removed only when the line does not parse as typed.
FILLERS = frozenset(
    {
        "bro",
        "da",
        "dei",
        "machan",
        "macha",
        "machi",
        "dude",
        "man",
        "bhai",
        "yaar",
        "pa",
        "pannen",
        "panniten",
        "pannitten",
        "panninen",
        "adichen",
        "senjen",
        "kiye",
        "kiya",
        "kar",
        "liya",
        "liye",
        "hai",
        "aaj",
        "inniki",
        "innaiku",
        "today",
        "todays",
        "just",
        "now",
        "done",
        "finished",
        "completed",
        "complete",
        "total",
        "also",
        "ok",
        "okay",
        "so",
        "yay",
        "lol",
        "guys",
        "sir",
        "boss",
        "anna",
        "i",
        "have",
        "has",
        "had",
        "did",
        "do",
        "got",
        "my",
        "this",
        "morning",
        "evening",
        "tonight",
        "in",
        "the",
        "gym",
    }
)
# Portion words: "1 katori dal", "half plate biryani", "2 cups of tea".
PORTION_WORDS = (
    r"(?:katoris?|cups?|bowls?|plates?|glass(?:es)?|pieces?|pcs|servings?|nos|slices?|"
    r"scoops?|spoons?|tbsp|tsp)"
)
# Exercises nobody loads with a weight, so "pushups 8x10" is 8 sets of 10.
_BODYWEIGHT_WORDS = re.compile(
    r"push|pull|chin|dip|sit ?up|crunch|plank|lunge|burpee|jump|squat|pike|muscle ?up|"
    r"leg raise|hang|row|bridge"
)


@dataclass(frozen=True)
class Parsed:
    kind: str
    params: dict[str, Any]


def _n(s: str) -> float:
    return float(s.replace(",", "."))


def _kg(value: float, unit: str | None, units: str, places: int = 2) -> float:
    u = (unit or ("lb" if units == "imperial" else "kg")).lower()
    return round(value * LB, places) if u.startswith(("lb", "pound")) else value


def meal_type_for(word: str | None, hour: int) -> str:
    """The meal a line is for: the word typed, else the time of day (v1.3: the afternoon
    is a snack, not dinner)."""
    if word in MEAL_WORDS:
        return word
    if hour < 11:
        return "breakfast"
    if hour < 15:
        return "lunch"
    if hour < 18:
        return "snack"
    if hour < 22:
        return "dinner"
    return "snack"


_PREFIX = r"^(?:log |add |i did |did |i do |done )?"
_RPE = r"(?: ?(?:@|rpe) ?" + NUM + r")?"
_UNIT = r" ?(kg|kgs|kilos?|lb|lbs|pounds?)"
_SETS = re.compile(
    _PREFIX
    + r"(\d+) ?(?:[x×*]|sets? of|sets?) ?(\d+) (?:reps? )?(?:of )?([a-z].*?)(?: (?:at|with) "
    + NUM
    + r"(?:"
    + _UNIT
    + r")?)?"
    + _RPE
    + r"$"
)
# "3 sets 10 reps pushups", "3 set 10 rep pushup"
_SETS_REPS_WORDS = re.compile(_PREFIX + r"(\d+) ?sets? (?:of )?(\d+) ?reps? (?:of )?([a-z].*?)$")
# "pushups 3 sets of 10", "pushups 3 sets 10 reps"
_NAME_SETS_WORDS = re.compile(
    _PREFIX + r"([a-z][a-z' -]*?) (\d+) ?sets? (?:of |x )?(\d+)(?: ?reps?)?$"
)
_WEIGHT_X_REPS = re.compile(
    _PREFIX + r"(.+?) " + NUM + r"(?:" + _UNIT + r")? ?[x×*] ?(\d+)" + _RPE + r"$"
)
# "bench 20kg 8 reps", "bench press 20kg for 8 reps"
_NAME_KG_REPS = re.compile(
    _PREFIX + r"([a-z][a-z' -]*?) " + NUM + _UNIT + r" (?:for |x )?(\d+) ?reps?" + _RPE + r"$"
)
# "8 reps bench 20kg", "10kg db curl 10 reps"
_REPS_NAME_KG = re.compile(_PREFIX + r"(\d+) ?reps? (?:of )?([a-z][a-z' -]*?) " + NUM + _UNIT + "$")
_KG_NAME_REPS = re.compile(_PREFIX + NUM + _UNIT + r" ([a-z][a-z' -]*?) (\d+) ?reps?$")
_BODYWEIGHT = re.compile(_PREFIX + r"(.+?) (?:[x×*] ?(\d+)|(\d+) ?reps?)" + _RPE + r"$")
_SECS = r"(?:s|sec|secs|second|seconds)"
_MINS = r"(?:m|min|mins|minute|minutes)"
# A duration: "60s", "1 min", "1.5 min", "1:30", "1 min 30 sec", "a minute".
_DUR = (
    r"(?:(\d+):([0-5]\d)|(\d+(?:\.\d+)?) ?" + _MINS + r"(?: (?:and )?(\d+) ?" + _SECS + r")?"
    r"|(\d+) ?" + _SECS + r"|an? " + r"(?:minute|min))"
)
_HOLD = re.compile(
    r"^(?:log |add |held |hold |did |i held |i did )?(?:a )?([a-z][a-z' -]*?) (?:hold )?"
    r"(?:for )?" + _DUR + _RPE + r"$"
)
_HOLD_FIRST = re.compile(
    r"^(?:log |add |held |did |i held |i did )?(?:a )?" + _DUR + r" (?:of )?([a-z][a-z' -]*?)"
    r"(?: hold)?$"
)
# "3x30s plank", "plank 3 x 30 sec"
_HOLD_SETS = re.compile(r"^(?:log |did )?(\d+) ?[x×*] ?(\d+) ?" + _SECS + r" ([a-z][a-z' -]*?)$")
_NAME_HOLD_SETS = re.compile(
    r"^(?:log |did )?([a-z][a-z' -]*?) (\d+) ?[x×*] ?(\d+) ?" + _SECS + r"$"
)
_WEIGH = re.compile(
    r"^(?:log (?:my )?weight|i weigh|i weighed|weigh(?:ed|t|s)?|bw|body ?weight|scale"
    r"|my (?:body ?)?weight(?: today)?|today'?s weight|i'?m|i am|am)"
    r"(?: is| was| of| now| today)?:? "
    + NUM
    + r"(?:"
    + _UNIT
    + r")?(?: today| now| this morning)?$"
)
_BARE_KG = re.compile(r"^" + NUM + r" ?(kg|kgs|lb|lbs)(?: today| now)?$")
_MEAL = re.compile(
    r"^(?:(i ate|ate|eat|had|i had|meal|breakfast|lunch|dinner|snacks?|for breakfast|"
    r"for lunch|for dinner):? )(.+)$"
)
_ADD_FOOD = re.compile(r"^add " + NUM + r" (?:x |× )?([a-z].*)$")
_MEAL_FOR = re.compile(
    r"^(.+?) (?:for|as|at) (?:my )?(breakfast|lunch|dinner|snacks?|tiffin)(?: today)?$"
)
_QTY = re.compile(
    r"^(\d+(?:[.,]\d+)?|a|an|one|two|three|four|five|half) (?:"
    + PORTION_WORDS
    + r" )?(?:of )?(.+)$"
)
_COUNT_FIRST = re.compile(
    r"^(?:log |add |i did |did |i ate |ate |had )?(\d+) ([a-z][a-z' /-]*?)"
    r"(?: for (breakfast|lunch|dinner|snack))?$"
)
_QTY_PORTION = re.compile(
    r"^(?:had |ate |i ate |i had )?(\d+[.,]\d+|half|\d+(?= ?" + PORTION_WORDS + r"))"
    r" ?(?:a )?(?:" + PORTION_WORDS + r" )?(?:of )?([a-z][a-z' /()-]*?)"
    r"(?: for (breakfast|lunch|dinner|snack))?$"
)
# "pullups 7", "dips 12", "ring pull ups 5"
_NAME_COUNT = re.compile(r"^(?:log |did )?([a-z][a-z' -]*?) (\d+)$")
_GRAMS = re.compile(
    r"^(?:log |add |i ate |ate |had )?([a-z][a-z' /()-]*?) " + NUM + r" ?(?:g|gm|gms|grams?|ml)"
    r"(?: for (breakfast|lunch|dinner|snack))?$"
)
_GRAMS_FIRST = re.compile(
    r"^(?:log |add |i ate |ate |had )?"
    + NUM
    + r" ?(?:g|gm|gms|grams?|ml) (?:of )?([a-z][a-z' /()-]*?)"
    r"(?: for (breakfast|lunch|dinner|snack))?$"
)
_FOLLOW = re.compile(
    r"^(?:switch me to|switch to|follow|start|put me on|enrol me in|enroll me in) "
    r"(?:the )?(.+?)(?: program| programme| plan| split)?$"
)
# Several items in one line: "idli and sambar", "dosa, chutney", "idli + vada", "dosa with
# chutney". A number inside a food name ("Omelette (2 eggs)") is never a separator.
_SPLIT = re.compile(r"\s*(?:,|\+|&| and | with | n | aur | um )\s*")
_EMOJI = re.compile(r"[^\x00-\x7f]+")


def _clean(text: str) -> str:
    t = text.strip().lower().replace("\u2019", "'").replace("\u00d7", "x")
    t = _EMOJI.sub(" ", t)
    t = re.sub(r"\s+", " ", t).strip().rstrip(".!? ").strip()
    return re.sub(r"\b([a-z]{4,}) s\b", r"\1s", t)  # "pushup s" -> "pushups"


def _number_words(t: str) -> str:
    for word, n in sorted(NUMBER_WORDS.items(), key=lambda kv: -len(kv[0])):
        t = re.sub(rf"(?<![a-z]){word}(?![a-z])", str(n), t)
    return t


def _defiller(t: str) -> str:
    """Drop chat fillers and glue typo-split words ("pushup s")."""
    words = [w for w in t.split(" ") if w not in FILLERS]
    return " ".join(words).strip()


def _seconds(m: re.Match[str], first: int) -> int | None:
    g = m.groups()[first : first + 5]
    mm_ss_m, mm_ss_s, mins, extra_s, secs = g
    if mm_ss_m is not None:
        return int(mm_ss_m) * 60 + int(mm_ss_s)
    if mins is not None:
        return round(float(mins) * 60) + (int(extra_s) if extra_s else 0)
    if secs is not None:
        return int(secs)
    return 60  # "a minute"


def _set(name: str, reps: int, kg: float = 0.0, sets: int = 1, rpe: str | None = None) -> Parsed:
    return Parsed(
        "log_set",
        {
            "exercise": name.strip(),
            "reps": reps,
            "weight_kg": kg,
            "sets": sets,
            "rpe": _n(rpe) if rpe else None,
        },
    )


def _single(t: str, units: str, hour: int, meal_word: str | None = None) -> Parsed | None:
    """One log line (no item separators), with filler words dropped from the name."""
    hit = _single_raw(t, units, hour, meal_word)
    if hit is None:
        return None
    for key in ("exercise", "name"):
        name = hit.params.get(key)
        if isinstance(name, str):
            kept = " ".join(w for w in name.split(" ") if w not in FILLERS)
            if not kept:
                return None
            portion = re.match(r"^(?:half )?" + PORTION_WORDS + r" (?:of )?(.+)$", kept)
            if key == "name" and portion:  # "1 katori dal": a food, never a set
                return Parsed(
                    "log_meal",
                    {
                        "food": portion.group(1),
                        "portions": float(hit.params["count"]),
                        "meal_type": meal_type_for(meal_word, hour),
                    },
                )
            hit.params[key] = kept
    food = hit.params.get("food")
    if isinstance(food, str):
        hit.params["food"] = re.sub(r"^" + PORTION_WORDS + r" (?:of )?", "", food)
    return hit


def _single_raw(t: str, units: str, hour: int, meal_word: str | None = None) -> Parsed | None:
    m = _SETS.match(t)
    if m:
        w = _kg(_n(m.group(4)), m.group(5), units) if m.group(4) else 0.0
        return _set(m.group(3), int(m.group(2)), w, int(m.group(1)), m.group(6))
    m = _SETS_REPS_WORDS.match(t)
    if m:
        return _set(m.group(3), int(m.group(2)), 0.0, int(m.group(1)))
    m = _NAME_SETS_WORDS.match(t)
    if m:
        return _set(m.group(1), int(m.group(3)), 0.0, int(m.group(2)))
    m = _WEIGH.match(t) or _BARE_KG.match(t)
    if m:
        return Parsed(
            "log_weight", {"weight_kg": round(_kg(_n(m.group(1)), m.group(2), units, 1), 1)}
        )
    m = _HOLD_SETS.match(t)
    if m:
        return Parsed(
            "log_hold",
            {
                "exercise": m.group(3),
                "seconds": int(m.group(2)),
                "sets": int(m.group(1)),
                "rpe": None,
            },
        )
    m = _NAME_HOLD_SETS.match(t)
    if m:
        return Parsed(
            "log_hold",
            {
                "exercise": m.group(1),
                "seconds": int(m.group(3)),
                "sets": int(m.group(2)),
                "rpe": None,
            },
        )
    m = _NAME_KG_REPS.match(t)
    if m:
        return _set(
            m.group(1), int(m.group(4)), _kg(_n(m.group(2)), m.group(3), units), rpe=m.group(5)
        )
    m = _REPS_NAME_KG.match(t)
    if m:
        return _set(m.group(2), int(m.group(1)), _kg(_n(m.group(3)), m.group(4), units))
    m = _KG_NAME_REPS.match(t)
    if m:
        return _set(m.group(3), int(m.group(4)), _kg(_n(m.group(1)), m.group(2), units))
    m = _WEIGHT_X_REPS.match(t)
    if m:
        name, a, unit, b = m.group(1), _n(m.group(2)), m.group(3), int(m.group(4))
        # v1.3: "pushups 3x10" with no unit is 3 sets of 10, not 3 kg (a weighted lift
        # like "bench 80x5" stays a load; a small first number reads as sets).
        if (
            unit is None
            and a == int(a)
            and (a <= 5 or (a <= 10 and _BODYWEIGHT_WORDS.search(name)))
        ):
            return _set(name, b, 0.0, int(a), m.group(5))
        return _set(name, b, _kg(a, unit, units), 1, m.group(5))
    m = _HOLD.match(t)
    if m:
        secs = _seconds(m, 1)
        return Parsed("log_hold", {"exercise": m.group(1), "seconds": secs, "rpe": None})
    m = _HOLD_FIRST.match(t)
    if m:
        secs = _seconds(m, 0)
        return Parsed("log_hold", {"exercise": m.group(6), "seconds": secs, "rpe": None})
    m = _BODYWEIGHT.match(t)
    if m:
        return _set(m.group(1), int(m.group(2) or m.group(3)), rpe=m.group(4))
    m = _MEAL.match(t)
    if m:
        word = m.group(1).replace("for ", "")
        word = "snack" if word.startswith("snack") else word
        return _food_item(m.group(2), units, hour, word if word in MEAL_WORDS else meal_word)
    m = _GRAMS.match(t)
    if m:
        return Parsed(
            "log_food_grams",
            {
                "food": m.group(1),
                "grams": _n(m.group(2)),
                "meal_type": meal_type_for(m.group(3) or meal_word, hour),
            },
        )
    m = _GRAMS_FIRST.match(t)
    if m:
        return Parsed(
            "log_food_grams",
            {
                "food": m.group(2),
                "grams": _n(m.group(1)),
                "meal_type": meal_type_for(m.group(3) or meal_word, hour),
            },
        )
    m = _MEAL_FOR.match(t)
    if m and not re.match(r"^\d", t) and not _QUESTION.search(t):
        return _food_item(t, units, hour, meal_word)
    m = _QTY_PORTION.match(t)
    if m:  # "half plate biryani", "1.5 cup curd rice", "2 glass milk": food, never a set
        raw = m.group(1)
        portions = WORD_NUMS[raw] if raw in WORD_NUMS else _n(raw)
        return Parsed(
            "log_meal",
            {
                "food": m.group(2),
                "portions": portions,
                "meal_type": meal_type_for(m.group(3) or meal_word, hour),
            },
        )
    m = _COUNT_FIRST.match(t)
    if m and not t.startswith("add "):
        if m.group(3) or meal_word:
            return Parsed(
                "log_meal",
                {
                    "food": m.group(2),
                    "portions": float(m.group(1)),
                    "meal_type": m.group(3) or meal_word,
                },
            )
        return Parsed(
            "log_count",
            {"name": m.group(2), "count": int(m.group(1)), "meal_type": meal_type_for(None, hour)},
        )
    m = _ADD_FOOD.match(t)
    if m:
        return Parsed(
            "log_meal",
            {
                "food": m.group(2),
                "portions": _n(m.group(1)),
                "meal_type": meal_type_for(meal_word, hour),
            },
        )
    m = _FOLLOW.match(t)
    if m:
        return Parsed("follow_program", {"program": m.group(1)})
    m = _NAME_COUNT.match(t)
    if m and not _WORDY.search(m.group(1)):
        return Parsed(
            "log_count",
            {
                "name": m.group(1),
                "count": int(m.group(2)),
                "meal_type": meal_type_for(meal_word, hour),
            },
        )
    return None


# Words that make a phrase a sentence, not a dish ("small woman and want to get bigger").
_STOP = re.compile(
    r"\b(my|me|i|to|is|are|was|by|be|can|want|get|got|what|how|why|when|which|as|of|on|up|"
    r"it|this|that|do|does|vs|or|not|very|too|so|pros|cons)\b"
)
_QUESTION = re.compile(
    r"\b(what|how|should|can|could|which|suggest|recommend|give|plan|ideas?|best|good|why|"
    r"make|need|want|options?)\b"
)
# A "name N" line is a log only when the name is a name, not a sentence ("set my age 21").
_WORDY = re.compile(
    r"\b(my|set|change|make|what|how|is|are|to|age|height|target|goal|day|days|week|weeks|"
    r"times?|minutes?|level|rank|streak|xp)\b"
)


def _food_item(rest: str, units: str, hour: int, word: str | None) -> Parsed:
    mf = _MEAL_FOR.match(rest)
    if mf:
        rest, word = mf.group(1), mf.group(2)
    word = _meal_word(word)
    g = re.match(r"^" + NUM + r" ?(?:g|gm|gms|grams?) (?:of )?(.+)$", rest)
    if g:  # "ate 200 grams chicken"
        return Parsed(
            "log_food_grams",
            {"food": g.group(2), "grams": _n(g.group(1)), "meal_type": meal_type_for(word, hour)},
        )
    portions = 1.0
    q = _QTY.match(rest)
    if q:
        raw = q.group(1)
        portions = WORD_NUMS[raw] if raw in WORD_NUMS else _n(raw)
        rest = q.group(2)
    if rest.startswith("half "):  # "a half plate", "half katori"
        portions, rest = portions * 0.5, rest[5:]
    rest = re.sub(r"^" + PORTION_WORDS + r" (?:of )?", "", rest)
    return Parsed(
        "log_meal",
        {"food": rest.strip(), "portions": portions, "meal_type": meal_type_for(word, hour)},
    )


def _meal_word(word: str | None) -> str | None:
    if word is None:
        return None
    if word.startswith("snack"):
        return "snack"
    return {"tiffin": "breakfast"}.get(word, word)


def parse(text: str, units: str = "metric", hour: int = 12) -> Parsed | None:
    """One action for a line, or None. Lines with several items (meals or sets) come back
    as a log_meal with `items`, or a log_items the service resolves item by item."""
    t = _clean(text)
    if not t or "?" in text:  # a question is never a log line
        return None
    hit = _single(t, units, hour)
    if hit is not None and not _has_separator(hit):
        return hit
    multi = _parse_multi(t, units, hour)
    if multi is not None:
        return multi
    if hit is not None:
        return hit
    # Second pass: number words, chat fillers and typo-split words removed.
    t2 = _defiller(_number_words(t))
    if t2 and t2 != t:
        hit = _single(t2, units, hour)
        if hit is not None:
            return hit
        return _parse_multi(t2, units, hour)
    return None


def _has_separator(p: Parsed) -> bool:
    name = str(p.params.get("food") or p.params.get("exercise") or p.params.get("name") or "")
    return bool(_SPLIT.search(f" {name} ".replace(" ", "  ")) and _SPLIT.split(name)[1:])


_LEAD = re.compile(
    r"^(?:(?:i )?(?:ate|had|eat)|for (breakfast|lunch|dinner|snacks?|tiffin)|"
    r"(breakfast|lunch|dinner|snacks?|tiffin))[: ]+"
)
_TRAIL = re.compile(r" (?:for|as|at) (?:my )?(breakfast|lunch|dinner|snacks?|tiffin)(?: today)?$")


def _parse_multi(t: str, units: str, hour: int) -> Parsed | None:
    """'2 idli and sambar for breakfast' -> one meal with two items; '10 pushups, 5 pullups'
    -> log_items (resolved as sets)."""
    word: str | None = None
    body = t
    lead = _LEAD.match(body)
    if lead:
        word = lead.group(1) or lead.group(2)
        body = body[lead.end() :]
    trail = _TRAIL.search(body)
    if trail:
        word = trail.group(1)
        body = body[: trail.start()]
    word = _meal_word(word)
    parts = [p for p in _SPLIT.split(body) if p.strip()]
    if len(parts) < 2 or len(parts) > 8:
        return None
    items: list[dict[str, Any]] = []
    foods = 0
    sets = 0
    for part in parts:
        p = part.strip()
        hit = _single(p, units, hour, word) or _single(
            _defiller(_number_words(p)), units, hour, word
        )
        if hit is None or hit.kind == "follow_program" or hit.kind == "log_weight":
            # a bare name ("sambar"): a food item of one portion
            if not re.fullmatch(r"[a-z][a-z' ()-]*", p) or len(p.split()) > 3 or _STOP.search(p):
                return None
            items.append({"name": p, "count": 1.0, "food_only": True, "bare": True})
            foods += 1
            continue
        if hit.kind == "log_meal":
            items.append(
                {
                    "name": hit.params["food"],
                    "count": float(hit.params["portions"]),
                    "food_only": True,
                }
            )
            foods += 1
        elif hit.kind == "log_food_grams":
            items.append(
                {"name": hit.params["food"], "grams": float(hit.params["grams"]), "food_only": True}
            )
            foods += 1
        elif hit.kind == "log_count":
            items.append({"name": hit.params["name"], "count": float(hit.params["count"])})
        elif hit.kind == "log_set":
            items.append(
                {
                    "name": hit.params["exercise"],
                    "count": float(hit.params["reps"]),
                    "sets": int(hit.params["sets"]),
                    "weight_kg": float(hit.params["weight_kg"]),
                }
            )
            sets += 1
        else:
            return None
    if foods and sets:
        return None
    return Parsed(
        "log_items",
        {"items": items, "meal_type": meal_type_for(word, hour), "meal_word": word is not None},
    )


# Parsed kinds that need a lookup before they become an action (see actions.service).
AMBIGUOUS_KINDS = frozenset({"log_count", "log_food_grams", "log_items"})
