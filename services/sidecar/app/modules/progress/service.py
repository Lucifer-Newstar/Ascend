"""Profile, settings and muscle-state queries + the SetLogged -> muscle load handler."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import cast

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.events import EventBus, SetDeleted, SetImported, SetLogged, SetUpdated
from app.modules.nutrition import tdee as tdee_engine
from app.modules.progress import energy, muscle_load
from app.modules.progress.models import MuscleLoadEvent, Profile, Setting
from app.modules.progress.schemas import (
    EnergyTargets,
    ProfileIn,
    SettingsIn,
    SettingsOut,
    Theme,
    Units,
)
from app.modules.workouts.activity_seed import TIME_BASED_SECTIONS
from app.modules.workouts.models import Exercise, Workout

PROFILE_ID = 1


def get_profile(db: Session) -> Profile | None:
    return db.get(Profile, PROFILE_ID)


def upsert_profile(db: Session, data: ProfileIn) -> Profile:
    profile = get_profile(db)
    if profile is None:
        profile = Profile(id=PROFILE_ID, **data.model_dump())
        db.add(profile)
    else:
        for k, v in data.model_dump().items():
            setattr(profile, k, v)
    db.flush()
    return profile


def energy_for(profile: Profile) -> EnergyTargets:
    """Estimated BMR, TDEE (kcal/day) and calorie/protein targets for a profile."""
    sex = cast(tdee_engine.Sex, profile.sex)
    goal = cast(tdee_engine.Goal, profile.goal)
    activity = cast(tdee_engine.Activity, profile.activity)
    bmr = tdee_engine.bmr_mifflin_st_jeor(sex, profile.weight_kg, profile.height_cm, profile.age)
    total = tdee_engine.tdee(bmr, activity)
    return EnergyTargets(
        bmr=round(bmr),
        tdee=round(total),
        kcal_target=tdee_engine.calorie_target(total, goal),
        protein_target_g=tdee_engine.protein_target_g(profile.weight_kg, goal),
        formula_version=tdee_engine.FORMULA_VERSION,
    )


# --- settings --------------------------------------------------------------


def get_setting(db: Session, key: str, default: str) -> str:
    row = db.get(Setting, key)
    return row.value if row else default


def set_setting(db: Session, key: str, value: str) -> None:
    row = db.get(Setting, key)
    if row is None:
        db.add(Setting(key=key, value=value))
    else:
        row.value = value


def ai_enabled(db: Session) -> bool:
    return get_setting(db, "ai_enabled", "true") == "true"


def read_settings(db: Session) -> SettingsOut:
    return SettingsOut(
        ai_enabled=ai_enabled(db),
        units=cast(Units, get_setting(db, "units", "metric")),
        theme=cast(Theme, get_setting(db, "theme", "dark")),
        sessions_per_week=int(get_setting(db, "sessions_per_week", "3")),
    )


def update_settings(db: Session, data: SettingsIn) -> SettingsOut:
    changes = data.model_dump(exclude_none=True)
    for key, value in changes.items():
        if isinstance(value, bool):
            value = "true" if value else "false"
        set_setting(db, key, str(value))
    db.flush()
    return read_settings(db)


# --- muscle load ------------------------------------------------------------


def muscle_states(db: Session, now: datetime) -> list[muscle_load.MuscleState]:
    since = now - timedelta(days=28)
    rows = db.scalars(select(MuscleLoadEvent).where(MuscleLoadEvent.at >= since)).all()
    contribs = [muscle_load.Contribution(r.muscle, r.es, r.at) for r in rows]
    return muscle_load.compute_states(contribs, now)


def on_set_logged(db: Session, event: SetLogged | SetUpdated | SetImported) -> None:
    """Event handler: turn one logged set into per-muscle effective-set rows."""
    exercise = db.get(Exercise, event.exercise_id)
    if exercise is None:
        return
    if event.duration_s and exercise.section in TIME_BASED_SECTIONS:
        base = muscle_load.time_effective_sets(event.duration_s, event.rpe)
        version = muscle_load.TIME_FORMULA_VERSION
    else:
        base = muscle_load.effort(event.rpe)
        version = muscle_load.FORMULA_VERSION
    for link in exercise.muscles:
        es = round(link.weight * base, 3)
        if es <= 0:
            continue
        db.add(
            MuscleLoadEvent(
                set_id=event.set_id,
                muscle=link.muscle,
                es=es,
                at=event.performed_at,
                formula_version=version,
            )
        )


def on_set_updated(db: Session, event: SetUpdated) -> None:
    """Replace the set's muscle rows: effort (RPE) may have changed."""
    db.execute(delete(MuscleLoadEvent).where(MuscleLoadEvent.set_id == event.set_id))
    on_set_logged(db, event)


def on_set_deleted(db: Session, event: SetDeleted) -> None:
    db.execute(delete(MuscleLoadEvent).where(MuscleLoadEvent.set_id == event.set_id))


def register(bus: EventBus) -> None:
    bus.subscribe(SetLogged, on_set_logged)
    bus.subscribe(SetUpdated, on_set_updated)
    bus.subscribe(SetDeleted, on_set_deleted)
    bus.subscribe(SetImported, on_set_logged)


def workout_burn(w: Workout, weight_kg: float) -> float:
    """Estimated kcal for one session (see energy.workout_kcal)."""
    duration = (w.finished_at - w.started_at).total_seconds() / 60 if w.finished_at else None
    timed = [
        (s.exercise.met, s.duration_s)
        for s in w.sets
        if s.duration_s and s.exercise.met and s.exercise.section in TIME_BASED_SECTIONS
    ]
    lifting = sum(1 for s in w.sets if s.exercise.section not in TIME_BASED_SECTIONS)
    return energy.workout_kcal(duration, lifting, timed, weight_kg)
