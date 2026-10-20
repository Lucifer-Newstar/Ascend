"""Equipment the user said they have (onboarding), and which library exercises fit it.

The checklist is coarse on purpose: none / pull-up bar / rings / dumbbells / gym. An
empty list means "not stated", and then nothing is filtered (profiles from before the
checklist existed keep every suggestion). "gym" allows everything.
"""

from __future__ import annotations

from collections.abc import Iterable

CHOICES = ("none", "pullup_bar", "rings", "dumbbells", "gym")

# Library equipment that needs nothing (floor, mat, own body weight).
_ALWAYS = frozenset({"bodyweight", "none", "mat"})
_BY_CHOICE: dict[str, frozenset[str]] = {
    "none": frozenset(),
    "pullup_bar": frozenset({"bar"}),
    "rings": frozenset({"rings"}),
    "dumbbells": frozenset({"dumbbell"}),
}


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


def allowed_for_profile(db: object) -> frozenset[str] | None:
    """The filter for the stored profile (None without a profile or a checklist)."""
    from sqlalchemy.orm import Session

    from app.modules.progress.service import get_profile

    assert isinstance(db, Session)
    p = get_profile(db)
    return allowed_equipment(p.equipment) if p is not None else None
