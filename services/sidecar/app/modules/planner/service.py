"""Planner service: the AI is the brain that drafts plans; engines own every number.

Flow for both plans: read the profile -> goalcheck-v1 flags -> rule-based generator
(plangen-v1 / dietgen-v1) -> optionally the local model rewords the summary/notes, and the
coach's number guard rejects any rewording that changes or invents a number -> the user
reviews, edits and saves. Nothing is saved without the user asking.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.coach import ollama, validate
from app.modules.nutrition.models import Food
from app.modules.planner import diet_gen, section_gen, workout_gen
from app.modules.planner import validate as goalcheck
from app.modules.planner.models import CustomProgram, DietPlan
from app.modules.planner.schemas import (
    CustomProgramOut,
    DayIO,
    DayPlanOut,
    DietPlanIn,
    DietPlanOut,
    FlagOut,
    GoalCheckIn,
    GoalCheckOut,
    Phrased,
    ProgramDraft,
    SavedDietOut,
    SlotIO,
    WorkoutPlanIn,
    WorkoutPlanOut,
)
from app.modules.progress import service as progress
from app.modules.workouts import equipment as equipment_rules
from app.modules.workouts import programs
from app.modules.workouts.models import Exercise, PlanEnrollment

log = logging.getLogger("ascend")

CUSTOM_PREFIX = "custom-"

PLANNER_SYSTEM = (
    "You reword a fitness app's plan summary for the user. Keep every number exactly as "
    "given and add no new numbers, exercises, foods or medical claims. Two short, friendly "
    "sentences in second person. No lists, no headings."
)


class NoProfile(Exception):
    pass


class NotFound(Exception):
    pass


class UnknownExercise(ValueError):
    pass


def flags_out(flags: list[goalcheck.Flag]) -> list[FlagOut]:
    return [FlagOut(**asdict(f)) for f in flags]


def check(body: GoalCheckIn) -> GoalCheckOut:
    flags: list[goalcheck.Flag] = []
    if body.weight_kg and body.target_weight_kg and body.weeks:
        flags += goalcheck.check_weight_goal(
            body.weight_kg, body.target_weight_kg, body.weeks, body.height_cm
        )
    if body.weight_kg and body.target_weight_kg:
        flags += goalcheck.check_age(body.age, body.target_weight_kg < body.weight_kg)
    if body.protein_g is not None and body.weight_kg:
        flags += goalcheck.check_protein(body.protein_g, body.weight_kg)
    if body.days_per_week is not None:
        flags += goalcheck.check_schedule(
            body.days_per_week, body.minutes or 60, body.experience or "beginner"
        )
    if body.lift_current_kg and body.lift_target_kg and body.lift_weeks:
        flags += goalcheck.check_strength_goal(
            body.lift_current_kg,
            body.lift_target_kg,
            body.lift_weeks,
            body.experience or "beginner",
        )
    return GoalCheckOut(
        flags=flags_out(flags), worst=goalcheck.worst(flags), algo_version=goalcheck.ALGO_VERSION
    )


def profile_flags(db: Session) -> list[goalcheck.Flag]:
    """Checks on the stored profile's own goal (the trainer repeats these when planning)."""
    p = progress.get_profile(db)
    if p is None:
        return []
    flags: list[goalcheck.Flag] = []
    if p.target_weight_kg:
        flags += goalcheck.check_weight_goal(p.weight_kg, p.target_weight_kg, 0, p.height_cm)
    flags += goalcheck.check_age(p.age, p.goal == "cut")
    e = progress.energy_for(p)
    flags += goalcheck.check_calories(e.kcal_target, p.sex, e.bmr)
    return flags


