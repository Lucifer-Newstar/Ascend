"""The build_plan action (actions-v4): save what you told the trainer and, if you like,
rebuild your plan from it. Propose -> confirm -> undo like every trainer action (R3, R5).

Undo puts everything back: the facts, the equipment checklist, the program you followed
before (the built plan is archived) and your training days.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.events import EventBus
from app.modules.actions.edits import CHOICE_LABEL, Choice, EditError
from app.modules.planbuilder import facts as factstore
from app.modules.planbuilder.build import Built, Person, build
from app.modules.planbuilder.facts import PlanFacts


class BuildPlanP(BaseModel):
    facts: PlanFacts = Field(default_factory=PlanFacts)
    equipment_add: list[Choice] = Field(default_factory=list, max_length=6)
    # False: only remember the facts; the plan stays as it is.
    rebuild: bool = True


def _person(db: Session, kit_add: list[str]) -> Person:
    from app.modules.planner.service import baseline_capacity
    from app.modules.progress import service as progress

    prof = progress.get_profile(db)
    if prof is None:
        raise EditError("Set up your profile first (Profile page), then I can build your plan.")
    cap = baseline_capacity(prof)
    kit = list(prof.equipment or [])
    kit += [k for k in kit_add if k not in kit]
    return Person(
        weight_kg=prof.weight_kg,
        age=prof.age,
        equipment=kit,
        pushups=cap["pushups"],
        pullups=cap["pullups"],
        plank_s=cap["plank_s"],
        sessions_per_week=int(progress.get_setting(db, "sessions_per_week", "3")),
        hide_calories=progress.get_setting(db, "hide_calories", "false") == "true",
        gaining=prof.goal == "bulk"
        or (prof.target_weight_kg is not None and prof.target_weight_kg > prof.weight_kg),
    )


def _plan(db: Session, p: BuildPlanP) -> tuple[PlanFacts, Built | None]:
    merged = factstore.merge(factstore.load(db), p.facts)
    if not p.rebuild:
        return merged, None
    return merged, build(merged, _person(db, list(p.equipment_add)))


def describe(db: Session, p: BuildPlanP) -> list[str]:
    merged, built = _plan(db, p)
    out = [f"Remember: {line}" for line in factstore.lines(p.facts)]
    if p.equipment_add:
        out.append(
            "Add to your equipment: " + ", ".join(CHOICE_LABEL[c] for c in p.equipment_add) + "."
        )
    if built is None:
        return out or ["Nothing new to remember."]
    out.append(f"New plan, {built.draft.summary.split('.')[0].lower()}: {built.week_line}.")
    out += built.notes
    out += built.food
    out.append("Your current program stays saved; undo switches back to it.")
    return out


def execute(
    db: Session, bus: EventBus, now: datetime, p: BuildPlanP
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    from app.modules.actions import edits
    from app.modules.planner import service as planner
    from app.modules.progress import service as progress
    from app.modules.schedule import service as schedule
    from app.modules.workouts import programs_service

    _person(db, [])  # a profile is needed for everything below
    merged, built = _plan(db, p)
    undo: dict[str, Any] = {
        "facts": progress.get_setting(db, factstore.SETTING_KEY, ""),
        "kit": None,
        "program_key": None,
        "program_id": None,
        "schedule": {
            k: progress.get_setting(db, k, "")
            for k in (schedule.DAYS_KEY, schedule.TIME_KEY, "sessions_per_week")
        },
    }
    factstore.save(db, merged)
    if p.equipment_add:
        old = edits._kit_now(db)
        new = edits._kit_after(old, edits.SetEquipmentP(add=list(p.equipment_add)))
        if new != old:
            edits._save_kit(db, new, now)
            undo["kit"] = old
    db.commit()
    result: dict[str, Any] = {"facts": json.loads(merged.model_dump_json(exclude_defaults=True))}
    if built is not None:
        before = programs_service.active(db)
        undo["program_key"] = before.program_key if before is not None else None
        saved = planner.save_program(db, built.draft, now)
        undo["program_id"] = saved.id
        programs_service.enroll(db, saved.key, now)
        time = progress.get_setting(db, schedule.TIME_KEY, "") or None
        schedule.save(db, built.weekdays, time, now.date())
        result.update(program_key=saved.key, days=built.weekdays)
    return result, undo


def undo(db: Session, bus: EventBus, now: datetime, u: dict[str, Any]) -> None:
    from app.modules.actions import edits
    from app.modules.planner import service as planner
    from app.modules.progress import service as progress
    from app.modules.workouts import programs_service

    progress.set_setting(db, factstore.SETTING_KEY, u.get("facts") or "")
    if u.get("kit") is not None:
        edits._save_kit(db, list(u["kit"]), now)
    if u.get("program_id") is not None:
        try:
            planner.delete_program(db, int(u["program_id"]), now)
        except planner.NotFound:
            pass
        if u.get("program_key"):
            try:
                programs_service.enroll(db, u["program_key"], now)
            except programs_service.UnknownProgram:
                pass
    for key, value in (u.get("schedule") or {}).items():
        progress.set_setting(db, key, value)
    db.commit()
