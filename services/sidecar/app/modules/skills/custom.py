"""User-written skill trees.

A custom skill is a list of milestones. Each milestone is a goal on a library exercise
(3x8 reps, 3x20 s, optionally with added kg); the first one is open from the start and
each next one opens when its own goal is shown in logged sets, judged by the same engine
as the built-in trees. They pay no XP (only the built-in trees do), so a custom tree
cannot be used to farm levels.
"""

from __future__ import annotations

import json
import re
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.skills.catalog import SKILL_BY_KEY, SKILLS, C, Skill, Step
from app.modules.skills.models import CustomSkill
from app.modules.workouts.models import Exercise

MAX_CUSTOM_SKILLS = 20
MAX_STEPS = 8
FAMILIES = ("pull", "push", "core", "balance", "legs", "levers", "custom")


class CustomSkillError(ValueError):
    pass


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:24] or "step"


def to_skill(row: CustomSkill) -> Skill:
    steps: list[Step] = []
    seen: set[str] = set()
    names: set[str] = set()
    for i, raw in enumerate(row.steps):
        exercise = str(raw["exercise"])
        names.add(exercise)
        sets = int(raw.get("sets") or 3)  # type: ignore[call-overload]
        reps = raw.get("reps")
        hold = raw.get("hold_s")
        kg = float(raw.get("added_kg") or 0)  # type: ignore[arg-type]
        crit = C(
            exercise,
            sets,
            int(reps) if reps is not None else None,  # type: ignore[call-overload]
            hold=int(hold) if hold is not None else None,  # type: ignore[call-overload]
            kg=kg,
        )
        key = f"m{i + 1}_{_slug(str(raw.get('name') or exercise))}"[:40]
        while key in seen:
            key += "x"
        seen.add(key)
        steps.append(Step(key, str(raw.get("name") or exercise)[:60], exercise, (crit,), xp=0))
    return Skill(
        row.key,
        row.name,
        row.family,
        row.summary or "Your own skill tree.",
        tuple(steps),
        tuple(sorted(names)),
        (),
        tags=("custom",),
    )


def custom_skills(db: Session) -> list[Skill]:
    rows = db.scalars(
        select(CustomSkill).where(CustomSkill.archived.is_(False)).order_by(CustomSkill.id)
    ).all()
    return [to_skill(r) for r in rows if r.steps]


def all_skills(db: Session) -> list[Skill]:
    """The built-in trees followed by the user's own."""
    return [*SKILLS, *custom_skills(db)]


def skill_by_key(db: Session, key: str) -> Skill | None:
    if key in SKILL_BY_KEY:
        return SKILL_BY_KEY[key]
    if not key.startswith("custom_") or not key[7:].isdigit():
        return None
    row = db.get(CustomSkill, int(key[7:]))
    if row is None or row.archived or not row.steps:
        return None
    return to_skill(row)


def _clean_steps(db: Session, steps: list[dict[str, object]]) -> list[dict[str, object]]:
    if not 1 <= len(steps) <= MAX_STEPS:
        raise CustomSkillError(f"A custom skill needs 1 to {MAX_STEPS} milestones.")
    out: list[dict[str, object]] = []
    for i, s in enumerate(steps, start=1):
        ex = db.get(Exercise, int(s["exercise_id"]))  # type: ignore[call-overload]
        if ex is None:
            raise CustomSkillError(f"Milestone {i}: that exercise is not in the library.")
        reps, hold = s.get("reps"), s.get("hold_s")
        if (reps is None) == (hold is None):
            raise CustomSkillError(f"Milestone {i}: give reps or seconds, not both.")
        if ex.measure == "hold" and hold is None:
            raise CustomSkillError(f"Milestone {i}: {ex.name} is a hold, so give seconds.")
        if ex.measure != "hold" and reps is None:
            raise CustomSkillError(f"Milestone {i}: {ex.name} is counted in reps.")
        out.append(
            {
                "name": str(s.get("name") or ex.name)[:60],
                "exercise": ex.name,
                "exercise_id": ex.id,
                "sets": int(s.get("sets") or 3),  # type: ignore[call-overload]
                "reps": int(reps) if reps is not None else None,  # type: ignore[call-overload]
                "hold_s": int(hold) if hold is not None else None,  # type: ignore[call-overload]
                "added_kg": float(s.get("added_kg") or 0),  # type: ignore[arg-type]
            }
        )
    return out


def create(
    db: Session, name: str, family: str, summary: str, steps: list[dict[str, object]], now: datetime
) -> CustomSkill:
    name = name.strip()
    if not name:
        raise CustomSkillError("Give the skill a name.")
    if family not in FAMILIES:
        raise CustomSkillError(f"family must be one of {', '.join(FAMILIES)}")
    live = db.scalars(select(CustomSkill).where(CustomSkill.archived.is_(False))).all()
    if len(live) >= MAX_CUSTOM_SKILLS:
        raise CustomSkillError(f"You can keep up to {MAX_CUSTOM_SKILLS} custom skills.")
    if any(r.name.lower() == name.lower() for r in live) or any(
        s.name.lower() == name.lower() for s in SKILLS
    ):
        raise CustomSkillError(f"A skill called {name} already exists.")
    row = CustomSkill(
        name=name[:60],
        family=family,
        summary=summary.strip()[:240],
        steps_json=json.dumps(_clean_steps(db, steps)),
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def update(
    db: Session,
    skill_id: int,
    name: str,
    family: str,
    summary: str,
    steps: list[dict[str, object]],
    now: datetime,
) -> CustomSkill:
    row = db.get(CustomSkill, skill_id)
    if row is None or row.archived:
        raise LookupError("custom skill not found")
    if family not in FAMILIES:
        raise CustomSkillError(f"family must be one of {', '.join(FAMILIES)}")
    row.name = name.strip()[:60] or row.name
    row.family = family
    row.summary = summary.strip()[:240]
    row.steps_json = json.dumps(_clean_steps(db, steps))
    row.updated_at = now
    _drop_unlocks(db, row.key)
    db.flush()
    return row


def _drop_unlocks(db: Session, key: str) -> None:
    from app.modules.skills.models import SkillUnlock

    for u in db.scalars(select(SkillUnlock).where(SkillUnlock.skill_key == key)).all():
        db.delete(u)


def archive(db: Session, skill_id: int) -> None:
    row = db.get(CustomSkill, skill_id)
    if row is None or row.archived:
        raise LookupError("custom skill not found")
    row.archived = True
    _drop_unlocks(db, row.key)
    db.flush()


def rows(db: Session) -> list[CustomSkill]:
    return list(
        db.scalars(
            select(CustomSkill).where(CustomSkill.archived.is_(False)).order_by(CustomSkill.id)
        ).all()
    )