def phrase(db: Session, settings: Settings, text: str, use_ai: bool) -> tuple[str, Phrased]:
    """The local model's rewording of `text`, or `text` itself (AI off, Ollama missing,
    an error, or the number guard rejecting the rewording)."""
    if not use_ai or not progress.ai_enabled(db):
        return text, "rules"
    if not ollama.is_available(settings.ollama_host, settings.coach_model):
        return text, "rules"
    try:
        out = ollama.chat(
            settings.ollama_host,
            settings.coach_model,
            text,
            "Reword the summary above.",
            timeout=settings.coach_timeout_s,
            system=PLANNER_SYSTEM,
        )
    except ollama.OllamaUnavailable as e:
        log.info("planner wording kept (ollama: %s)", e)
        return text, "rules"
    checks = validate.check_reply(out, text, None)
    if not checks.ok:
        log.info("planner wording rejected by the guard: %s", checks.summary())
        return text, "rules"
    return out, "ollama"


def _library(db: Session) -> dict[str, Exercise]:
    return {e.name: e for e in db.scalars(select(Exercise).where(Exercise.archived.is_(False)))}


def baseline_capacity(p: object | None) -> dict[str, int | None]:
    """Max push-ups / pull-ups from the onboarding baseline test (None when not tested)."""
    base = getattr(p, "baseline", None) or {}
    out: dict[str, int | None] = {}
    for key in ("pushups", "pullups"):
        v = base.get(key) if isinstance(base, dict) else None
        out[key] = int(v) if isinstance(v, int | float) else None
    return out


def _draft_section(
    db: Session, settings: Settings, body: WorkoutPlanIn, experience: str
) -> WorkoutPlanOut:
    """v1.2: a cardio, martial-arts, mobility or meditation plan (section_gen)."""
    lib = _library(db)
    gen = section_gen.generate(str(body.section), experience, body.days_per_week)
    summary, phrased = phrase(db, settings, gen.summary, body.use_ai)
    draft = ProgramDraft(
        name=gen.name,
        summary=summary,
        level="advanced" if gen.level == "expert" else gen.level,  # type: ignore[arg-type]
        equipment="bodyweight",
        notes=list(gen.notes),
        days=[
            DayIO(
                key=d.key,
                name=d.name,
                focus=d.focus,
                weekday=d.weekday,
                slots=[
                    SlotIO(**asdict(s), exercise_id=lib[s.exercise].id)
                    for s in d.slots
                    if s.exercise in lib
                ],
            )
            for d in gen.days
        ],
    )
    return WorkoutPlanOut(
        draft=draft,
        flags=flags_out(profile_flags(db)),
        phrased_by=phrased,
        algo_version=f"{workout_gen.ALGO_VERSION}+section",
    )


def draft_workout(db: Session, settings: Settings, body: WorkoutPlanIn) -> WorkoutPlanOut:
    p = progress.get_profile(db)
    experience = body.experience or (p.experience if p and p.experience else "beginner")
    if body.section in section_gen.TIME_SECTIONS:
        return _draft_section(db, settings, body, experience)
    choices = body.equipment if body.equipment is not None else (p.equipment if p else [])
    if body.section == "calisthenics":  # body weight, bar and rings only
        choices = [c for c in choices if c in ("none", "pullup_bar", "rings")] or ["none"]
    allowed = equipment_rules.allowed_equipment(choices)
    lib = _library(db)
    flags = goalcheck.check_schedule(body.days_per_week, body.minutes, experience)  # type: ignore[arg-type]
    gen = workout_gen.generate(
        focus=body.focus,
        experience=experience,  # type: ignore[arg-type]
        equipment=choices,
        days_per_week=min(body.days_per_week, workout_gen.MAX_DAYS),
        minutes=body.minutes,
        available=lambda n: n in lib and equipment_rules.fits(lib[n].equipment, allowed),
        is_hold=lambda n: n in lib and lib[n].measure == "hold",
        capacity=baseline_capacity(p),
    )
    summary, phrased = phrase(db, settings, gen.summary, body.use_ai)
    draft = ProgramDraft(
        name=gen.name,
        summary=summary,
        level=gen.level,
        equipment=gen.equipment,
        notes=list(gen.notes),
        days=[
            DayIO(
                key=d.key,
                name=d.name,
                focus=d.focus,
                weekday=d.weekday,
                slots=[SlotIO(**asdict(s), exercise_id=lib[s.exercise].id) for s in d.slots],
            )
            for d in gen.days
        ],
    )
    return WorkoutPlanOut(
        draft=draft,
        flags=flags_out(flags + profile_flags(db)),
        phrased_by=phrased,
        algo_version=workout_gen.ALGO_VERSION,
    )


