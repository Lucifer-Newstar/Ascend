"""actions-v3 (v1.3 wave 2): the trainer edits your plan, settings, kit and profile.

Same contract as every action: a proposal shows exactly what changes, nothing runs before
it is confirmed, and each one can be undone (the undo record keeps the old value). They
call the services the pages use; no SQL of their own beyond reading the current values.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.core.events import EventBus
from app.modules.actions.errors import ActionError

Choice = Literal["none", "pullup_bar", "rings", "dumbbells", "bench", "gym"]
CHOICE_LABEL: dict[str, str] = {
    "none": "no equipment",
    "pullup_bar": "pull-up bar",
    "rings": "rings",
    "dumbbells": "dumbbells",
    "bench": "bench",
    "gym": "full gym",
}
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


class EditError(ActionError):
    """An edit that can't apply (no profile, no program, that move isn't in the plan...)."""


# --- profile --------------------------------------------------------------------------

ProfileField = Literal[
    "name", "age", "height_cm", "weight_kg", "goal", "activity", "target_weight_kg",
    "experience", "focus",
]  # fmt: skip
PROFILE_LABEL = {
    "name": "name", "age": "age", "height_cm": "height", "weight_kg": "body weight",
    "goal": "goal", "activity": "activity level", "target_weight_kg": "target weight",
    "experience": "training experience", "focus": "training focus",
}  # fmt: skip


class UpdateProfileP(BaseModel):
    field: ProfileField
    value: str | float | int | None


def _profile_value(field: str, value: Any) -> str:
    if value is None or value == "":
        return "not set"
    if field in ("height_cm",):
        return f"{float(value):g} cm"
    if field in ("weight_kg", "target_weight_kg"):
        return f"{float(value):g} kg"
    return str(value).replace("_", " ")


def _profile_in(db: Session, p: UpdateProfileP) -> tuple[Any, Any]:
    """(the validated new ProfileIn, the old value)."""
    from app.modules.progress import service as progress
    from app.modules.progress.schemas import ProfileIn

    prof = progress.get_profile(db)
    if prof is None:
        raise EditError("Set up your profile first (Profile page), then I can change it.")
    data = {k: getattr(prof, k) for k in ProfileIn.model_fields}
    old = data.get(p.field)
    data[p.field] = p.value
    try:
        return ProfileIn(**data), old
    except ValidationError as e:
        msg = e.errors()[0].get("msg", "that value isn't allowed")
        raise EditError(f"I can't set your {PROFILE_LABEL[p.field]} to {p.value}: {msg}.") from e


def describe_profile(db: Session, p: UpdateProfileP) -> list[str]:
    new, old = _profile_in(db, p)
    label = PROFILE_LABEL[p.field]
    lines = [
        f"Change your {label} from {_profile_value(p.field, old)} to "
        f"{_profile_value(p.field, getattr(new, p.field))}."
    ]
    if p.field in ("weight_kg", "height_cm", "age", "goal", "activity"):
        lines.append("Your calorie and protein targets are worked out again from it.")
    return lines


def exec_profile(
    db: Session, bus: EventBus, now: datetime, p: UpdateProfileP
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    from app.modules.progress import service as progress

    new, old = _profile_in(db, p)
    progress.upsert_profile(db, new)
    return {"field": p.field, "value": getattr(new, p.field)}, {"field": p.field, "old": old}


def undo_profile(db: Session, bus: EventBus, now: datetime, u: dict[str, Any]) -> None:
    from app.modules.progress import service as progress

    new, _ = _profile_in(db, UpdateProfileP(field=u["field"], value=u["old"]))
    progress.upsert_profile(db, new)


# --- equipment ------------------------------------------------------------------------


class SetEquipmentP(BaseModel):
    add: list[Choice] = Field(default_factory=list, max_length=6)
    remove: list[Choice] = Field(default_factory=list, max_length=6)


def _kit_now(db: Session) -> list[str]:
    from app.modules.progress import service as progress

    prof = progress.get_profile(db)
    if prof is None:
        raise EditError("Set up your profile first (Profile page), then I can change your kit.")
    return list(prof.equipment or [])


def _kit_after(old: list[str], p: SetEquipmentP) -> list[str]:
    kit = [c for c in old if c not in p.remove]
    for c in p.add:
        if c not in kit:
            kit.append(c)
    if any(c != "none" for c in kit):
        kit = [c for c in kit if c != "none"]
    return kit or ["none"]


def _kit_label(kit: list[str]) -> str:
    return ", ".join(CHOICE_LABEL[c] for c in kit) if kit else "not stated"


def describe_equipment(db: Session, p: SetEquipmentP) -> list[str]:
    old = _kit_now(db)
    new = _kit_after(old, p)
    if new == old:
        raise EditError(f"Your kit is already: {_kit_label(old)}.")
    return [
        f"Change your equipment from {_kit_label(old)} to {_kit_label(new)}.",
        "Exercise lists, the planner and new plans follow it; your logged sets stay as they are.",
    ]


def _save_kit(db: Session, kit: list[str], now: datetime) -> None:
    from app.modules.gamification import service as game
    from app.modules.progress import service as progress
    from app.modules.progress.schemas import ProfileIn

    prof = progress.get_profile(db)
    assert prof is not None
    data = {k: getattr(prof, k) for k in ProfileIn.model_fields}
    data["equipment"] = kit
    progress.upsert_profile(db, ProfileIn(**data))
    game.refresh_training_item(db, now)  # today's quest follows the new kit, like PUT /profile


def exec_equipment(
    db: Session, bus: EventBus, now: datetime, p: SetEquipmentP
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    old = _kit_now(db)
    new = _kit_after(old, p)
    _save_kit(db, new, now)
    return {"equipment": new}, {"old": old}


def undo_equipment(db: Session, bus: EventBus, now: datetime, u: dict[str, Any]) -> None:
    _save_kit(db, list(u["old"]), now)


# --- settings -------------------------------------------------------------------------

SettingKey = Literal[
    "units", "theme", "reminders", "hide_calories", "reduce_motion", "ai_enabled",
    "trainer_id", "sessions_per_week", "background_art",
]  # fmt: skip
SETTING_LABEL = {
    "units": "units", "theme": "theme", "reminders": "reminders", "hide_calories":
    "hide calories", "reduce_motion": "reduce motion", "ai_enabled": "local AI",
    "trainer_id": "trainer", "sessions_per_week": "sessions per week",
    "background_art": "background art",
}  # fmt: skip


class UpdateSettingP(BaseModel):
    key: SettingKey
    value: str | bool | int


def _show(key: str, value: Any) -> str:
    if isinstance(value, bool):
        return "on" if value else "off"
    if key == "units":
        return {"metric": "kg and cm", "imperial": "lb and in"}.get(str(value), str(value))
    return str(value).replace("_", " ")


def _setting_in(p: UpdateSettingP) -> Any:
    from app.modules.progress.schemas import SettingsIn

    try:
        return SettingsIn.model_validate({p.key: p.value})
    except ValidationError as e:
        raise EditError(f"{p.value} isn't a choice for {SETTING_LABEL[p.key]}.") from e


def describe_setting(db: Session, p: UpdateSettingP) -> list[str]:
    from app.modules.progress import service as progress

    new = getattr(_setting_in(p), p.key)
    old = getattr(progress.read_settings(db), p.key)
    if new == old:
        raise EditError(f"{SETTING_LABEL[p.key].capitalize()} is already {_show(p.key, old)}.")
    lines = [f"Change {SETTING_LABEL[p.key]} from {_show(p.key, old)} to {_show(p.key, new)}."]
    if p.key == "sessions_per_week":
        lines.append(
            "Your weekly goal and the planner use this; the program you follow keeps its own "
            "days until you move or add one."
        )
    return lines


def exec_setting(
    db: Session, bus: EventBus, now: datetime, p: UpdateSettingP
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    from app.modules.progress import service as progress

    old = getattr(progress.read_settings(db), p.key)
    out = progress.update_settings(db, _setting_in(p))
    return {"key": p.key, "value": getattr(out, p.key)}, {"key": p.key, "old": old}


def undo_setting(db: Session, bus: EventBus, now: datetime, u: dict[str, Any]) -> None:
    from app.modules.progress import service as progress

    progress.update_settings(db, _setting_in(UpdateSettingP(key=u["key"], value=u["old"])))


# --- the followed plan ----------------------------------------------------------------

PlanOp = Literal["swap", "remove", "add", "sets", "reps", "rest", "move_day"]


class EditPlanP(BaseModel):
    op: PlanOp
    exercise: str | None = Field(default=None, max_length=80)
    new_exercise: str | None = Field(default=None, max_length=80)
    weekday: int | None = Field(default=None, ge=0, le=6)
    # "move leg day to saturday": the day by (part of) its name when no weekday is given
    day: str | None = Field(default=None, max_length=40)
    to_weekday: int | None = Field(default=None, ge=0, le=6)
    sets: int | None = Field(default=None, ge=1, le=10)
    rep_low: int | None = Field(default=None, ge=1, le=300)
    rep_high: int | None = Field(default=None, ge=1, le=300)
    rest_s: int | None = Field(default=None, ge=10, le=600)


def _rest(seconds: int) -> str:
    """90 -> "90 s", 120 -> "2 min", 150 -> "2 min 30 s"."""
    if seconds < 120:
        return f"{seconds} s"
    mins, secs = divmod(seconds, 60)
    return f"{mins} min" if not secs else f"{mins} min {secs} s"


def _current(db: Session) -> tuple[Any, Any]:
    from app.modules.workouts import programs_service
    from app.modules.workouts.equipment import allowed_for_profile

    e = programs_service.active(db)
    if e is None:
        raise EditError(
            "You don't follow a program yet. Pick one first (say \u201cfollow ppl\u201d)."
        )
    p = programs_service.get_program(db, e.program_key)
    if p is None:
        raise EditError("The program you follow is no longer available.")
    # Edit what the user sees: built-in moves their kit can't do are already swapped.
    lib = programs_service._library(db)
    return e, programs_service.for_kit(p, lib, allowed_for_profile(db))


def _days(program: Any) -> list[dict[str, Any]]:
    return [
        {
            "key": d.key,
            "name": d.name,
            "focus": d.focus,
            "weekday": d.weekday,
            "slots": [
                {
                    "exercise": s.exercise,
                    "sets": s.sets,
                    "rep_low": s.rep_low,
                    "rep_high": s.rep_high,
                    "target_rpe": s.target_rpe,
                    "rest_s": s.rest_s,
                }
                for s in d.slots
            ],
        }
        for d in program.days
    ]


def _find(days: list[dict[str, Any]], name: str) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    from app.modules.actions.resolve import compact

    want = compact(name)
    hits = [(d, s) for d in days for s in d["slots"] if compact(s["exercise"]) == want]
    if not hits:
        hits = [(d, s) for d in days for s in d["slots"] if want in compact(s["exercise"])]
    return hits


def _resolve(db: Session, name: str) -> str:
    from app.modules.actions.registry import ActionError, resolve_exercise

    try:
        return resolve_exercise(db, name).name
    except ActionError as e:
        raise EditError(str(e)) from e


def _apply(db: Session, program: Any, p: EditPlanP) -> tuple[list[dict[str, Any]], list[str]]:
    """The plan's days after the edit, and what changed in words."""
    days = _days(program)
    on = [d for d in days if p.weekday is None or d["weekday"] == p.weekday]
    if p.op in ("swap", "remove", "sets", "reps", "rest"):
        hits = [(d, s) for d, s in _find(days, p.exercise or "") if d in on]
        if not hits:
            where = f" on {WEEKDAYS[p.weekday]}" if p.weekday is not None else ""
            raise EditError(f"\u201c{p.exercise}\u201d isn't in {program.name}{where}.")
        name = hits[0][1]["exercise"]
        if p.op == "swap":
            new = _resolve(db, p.new_exercise or "")
            for _, s in hits:
                s["exercise"] = new
            return days, [f"Swap {name} for {new} in {program.name} ({len(hits)} \u00d7)."]
        if p.op == "remove":
            for d, s in hits:
                d["slots"].remove(s)
            if any(not d["slots"] for d in days):
                raise EditError(f"Removing {name} would leave a day with nothing on it.")
            return days, [f"Remove {name} from {program.name} ({len(hits)} \u00d7)."]
        if p.op == "sets":
            was = hits[0][1]["sets"]
            for _, s in hits:
                s["sets"] = p.sets
            return days, [f"{name}: {p.sets} sets instead of {was}."]
        if p.op == "rest":
            if p.rest_s is None:
                raise EditError(f"How long a rest do you want between sets of {name}?")
            was_s = hits[0][1]["rest_s"]
            for _, s in hits:
                s["rest_s"] = p.rest_s
            return days, [f"{name}: rest {_rest(p.rest_s)} between sets instead of {_rest(was_s)}."]
        lo, hi = p.rep_low or 1, p.rep_high or p.rep_low or 1
        old = f"{hits[0][1]['rep_low']}\u2013{hits[0][1]['rep_high']}"
        for _, s in hits:
            s["rep_low"], s["rep_high"] = lo, max(lo, hi)
        return days, [f"{name}: {lo}\u2013{max(lo, hi)} instead of {old}."]
    if p.op == "add":
        new = _resolve(db, p.exercise or "")
        targets = on if p.weekday is not None else days[:1]
        if not targets:
            raise EditError(f"{program.name} has no training day on {WEEKDAYS[p.weekday or 0]}.")
        for d in targets:
            d["slots"].append(
                {"exercise": new, "sets": p.sets or 3, "rep_low": p.rep_low or 8,
                 "rep_high": p.rep_high or p.rep_low or 12, "target_rpe": 8.0, "rest_s": 90}
            )  # fmt: skip
        day = targets[0]
        return days, [
            f"Add {p.sets or 3} sets of {new} to {day['name']} ({WEEKDAYS[day['weekday']]})."
        ]
    # move_day
    if p.weekday is not None:
        src = [d for d in days if d["weekday"] == p.weekday]
    else:
        want = (p.day or "").lower().replace(" day", "").strip()
        src = [d for d in days if want and want in d["name"].lower()]
    if not src or p.to_weekday is None:
        what = WEEKDAYS[p.weekday] if p.weekday is not None else f"\u201c{p.day}\u201d"
        raise EditError(f"{program.name} has no training day on {what}.")
    frm = WEEKDAYS[src[0]["weekday"]]
    if any(d["weekday"] == p.to_weekday for d in days):
        raise EditError(f"{WEEKDAYS[p.to_weekday]} already has a session in {program.name}.")
    src[0]["weekday"] = p.to_weekday
    days.sort(key=lambda d: d["weekday"])
    return days, [f"Move {src[0]['name']} from {frm} to {WEEKDAYS[p.to_weekday]}."]


