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
            kind=kind,
            params_json=params_json,
            status="executed",
            source=source,
            origin_text=origin,
            summary_json=summary,
            result_json=dumps(result),
            created_at=now,
            executed_at=now,
        )
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
    from app.modules.workouts.equipment import allowed_for_profile, fits_exercise
    from app.modules.workouts.models import Exercise

    allowed = allowed_for_profile(db)
    if fits_exercise(ex.name, ex.equipment, allowed):
        return ex
    base = ex.name.split()[-1]
    alt = db.scalars(
        select(Exercise).where(Exercise.name == f"Bodyweight {base}", Exercise.archived.is_(False))
    ).first()
    return alt if alt is not None else ex


def _as_set(db: Session, name: str, reps: int, sets: int = 1, kg: float = 0.0) -> dict[str, Any]:
    from app.modules.actions import registry

    ex = registry.resolve_exercise(db, name, strict=True)
    if not kg:
        ex = _bodyweight_variant(db, ex)
    return {"exercise": ex.name, "reps": reps, "weight_kg": kg, "sets": sets}


def _resolve_items(db: Session, hit: parser.Parsed) -> tuple[str, dict[str, Any]] | None:
    """ "2 idli and sambar" -> one meal; "10 pushups, 5 pullups" -> one card of sets. Every
    item must resolve the same way (all food or all exercises)."""
    from app.modules.actions import registry, resolve
    from app.modules.nutrition.models import Food

    p = hit.params
    items = list(p["items"])
    if not any(it.get("food_only") for it in items):
        sets = []
        for it in items:
            try:
                sets.append(
                    _as_set(
                        db,
                        str(it["name"]),
                        int(it["count"]),
                        int(it.get("sets", 1)),
                        float(it.get("weight_kg", 0.0)),
                    )
                )
            except registry.ActionError:
                sets = []
                break
        if sets:
            first, more = sets[0], sets[1:]
            return "log_set", {**first, "rpe": None, "more": more}
    foods: list[dict[str, Any]] = []
    loose = not p.get("meal_word") and all(it.get("bare") for it in items)
    for it in items:
        name = str(it["name"])
        if loose:  # "running with a backpack": only a line of known dishes is a meal
            exact = resolve.strict_food(db, name)
            if not exact:
                return None
            foods += [{"food": f.name, "portions": 1.0} for f in exact]
            continue
        if "grams" in it:
            found = registry.resolve_foods(db, name, grams=True)
            f = db.get(Food, found[0].id)
            assert f is not None
            portions = max(0.1, min(20.0, round(float(it["grams"]) / f.portion_g, 2)))
            foods.append({"food": f.name, "portions": portions})
            continue
        for f in registry.resolve_foods(db, name):  # raises: unknown / which one?
            foods.append({"food": f.name, "portions": float(it.get("count", 1.0))})
    first, more = foods[0], foods[1:]
    return "log_meal", {**first, "meal_type": p["meal_type"], "more": more}


def _resolve_ambiguous(db: Session, hit: parser.Parsed) -> tuple[str, dict[str, Any]] | None:
    """ "10 pushups" is a set, "2 idli" is food: an exercise name wins, then a food."""
    from app.modules.actions import registry

    p = hit.params
    if hit.kind == "log_items":
        return _resolve_items(db, hit)
    if hit.kind == "log_food_grams":
        try:
            foods = registry.resolve_foods(db, str(p["food"]), grams=True)
        except registry.UnknownFood:
            return None
        food = foods[0]
        portions = max(0.1, min(20.0, round(float(p["grams"]) / food.portion_g, 2)))
        return "log_meal", {"food": food.name, "portions": portions, "meal_type": p["meal_type"]}
    name, count = str(p["name"]), int(p["count"])
    try:
        return "log_set", {**_as_set(db, name, count), "rpe": None}
    except registry.ActionError:
        pass
    try:
        foods = registry.resolve_foods(db, name)
        first = {"food": foods[0].name, "portions": float(count)}
        more = [{"food": f.name, "portions": float(count)} for f in foods[1:]]
        return "log_meal", {**first, "meal_type": p["meal_type"], "more": more}
    except registry.AmbiguousName:
        raise
    except registry.ActionError:
        pass
    try:
        ex = registry.resolve_exercise(db, name)
    except registry.ActionError:
        # Neither an exercise nor a food we know: offer to add it as the user's own food.
        if count <= 20 and len(name.split()) <= 4:
            raise registry.UnknownFood(name) from None
        return None
    if count > 60:  # "bench 80" is not 80 reps
        return None
    ex = _bodyweight_variant(db, ex)
    return "log_set", {"exercise": ex.name, "reps": count, "weight_kg": 0.0, "sets": 1, "rpe": None}


def bare_food(
    db: Session, text: str, now: datetime, exact_only: bool = False
) -> tuple[str, dict[str, Any]] | None:
    """A line that only names a food ("ven pongal", "chutney"): one portion, by the clock.
    `exact_only`: the food's full name only ("tender coconut water"), no aliases."""
    from app.modules.actions import resolve

    t = text.strip().lower().rstrip(".!")
    foods = resolve.strict_food(db, t, exact_only)
    if not foods:
        return None
    first = {"food": foods[0].name, "portions": 1.0}
    more = [{"food": f.name, "portions": 1.0} for f in foods[1:]]
    return "log_meal", {**first, "meal_type": parser.meal_type_for(None, now.hour), "more": more}


def _with_kit(db: Session, params: dict[str, Any]) -> dict[str, Any]:
    """ "3x12 squats" for a user without a barbell is the bodyweight squat (v1.3: every
    path, not only "10 squats")."""
    from app.modules.actions import registry

    if params.get("weight_kg"):
        return params
    try:
        ex = _bodyweight_variant(db, registry.resolve_exercise(db, str(params["exercise"])))
    except registry.ActionError:
        return params
    return {**params, "exercise": ex.name}


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
    if hit is not None and hit.kind == "log_set":
        return hit.kind, _with_kit(db, hit.params), "rules"
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
            settings.ollama_host,
            model,
            "",
            text,
            timeout=runtime.timeout_for(settings, model),
            system=AI_SYSTEM,
            format=AI_SCHEMA,
        )
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