def _check_names(db: Session, draft: ProgramDraft) -> None:
    lib = _library(db)
    for d in draft.days:
        for s in d.slots:
            if s.exercise not in lib:
                raise UnknownExercise(s.exercise)
            if s.rep_high < s.rep_low:
                raise ValueError(f"{s.exercise}: rep_high is below rep_low")


def _days_json(draft: ProgramDraft) -> str:
    return json.dumps(
        [d.model_dump(exclude={"slots": {"__all__": {"exercise_id"}}}) for d in draft.days]
    )


def _following_key(db: Session) -> str | None:
    e = db.scalars(
        select(PlanEnrollment)
        .where(PlanEnrollment.ended_at.is_(None))
        .order_by(PlanEnrollment.id.desc())
    ).first()
    return e.program_key if e else None


def program_out(row: CustomProgram, following: str | None = None) -> CustomProgramOut:
    return CustomProgramOut(
        id=row.id,
        key=row.key,
        name=row.name,
        summary=row.summary,
        level=row.level,  # type: ignore[arg-type]
        equipment=row.equipment,  # type: ignore[arg-type]
        days=[DayIO(**d) for d in row.days],
        notes=row.notes,
        algo_version=row.algo_version,
        created_at=row.created_at,
        updated_at=row.updated_at,
        following=following == row.key,
    )


