"""Output validators for model replies (docs/ai/coach-llm.md section 5.2, ADR-0011).

Pure functions, no I/O. The coach runs them on every model reply before the user
sees it; the first failure replaces the reply with the rules text.

* V3 number fidelity: every number in the reply must come from the facts block or
  the user's own message (exactly, or rounded to fewer significant digits within 2%),
  with the same unit when a unit is attached.
* V4 banned phrases: diagnosis words, medicine or dose patterns, and claims that the
  plan was changed (only the planner changes plans, after the user approves).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

VALIDATOR_VERSION = "validate-1.0.0"

# Units we can recognise right after a number. Synonyms map to one canonical unit.
UNITS: dict[str, str] = {
    "kg": "kg",
    "kgs": "kg",
    "kilo": "kg",
    "kilos": "kg",
    "lb": "lb",
    "lbs": "lb",
    "kcal": "kcal",
    "cal": "kcal",
    "calories": "kcal",
    "g": "g",
    "gram": "g",
    "grams": "g",
    "km": "km",
    "cm": "cm",
    "min": "min",
    "mins": "min",
    "minutes": "min",
    "%": "%",
    "percent": "%",
    "sets": "sets",
    "set": "sets",
    "reps": "reps",
    "rep": "reps",
    "days": "days",
    "day": "days",
    "weeks": "weeks",
    "week": "weeks",
    "xp": "xp",
}

WORDS: dict[str, int] = {
    "zero": 0,
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
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
    "hundred": 100,
}
# "one thing", "two options": normal phrasing, allowed as words (not as digits).
ALWAYS_ALLOWED_WORDS = {"one", "two"}

_NUMBER = re.compile(
    r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?(?:\s*(%|[a-zA-Z]+))?",
)
_WORD = re.compile(r"\b(" + "|".join(WORDS) + r")\b(?:\s+([a-zA-Z]+|%))?", re.IGNORECASE)


@dataclass(frozen=True)
class Num:
    value: float
    raw: str
    unit: str | None = None
    word: bool = False


def _unit(token: str | None) -> str | None:
    if not token:
        return None
    return UNITS.get(token.lower())


def extract_numbers(text: str) -> list[Num]:
    """Numbers in reading order: digit groups (2,650 / 88.7 / both sides of 3/10) and
    English number words. The unit is the recognised word right after the number."""
    found: list[tuple[int, Num]] = []
    for m in _NUMBER.finditer(text):
        whole, frac, after = m.group(1), m.group(2), m.group(3)
        value = float(whole.replace(",", "") + (f".{frac}" if frac else ""))
        raw = whole + (f".{frac}" if frac else "")
        found.append((m.start(), Num(value, raw, _unit(after))))
    for m in _WORD.finditer(text):
        word = m.group(1).lower()
        found.append((m.start(), Num(float(WORDS[word]), word, _unit(m.group(2)), word=True)))
    return [n for _, n in sorted(found, key=lambda t: t[0])]


def _sig_digits(raw: str) -> int:
    digits = raw.replace(",", "").replace(".", "").lstrip("0")
    return len(digits.rstrip("0")) or 1


def _matches(n: Num, allowed: Num) -> bool:
    if n.unit and allowed.unit and n.unit != allowed.unit:
        return False
    if math.isclose(n.value, allowed.value, rel_tol=0, abs_tol=1e-9):
        return True
    # A rounded form of an allowed value: fewer significant digits and within 2%.
    if n.word or allowed.value == 0:
        return False
    fewer = _sig_digits(n.raw) < _sig_digits(allowed.raw)
    return fewer and abs(n.value - allowed.value) / abs(allowed.value) <= 0.02


@dataclass
class NumberCheck:
    ok: bool
    offending: list[str] = field(default_factory=list)


def check_numbers(reply: str, *sources: str) -> NumberCheck:
    """V3: each number in `reply` must be allowed by one of `sources` (facts, question)."""
    allowed = [n for s in sources for n in extract_numbers(s)]
    bad: list[str] = []
    for n in extract_numbers(reply):
        if n.word and n.raw in ALWAYS_ALLOWED_WORDS:
            continue
        if not any(_matches(n, a) for a in allowed):
            bad.append(f"{n.raw} {n.unit}".strip() if n.unit else n.raw)
    return NumberCheck(ok=not bad, offending=bad)
