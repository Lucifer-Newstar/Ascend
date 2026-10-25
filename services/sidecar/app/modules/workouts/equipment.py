"""Equipment the user said they have (onboarding), and which library exercises fit it.

The checklist is coarse on purpose: none / pull-up bar / rings / dumbbells / bench / gym.
An empty list means "not stated", and then nothing is filtered (profiles from before the
checklist existed keep every suggestion). "gym" allows everything. v1.3: rings count as a
bar for hanging and pulling moves (pull-ups, chin-ups, hangs, rows), and lifts that need a
bench (bench presses, incline and decline work) need "bench" ticked.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

CHOICES = ("none", "pullup_bar", "rings", "dumbbells", "bench", "gym")

# Library equipment that needs nothing (floor, mat, own body weight).
_ALWAYS = frozenset({"bodyweight", "none", "mat"})
_BY_CHOICE: dict[str, frozenset[str]] = {
    "none": frozenset(),
    "pullup_bar": frozenset({"bar"}),
    # Rings hang from anything: every pull-up, chin-up, hang and row works on them.
    "rings": frozenset({"rings", "bar"}),
    "dumbbells": frozenset({"dumbbell"}),
    "bench": frozenset({"bench"}),
}

# Library moves tagged only with their weight (a dumbbell, a barbell) that still need a
# bench to lie or sit on. Without "bench" (or "gym") they are left out; the planner
# offers a floor press instead.
_NEEDS_BENCH = re.compile(
    r"\b(bench press|incline (?:dumbbell|barbell|bench)|decline|chest fly(?:e)?s?|"
    r"dumbbell flyes?|hip thrust|pullover|preacher)\b",
    re.I,
)


def allowed_equipment(choices: Iterable[str]) -> frozenset[str] | None:
    """Library equipment values the user can use, or None for "no filter"."""
    picked = set(choices)
    if not picked or "gym" in picked:
        return None
    out = set(_ALWAYS)
    for c in picked:
        out |= _BY_CHOICE.get(c, frozenset())
    return frozenset(out)


def fits(equipment: str | None, allowed: frozenset[str] | None) -> bool:
    return allowed is None or (equipment or "none") in allowed


def needs_bench(name: str) -> bool:
    return bool(_NEEDS_BENCH.search(name))


def fits_exercise(name: str, equipment: str | None, allowed: frozenset[str] | None) -> bool:
    """`fits`, plus: a bench lift needs a bench (v1.3)."""
    if allowed is None:
        return True
    if needs_bench(name) and "bench" not in allowed:
        return False
    return fits(equipment, allowed)


def allowed_for_profile(db: object) -> frozenset[str] | None:
    """The filter for the stored profile (None without a profile or a checklist)."""
    from sqlalchemy.orm import Session

    from app.modules.progress.service import get_profile

    assert isinstance(db, Session)
    p = get_profile(db)
    return allowed_equipment(p.equipment) if p is not None else None