def save_program(db: Session, draft: ProgramDraft, now: datetime) -> CustomProgramOut:
    _check_names(db, draft)
    row = CustomProgram(
        name=draft.name,
        summary=draft.summary,
        level=draft.level,
        equipment=draft.equipment,
        days_json=_days_json(draft),
        notes_json=json.dumps(draft.notes),
        algo_version=workout_gen.ALGO_VERSION,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    return program_out(row)


def _get(db: Session, program_id: int) -> CustomProgram:
    row = db.get(CustomProgram, program_id)
    if row is None or row.archived:
        raise NotFound(program_id)
    return row


def update_program(
    db: Session, program_id: int, draft: ProgramDraft, now: datetime
) -> CustomProgramOut:
    row = _get(db, program_id)
    _check_names(db, draft)
    row.name = draft.name
    row.summary = draft.summary
    row.level = draft.level
    row.equipment = draft.equipment
    row.days_json = _days_json(draft)
    row.notes_json = json.dumps(draft.notes)
    row.updated_at = now
    db.commit()
    return program_out(row, _following_key(db))


def delete_program(db: Session, program_id: int, now: datetime) -> None:
    """Archive (the enrollment history keeps pointing at it); stop following it."""
    row = _get(db, program_id)
    row.archived = True
    db.execute(
        update(PlanEnrollment)
        .where(PlanEnrollment.program_key == row.key, PlanEnrollment.ended_at.is_(None))
        .values(ended_at=now)
    )
    db.commit()


def list_programs(db: Session) -> list[CustomProgramOut]:
    following = _following_key(db)
    rows = db.scalars(
        select(CustomProgram)
        .where(CustomProgram.archived.is_(False))
        .order_by(CustomProgram.id.desc())
    )
    return [program_out(r, following) for r in rows]


def as_program(row: CustomProgram) -> programs.Program:
    """The stored plan as a programs-v1 Program, so the plan, progression and boss engines
    treat it exactly like a built-in one."""
    return programs.Program(
        key=row.key,
        name=row.name,
        summary=row.summary,
        level=row.level,
        equipment=row.equipment,
        days=tuple(
            programs.Day(
                d["key"],
                d["name"],
                d.get("focus", ""),
                int(d["weekday"]),
                tuple(
                    programs.Slot(
                        s["exercise"],
                        int(s["sets"]),
                        int(s["rep_low"]),
                        int(s["rep_high"]),
                        float(s.get("target_rpe", 8.0)),
                        int(s.get("rest_s", 120)),
                    )
                    for s in d["slots"]
                ),
            )
            for d in row.days
        ),
    )


def get_program(db: Session, key: str) -> programs.Program | None:
    """A built-in program by key, or a saved custom one ("custom-<id>")."""
    if key.startswith(CUSTOM_PREFIX):
        try:
            row = db.get(CustomProgram, int(key[len(CUSTOM_PREFIX) :]))
        except ValueError:
            return None
        return as_program(row) if row is not None and not row.archived else None
    return programs.PROGRAMS.get(key)


# --- diet -------------------------------------------------------------------------


def _foods(db: Session) -> dict[str, diet_gen.FoodInfo]:
    return {
        f.name: diet_gen.FoodInfo(f.name, f.portion_label, f.kcal, f.protein_g, f.carbs_g, f.fat_g)
        for f in db.scalars(select(Food))
    }


def draft_diet(db: Session, settings: Settings, body: DietPlanIn) -> DietPlanOut:
    p = progress.get_profile(db)
    if p is None:
        raise NoProfile()
    e = progress.energy_for(p)
    kcal = body.kcal_target or e.kcal_target
    flags = goalcheck.check_calories(kcal, p.sex, e.bmr)
    if flags:  # below the floor: plan at the floor and say so
        kcal = goalcheck.kcal_floor(p.sex, e.bmr)
    # The daily target is already at maintenance for a "cut" under 18 (energy_goal), so the
    # chosen goal still counts as asking for a deficit and the plan says why it is not one.
    asks_deficit = kcal < e.tdee - 50 or (body.kcal_target is None and p.goal == "cut")
    under_18 = goalcheck.check_age(p.age, asks_deficit)
    if under_18:  # no deficit plans for under-18s: plan at maintenance and say so
        flags += under_18
        kcal = round(e.tdee)
    gen = diet_gen.generate(kcal, e.protein_target_g, _foods(db), body.diet)
    flags += goalcheck.check_protein(
        sum(d.protein_g for d in gen.days) / len(gen.days), p.weight_kg
    )
    notes = list(gen.notes)
    notes[0], phrased = phrase(db, settings, notes[0], body.use_ai)
    return DietPlanOut(
        kcal_target=gen.kcal_target,
        protein_target_g=gen.protein_target_g,
        diet=gen.diet,
        days=[
            DayPlanOut.model_validate(
                {
                    "day": d.day,
                    "kcal": d.kcal,
                    "protein_g": d.protein_g,
                    "meals": [
                        {
                            "meal": m.meal,
                            "kcal": m.kcal,
                            "protein_g": m.protein_g,
                            "items": [asdict(i) for i in m.items],
                        }
                        for m in d.meals
                    ],
                }
            )
            for d in gen.days
        ],
        notes=notes,
        flags=flags_out(flags),
        phrased_by=phrased,
        algo_version=diet_gen.ALGO_VERSION,
    )


def _diet_out(row: DietPlan) -> SavedDietOut:
    return SavedDietOut(
        id=row.id,
        name=row.name,
        created_at=row.created_at,
        active=row.active,
        plan=DietPlanOut.model_validate_json(row.plan_json),
    )


def save_diet(db: Session, name: str, plan: DietPlanOut, now: datetime) -> SavedDietOut:
    db.execute(update(DietPlan).values(active=False))
    row = DietPlan(
        name=name,
        kcal_target=plan.kcal_target,
        protein_target_g=plan.protein_target_g,
        diet=plan.diet,
        plan_json=plan.model_dump_json(),
        algo_version=plan.algo_version,
        created_at=now,
        active=True,
    )
    db.add(row)
    db.commit()
    return _diet_out(row)


def list_diets(db: Session) -> list[SavedDietOut]:
    return [_diet_out(r) for r in db.scalars(select(DietPlan).order_by(DietPlan.id.desc()))]


def delete_diet(db: Session, diet_id: int) -> None:
    row = db.get(DietPlan, diet_id)
    if row is None:
        raise NotFound(diet_id)
    db.delete(row)
    db.commit()