def describe_plan(db: Session, p: EditPlanP) -> list[str]:
    from app.modules.planner.service import CUSTOM_PREFIX

    e, program = _current(db)
    _, lines = _apply(db, program, p)
    if not e.program_key.startswith(CUSTOM_PREFIX):
        lines.append(
            f"{program.name} is built in, so this saves your own copy and you follow it from "
            "here; your progress through the week carries over."
        )
    return lines


def exec_plan(
    db: Session, bus: EventBus, now: datetime, p: EditPlanP
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    from app.modules.planner import service as planner
    from app.modules.planner.models import CustomProgram
    from app.modules.planner.schemas import ProgramDraft
    from app.modules.workouts import programs_service

    e, program = _current(db)
    days, lines = _apply(db, program, p)
    if e.program_key.startswith(planner.CUSTOM_PREFIX):
        row = db.get(CustomProgram, int(e.program_key[len(planner.CUSTOM_PREFIX) :]))
        assert row is not None
        old = row.days_json
        row.days_json = json.dumps(days)
        row.updated_at = now
        db.commit()
        return {"program": row.name, "change": lines[0]}, {"custom_id": row.id, "old_days": old}
    equipment = program.equipment if program.equipment in ("gym", "dumbbells") else "bodyweight"
    level = {"expert": "advanced"}.get(program.level, program.level)
    draft = ProgramDraft.model_validate(
        {
            "name": f"{program.name} (my version)"[:80],
            "summary": program.summary[:400],
            "level": level if level in ("beginner", "intermediate", "advanced") else "beginner",
            "equipment": equipment,
            "days": days,
        }
    )
    saved = planner.save_program(db, draft, now)
    started = e.started_on
    new = programs_service.enroll(db, saved.key, now)
    new.started_on = started  # the week's progress carries over to the copy
    db.commit()
    return {"program": saved.name, "change": lines[0]}, {
        "copy_id": saved.id,
        "previous": e.program_key,
        "started_on": started.isoformat(),
    }


def undo_plan(db: Session, bus: EventBus, now: datetime, u: dict[str, Any]) -> None:
    from datetime import date

    from app.modules.planner import service as planner
    from app.modules.planner.models import CustomProgram
    from app.modules.workouts import programs_service

    if "custom_id" in u:
        row = db.get(CustomProgram, u["custom_id"])
        if row is not None:
            row.days_json = u["old_days"]
            row.updated_at = now
            db.commit()
        return
    e = programs_service.enroll(db, u["previous"], now)
    e.started_on = date.fromisoformat(u["started_on"])
    db.commit()
    try:
        planner.delete_program(db, u["copy_id"], now)
    except planner.NotFound:
        pass
