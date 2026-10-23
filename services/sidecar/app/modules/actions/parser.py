"""actions-parse-v1: text -> (action kind, params) by rules, no model.

The same grammar as the command bar (apps/desktop/src/lib/commands.ts); both are tested
against packages/shared/src/command-vectors.json so they agree on what a line means.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

PARSE_VERSION = "actions-parse-v1"
LB = 0.45359237
NUM = r"(\d+(?:[.,]\d+)?)"
WORD_NUMS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "half": 0.5}
MEAL_WORDS = ("breakfast", "lunch", "dinner", "snack")


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
    if word in MEAL_WORDS:
        return word
    if hour < 11:
        return "breakfast"
    if hour < 15:
        return "lunch"
    if hour < 21:
        return "dinner"
    return "snack"


_PREFIX = r"^(?:log |add |i did |did )?"
_SETS = re.compile(
    _PREFIX
    + r"(\d+) ?(?:[x×*]|sets? of) ?(\d+) ([a-z].*?)(?: (?:at|with) "
    + NUM
    + r" ?(kg|kgs|lb|lbs)?)?(?: ?(?:@|rpe) ?"
    + NUM
    + r")?$"
)
_WEIGHT_X_REPS = re.compile(
    _PREFIX + r"(.+?) " + NUM + r" ?(kg|kgs|lb|lbs)? ?[x×*] ?(\d+)(?: ?(?:@|rpe) ?" + NUM + r")?$"
)
_BODYWEIGHT = re.compile(
    _PREFIX + r"(.+?) (?:[x×*] ?(\d+)|(\d+) ?reps?)(?: ?(?:@|rpe) ?" + NUM + r")?$"
)
_HOLD = re.compile(_PREFIX + r"(.+?) (\d+) ?(?:s|sec|secs|seconds)(?: ?(?:@|rpe) ?" + NUM + r")?$")
_WEIGH = re.compile(
    r"^(?:log (?:my )?weight|i weigh|i weighed|weigh(?:ed|t|s)?|bw|body ?weight|scale)"
    r"(?: is| was| of)? " + NUM + r" ?(kg|kgs|lb|lbs)?$"
)
_MEAL = re.compile(r"^(?:(i ate|ate|eat|had|meal|breakfast|lunch|dinner|snack):? )(.+)$")
_ADD_FOOD = re.compile(r"^add " + NUM + r" (?:x |× )?([a-z].*)$")
_MEAL_FOR = re.compile(r"^(.+?) for (breakfast|lunch|dinner|snack)$")
_QTY = re.compile(r"^(\d+(?:[.,]\d+)?|a|an|one|two|three|four|five|half) (?:of )?(.+)$")
# v1.2 natural forms: "10 pushups", "log 3 pull-ups", "2 idli for breakfast" (count first;
# the service decides exercise vs food by looking both up) and "chicken breast 200g".
_COUNT_FIRST = re.compile(
    r"^(?:log |add |i did |did |i ate |ate |had )?(\d+) ([a-z][a-z' /-]*?)"
    r"(?: for (breakfast|lunch|dinner|snack))?$"
)
_GRAMS = re.compile(
    r"^(?:log |add |i ate |ate |had )?([a-z][a-z' /()-]*?) " + NUM + r" ?(?:g|gm|gms|grams)"
    r"(?: for (breakfast|lunch|dinner|snack))?$"
)
_FOLLOW = re.compile(
    r"^(?:switch me to|switch to|follow|start|put me on|enrol me in|enroll me in) "
    r"(?:the )?(.+?)(?: program| programme| plan| split)?$"
)


def parse(text: str, units: str = "metric", hour: int = 12) -> Parsed | None:
    t = re.sub(r"\s+", " ", text.strip()).lower().rstrip(".!")
    if not t:
        return None
    m = _SETS.match(t)
    if m:
        w = _kg(_n(m.group(4)), m.group(5), units) if m.group(4) else 0.0
        return Parsed("log_set", {"exercise": m.group(3), "reps": int(m.group(2)),
                                  "weight_kg": w, "sets": int(m.group(1)),
                                  "rpe": _n(m.group(6)) if m.group(6) else None})  # fmt: skip
    m = _WEIGH.match(t)
    if m:
        return Parsed(
            "log_weight", {"weight_kg": round(_kg(_n(m.group(1)), m.group(2), units, 1), 1)}
        )
    m = _WEIGHT_X_REPS.match(t)
    if m:
        return Parsed("log_set", {"exercise": m.group(1), "reps": int(m.group(4)),
                                  "weight_kg": _kg(_n(m.group(2)), m.group(3), units), "sets": 1,
                                  "rpe": _n(m.group(5)) if m.group(5) else None})  # fmt: skip
    m = _HOLD.match(t)
    if m:
        return Parsed("log_hold", {"exercise": m.group(1), "seconds": int(m.group(2)),
                                   "rpe": _n(m.group(3)) if m.group(3) else None})  # fmt: skip
    m = _BODYWEIGHT.match(t)
    if m:
        return Parsed("log_set", {"exercise": m.group(1), "reps": int(m.group(2) or m.group(3)),
                                  "weight_kg": 0.0, "sets": 1,
                                  "rpe": _n(m.group(4)) if m.group(4) else None})  # fmt: skip
    m = _MEAL.match(t)
    if m:
        word = m.group(1)
        rest = m.group(2)
        mf = _MEAL_FOR.match(rest)
        if mf:
            rest, word = mf.group(1), mf.group(2)
        portions = 1.0
        q = _QTY.match(rest)
        if q:
            raw = q.group(1)
            portions = WORD_NUMS[raw] if raw in WORD_NUMS else _n(raw)
            rest = q.group(2)
        return Parsed("log_meal", {"food": rest, "portions": portions,
                                   "meal_type": meal_type_for(word, hour)})  # fmt: skip
    m = _GRAMS.match(t)
    if m:
        return Parsed("log_food_grams", {"food": m.group(1), "grams": _n(m.group(2)),
                                         "meal_type": meal_type_for(m.group(3), hour)})  # fmt: skip
    m = _COUNT_FIRST.match(t)
    if m and not t.startswith("add "):
        if m.group(3):
            return Parsed("log_meal", {"food": m.group(2), "portions": float(m.group(1)),
                                       "meal_type": m.group(3)})  # fmt: skip
        return Parsed("log_count", {"name": m.group(2), "count": int(m.group(1)),
                                    "meal_type": meal_type_for(None, hour)})  # fmt: skip
    m = _ADD_FOOD.match(t)
    if m:
        return Parsed("log_meal", {"food": m.group(2), "portions": _n(m.group(1)),
                                   "meal_type": meal_type_for(None, hour)})  # fmt: skip
    m = _FOLLOW.match(t)
    if m:
        return Parsed("follow_program", {"program": m.group(1)})
    return None


# Parsed kinds that need a lookup before they become an action (see actions.service).
AMBIGUOUS_KINDS = frozenset({"log_count", "log_food_grams"})
