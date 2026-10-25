"""Free-chat pickup (planbuilder-v1): plain sentences -> plan facts, rules only.

The main path for the plan builder (Navin, 2026-10-25): people mention things in normal
chat and the trainer picks them up. Each rule needs a statement about *you* ("I have",
"I want to", "I trained", "I can't eat"), so a question like "how do I use a punching bag?"
is never taken as a fact. Works with the AI off; numbers always come from the text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.modules.planbuilder.facts import PlanFacts

_WORD_NUM = {
    "a": 1, "an": 1, "one": 1, "single": 1, "two": 2, "pair of": 2, "a pair of": 2, "both": 2,
    "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "ten": 10,
}  # fmt: skip
_NUM = (
    r"(\d+(?:\.\d+)?|a pair of|pair of|an|a|one|single|two|both|three|four|five|six|seven|"
    r"eight|ten)"
)

_QUESTION = re.compile(r"\?\s*$|^(how|what|which|why|should|can|could|is|are|do|does|will)\b")
_HAVE = re.compile(r"\b(i(?:'ve| have)?|i've got|i got|got|own|bought|have|there'?s|with)\b")

# --- kit ------------------------------------------------------------------------------
_KIT = (
    ("punching_bag", re.compile(r"\b(punch(?:ing)?\s?bag|heavy\s?bag|boxing\s?bag|kick\s?bag)\b")),
    ("gripper", re.compile(r"\b(hand\s?)?grippers?\b|\bgrip\s?trainer\b")),
    ("hand_wraps", re.compile(r"\b(hand\s?)?wraps\b")),
    ("gloves", re.compile(r"\b(boxing\s|mma\s|bag\s)?gloves\b")),
    ("jump_rope", re.compile(r"\b(jump|skipping)\s?ropes?\b")),
)
_BASE_KIT = (
    ("rings", re.compile(r"\b(gymnastic\s)?rings\b")),
    ("pullup_bar", re.compile(r"\b(pull\s?-?\s?up|chin\s?-?\s?up)\s?bar\b")),
    ("bench", re.compile(r"\b(workout\s|weight\s|flat\s)?bench\b")),
)
_DUMBBELL = re.compile(r"\bdumb\s?-?bells?\b")
_COUNT_X_KG = re.compile(r"\b(\d+)\s*[x×]\s*(\d+(?:\.\d+)?)\s*kg\b")
_N_KG = re.compile(rf"(?:\b{_NUM}\s+)?(\d+(?:\.\d+)?)\s*-?\s*kgs?\b")

# --- sports ---------------------------------------------------------------------------
_SPORTS = (
    ("muay_thai", re.compile(r"\bmuay\s?thai\b")),
    ("kickboxing", re.compile(r"\bkick\s?-?\s?boxing\b|\bkicks?\b")),
    ("boxing", re.compile(r"(?<!kick)(?<!kick )\bboxing\b")),
    ("taekwondo", re.compile(r"\btae\s?kwon\s?-?do\b")),
    ("karate", re.compile(r"\bkarate\b")),
    ("mma", re.compile(r"\bmma\b|\bmixed martial arts\b")),
)
_SPORT_VERB = re.compile(
    r"\b(want|wanna|would like|like|love|trained|train|training|did|do|doing|practi[sc]e|"
    r"learn|learning|into|used to)\b"
)
_YEARS_AGO = re.compile(rf"\b{_NUM}\s*(?:years?|yrs?)\s*(?:ago|back)\b")
_LAST_YEAR = re.compile(r"\blast year\b")

# --- goals, weight, days --------------------------------------------------------------
_GOAL = (
    ("gain_weight", re.compile(r"\b(gain|put on|increase)\s+(some\s+)?weight\b|\bbulk(ing)?\b")),
    ("gain_muscle", re.compile(r"\b(build|gain|grow)\s+(some\s+)?muscles?\b")),
    ("lose_fat", re.compile(r"\b(lose|burn|drop)\s+(some\s+)?(fat|weight)\b|\bcut(ting)?\b")),
    ("strength", re.compile(r"\b(get|be(?:come)?)\s+stronger\b")),
)
_WANT = re.compile(r"\b(i\s+)?(want|wanna|would like|need|trying|try|plan|hope|goal|aim)\b")
_TARGET = re.compile(
    r"\b(?:reach|get to|hit|be at|weigh|target(?: weight)?(?: is| of)?|gain to|go to|up to|"
    r"goal(?: is| of)?)\s*(?:about\s+|around\s+)?(\d{2,3}(?:\.\d)?)\s*kgs?\b"
)
_FROM = re.compile(
    r"\bfrom\s*(\d{2,3}(?:\.\d)?)\s*kgs?\b|"
    r"\b(?:i\s*(?:am|'m)|i weigh)\s*(\d{2,3}(?:\.\d)?)\s*kgs?\b"
)
_IN_WEEKS = re.compile(rf"\bin\s+{_NUM}\s+(weeks?|months?)\b")
_DAYS = re.compile(r"\b([2-6])\s*(?:days?|times?)\s*(?:a|per|each)\s*week\b")
_MINUTES = re.compile(
    r"\b(\d{2,3})\s*(?:min|mins|minutes)\s*(?:a|per|each)?\s*(?:session|workout|day)?\b"
)
_HOUR = re.compile(r"\b(an|one)\s+hour\s+(?:a|per|each)\s+(?:session|workout|day)\b")

# --- appetite -------------------------------------------------------------------------
_CANT_EAT = re.compile(
    r"\b(can'?t|cannot|can not|don'?t|do not|unable to)\s+eat\s+(much|a lot|more|big|enough)|"
    r"\b(no|small|low|poor)\s+appetite\b|\bnot (very )?hungry\b|\bget full (fast|quickly)\b"
)
_CAN_DRINK = re.compile(r"\b(can|could|i)\s+drink\b|\bshakes? (are|is) (fine|ok|easy)\b")


def _num(token: str) -> float:
    t = token.strip()
    return float(t) if t[0].isdigit() else float(_WORD_NUM.get(t, 1))


@dataclass
class Picked:
    """What one message said: the facts, plus base kit for the profile checklist."""

    facts: PlanFacts
    equipment_add: list[str] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return self.facts.is_empty() and not self.equipment_add

    @property
    def specific(self) -> bool:
        """Something only the plan builder can hold. "I have a bench", "train 4 days a week"
        or "I want to reach 50 kg" alone stay the v1.3 edits; they ride along otherwise."""
        f = self.facts
        return bool(
            f.dumbbells_kg or f.kit or f.sports or f.sports_years_ago is not None
            or f.liquid_calories
        )  # fmt: skip


def _dumbbells(t: str) -> list[float]:
    if not _DUMBBELL.search(t):
        return []
    out: list[float] = []
    for n, kg in _COUNT_X_KG.findall(t):
        out += [float(kg)] * min(int(n), 4)
    if out:
        return out
    for count, kg in _N_KG.findall(t):
        w = float(kg)
        if 0.5 <= w <= 60:
            out += [w] * min(int(_num(count)) if count else 1, 4)
    return out[:8]


def extract(text: str) -> Picked | None:
    t = " ".join(text.lower().replace("’", "'").split())
    if not t or _QUESTION.search(t):
        return None
    data: dict[str, object] = {}
    equipment: list[str] = []
    has = bool(_HAVE.search(t))

    if has:
        dbs = _dumbbells(t)
        if dbs:
            data["dumbbells_kg"] = dbs
            equipment.append("dumbbells")
        kit = [k for k, rx in _KIT if rx.search(t)]
        if kit:
            data["kit"] = kit
        equipment += [k for k, rx in _BASE_KIT if rx.search(t)]

    if _SPORT_VERB.search(t) or _YEARS_AGO.search(t):
        sports = [s for s, rx in _SPORTS if rx.search(t)]
        if (
            "muay_thai" in sports
            and "kickboxing" in sports
            and not re.search(r"kick\s?-?\s?boxing", t)
        ):
            sports.remove("kickboxing")  # "muay thai kicks" is one sport
        if sports:
            data["sports"] = sports
        m = _YEARS_AGO.search(t)
        if m and (sports or re.search(r"\b(martial|fight|spar|kicks?|punch)", t)):
            data["sports_years_ago"] = int(_num(m.group(1)))
        elif sports and _LAST_YEAR.search(t):
            data["sports_years_ago"] = 1

    if _WANT.search(t):
        for g, rx in _GOAL:
            if rx.search(t):
                data["goal"] = g
                break
        m = _TARGET.search(t)
        if m:
            data["target_weight_kg"] = float(m.group(1))
            data.setdefault("goal", None)
    m = _FROM.search(t)
    if m and "target_weight_kg" in data:
        data["weight_kg"] = float(m.group(1) or m.group(2))
    m = _IN_WEEKS.search(t)
    if m and "target_weight_kg" in data:
        n = _num(m.group(1))
        data["weeks"] = int(n * 4 if m.group(2).startswith("month") else n)

    m = _DAYS.search(t)
    if m and ("train" in t or "work out" in t or "workout" in t or "gym" in t):
        data["days_per_week"] = int(m.group(1))
    m = _MINUTES.search(t) if ("session" in t or "workout" in t or "train" in t) else None
    if m and 10 <= int(m.group(1)) <= 120:
        data["session_minutes"] = int(m.group(1))
    elif _HOUR.search(t):
        data["session_minutes"] = 60

    if _CANT_EAT.search(t) or (_CAN_DRINK.search(t) and "eat" in t):
        data["liquid_calories"] = True

    if data.get("goal") is None:
        data.pop("goal", None)
    if not data and not equipment:
        return None
    try:
        facts = PlanFacts.model_validate(data)
    except ValueError:
        return None
    return Picked(facts=facts, equipment_add=list(dict.fromkeys(equipment)))
