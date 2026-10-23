"""Propose -> confirm -> execute -> (undo), with every step in the audit log."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.events import EventBus
from app.modules.actions import parser
from app.modules.actions.models import ActionLog
from app.modules.actions.registry import SPECS, ActionError, Spec, dumps
from app.modules.progress import service as progress

log = logging.getLogger("ascend.actions")
AUTO_PREFIX = "actions.auto."


class NotFound(Exception):
    pass


class Refused(Exception):
    """The action can't run in its current state (already done, wrong word typed...)."""


def spec_for(kind: str) -> Spec:
    if kind not in SPECS:
        raise ActionError(f"{kind} is not an allowed action")
    return SPECS[kind]


def auto_allowed(db: Session, kind: str) -> bool:
    spec = SPECS.get(kind)
    return bool(
        spec and spec.risk == "low" and progress.get_setting(db, AUTO_PREFIX + kind, "") == "true"
    )


def set_auto(db: Session, kind: str, allow: bool) -> None:
    spec = spec_for(kind)
    if spec.risk != "low" and allow:
        raise Refused("only low-risk actions can skip the confirm step")
    progress.set_setting(db, AUTO_PREFIX + kind, "true" if allow else "")
    db.commit()


def propose(
    db: Session, kind: str, params: dict[str, Any], source: str, text: str | None, now: datetime
) -> ActionLog:
    """Validate and describe an action; nothing changes until confirm()."""
    spec = spec_for(kind)
    try:
        p = spec.params.model_validate(params)
    except ValidationError as e:
        raise ActionError(f"{spec.label}: {e.errors()[0]['msg']}") from e
    summary = spec.describe(db, p)
    row = ActionLog(
        kind=kind,
        params_json=dumps(p.model_dump()),
        status="proposed",
        source=source,
        origin_text=(text or "")[:400] or None,
        summary_json=dumps(summary),
        created_at=now,
    )
    db.add(row)
    db.commit()
    return row


def get(db: Session, action_id: int) -> ActionLog:
    row = db.get(ActionLog, action_id)
    if row is None:
        raise NotFound(f"action {action_id} not found")
    return row


def confirm(
    db: Session,
    bus: EventBus,
    now: datetime,
    action_id: int,
    typed: str | None,
    eraser: Callable[[bool], dict[str, Any]] | None = None,
) -> ActionLog:
    row = get(db, action_id)
    if row.status != "proposed":
        raise Refused(f"this action is already {row.status}")
    spec = spec_for(row.kind)
    if spec.confirm_word and (typed or "").strip().upper() != spec.confirm_word:
        raise Refused(f"type {spec.confirm_word} to confirm")
    p = spec.params.model_validate(row.params)
    if row.kind == "erase_data":
        if eraser is None:
            raise Refused("erase needs the data folder")
        snapshot = (row.kind, row.params_json, row.source, row.origin_text, row.summary_json)
        result = eraser(bool(p.model_dump()["keep_preferences"]))
        # The erase wiped the audit log too; record the erase itself as its first entry.
        kind, params_json, source, origin, summary = snapshot
        row = ActionLog(
            kind=kind, params_json=params_json, status="executed", source=source,
            origin_text=origin, summary_json=summary, result_json=dumps(result),
            created_at=now, executed_at=now,
        )  # fmt: skip
        db.add(row)
        db.commit()
        return row
    try:
        result, undo = spec.execute(db, bus, now, p)
    except Exception as e:  # noqa: BLE001 - every failure is recorded, then shown
        db.rollback()
        row = get(db, action_id)
        row.status = "failed"
        row.error = str(e)[:300]
        db.commit()
        log.info("action %s failed: %s", row.kind, type(e).__name__)
        return row
    row.status = "executed"
    row.executed_at = now
    row.result_json = dumps(result)
    row.undo_json = dumps(undo) if undo is not None else None
    db.commit()
    return row


def cancel(db: Session, action_id: int) -> ActionLog:
    row = get(db, action_id)
    if row.status != "proposed":
        raise Refused(f"this action is already {row.status}")
    row.status = "cancelled"
    db.commit()
    return row


def undo(db: Session, bus: EventBus, now: datetime, action_id: int) -> ActionLog:
    row = get(db, action_id)
    spec = spec_for(row.kind)
    if row.status != "executed" or spec.undo is None or not row.undo_json:
        raise Refused("this action can't be undone here")
    spec.undo(db, bus, now, json.loads(row.undo_json))
    row.status = "undone"
    row.undone_at = now
    db.commit()
    return row


def recent(db: Session, limit: int = 50) -> list[ActionLog]:
    return list(db.scalars(select(ActionLog).order_by(ActionLog.id.desc()).limit(limit)).all())


# --- turning text into a proposal ---------------------------------------------------------

AI_SYSTEM = (
    "You turn one fitness-app request into a JSON action. Allowed kinds and params: "
    "log_set {exercise, reps, weight_kg, sets, rpe}, log_hold {exercise, seconds, rpe}, "
    "log_weight {weight_kg}, log_meal {food, portions, meal_type: breakfast|lunch|dinner|snack}, "
    "follow_program {program}. If the request is none of these, answer "
    '{"kind": "none", "params": {}}. Use only numbers the user wrote. JSON only.'
)
AI_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "kind": {
            "type": "string",
            "enum": ["log_set", "log_hold", "log_weight", "log_meal", "follow_program", "none"],
        },
        "params": {"type": "object"},
    },
    "required": ["kind", "params"],
}


def _bodyweight_variant(db: Session, ex: Any) -> Any:
    """ "10 squats" with no barbell in the kit is the bodyweight squat, not a back squat."""
    from app.modules.workouts.equipment import allowed_for_profile, fits
    from app.modules.workouts.models import Exercise

    allowed = allowed_for_profile(db)
    if fits(ex.equipment, allowed):
        return ex
    base = ex.name.split()[-1]
    alt = db.scalars(
        select(Exercise).where(Exercise.name == f"Bodyweight {base}", Exercise.archived.is_(False))
    ).first()
    return alt if alt is not None else ex


def _resolve_ambiguous(db: Session, hit: parser.Parsed) -> tuple[str, dict[str, Any]] | None:
    """ "10 pushups" is a set, "2 idli" is food: an exercise name wins, then a food."""
    from app.modules.actions import registry

    p = hit.params
    if hit.kind == "log_food_grams":
        try:
            food_id, _name = registry.resolve_food(db, str(p["food"]))
        except registry.ActionError:
            return None
        from app.modules.nutrition.models import Food

        food = db.get(Food, food_id)
        assert food is not None
        portions = max(0.1, min(20.0, round(float(p["grams"]) / food.portion_g, 2)))
        return "log_meal", {"food": food.name, "portions": portions, "meal_type": p["meal_type"]}
    name, count = str(p["name"]), int(p["count"])
    try:
        ex = _bodyweight_variant(db, registry.resolve_exercise(db, name, strict=True))
        return "log_set", {"exercise": ex.name, "reps": count, "weight_kg": 0.0, "sets": 1,
                           "rpe": None}  # fmt: skip
    except registry.ActionError:
        pass
    try:
        _fid, food_name = registry.resolve_food(db, name)
        return "log_meal", {"food": food_name, "portions": float(count),
                            "meal_type": p["meal_type"]}  # fmt: skip
    except registry.ActionError:
        pass
    try:
        ex = registry.resolve_exercise(db, name)
    except registry.ActionError:
        return None
    return "log_set", {"exercise": ex.name, "reps": count, "weight_kg": 0.0, "sets": 1,
                       "rpe": None}  # fmt: skip


def parse_text(
    db: Session, settings: Settings, text: str, now: datetime, rules_only: bool = False
) -> tuple[str, dict[str, Any], str] | None:
    """(kind, params, source) from rules, else from the local model when it is on
    (never with rules_only: then only the shared grammar can propose an action)."""
    units = progress.get_setting(db, "units", "metric")
    hit = parser.parse(text, units, now.hour)
    if hit is not None and hit.kind in parser.AMBIGUOUS_KINDS:
        resolved = _resolve_ambiguous(db, hit)
        return (*resolved, "rules") if resolved else None
    if hit is not None:
        return hit.kind, hit.params, "rules"
    if rules_only:
        return None
    from app.modules.coach import ollama, runtime
    from app.modules.coach.validate import check_numbers

    ok, _, model = runtime.available(db, settings)
    if not ok:
        return None
    try:
        raw = ollama.chat(
            settings.ollama_host, model, "", text, timeout=runtime.timeout_for(settings, model),
            system=AI_SYSTEM, format=AI_SCHEMA,
        )  # fmt: skip
        data = json.loads(raw)
    except (ollama.OllamaUnavailable, ValueError):
        return None
    kind = data.get("kind") if isinstance(data, dict) else None
    params = data.get("params") if isinstance(data, dict) else None
    if kind not in SPECS or kind == "erase_data" or not isinstance(params, dict):
        return None
    # The model may only reuse numbers the user wrote (the coach's number guard).
    if not check_numbers(json.dumps(params), text).ok:
        return None
    return str(kind), params, "ai"
