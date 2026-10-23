"""Profile, settings and muscle-state queries + the SetLogged -> muscle dose handler."""

from __future__ import annotations

import time
from datetime import datetime
from typing import cast

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.events import EventBus, SetDeleted, SetImported, SetLogged, SetUpdated
from app.modules.intelligence import doses, recovery, recovery_service
from app.modules.nutrition import tdee as tdee_engine
from app.modules.progress import energy, muscle_load
from app.modules.progress.models import MuscleLoadEvent, Profile, Setting
from app.modules.progress.schemas import (
    AvatarLook,
    BackgroundArt,
    EnergyTargets,
    ProfileIn,
    SettingsIn,
    SettingsOut,
    Theme,
    TrainerId,
    Units,
)
from app.modules.workouts.activity_seed import TIME_BASED_SECTIONS
from app.modules.workouts.models import Exercise, Workout, WorkoutSet

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


_AI_PROBE_TTL_S = 300.0
_ai_probe: tuple[float, bool] | None = None


def local_ai_installed() -> bool:
    """Whether a local model server answers on this PC with at least one model pulled.

    Probed once every few minutes (a refused localhost connection returns at once), so a
    settings read never waits on it for long."""
    global _ai_probe
    now = time.monotonic()
    if _ai_probe is not None and now - _ai_probe[0] < _AI_PROBE_TTL_S:
        return _ai_probe[1]
    from app.core.config import load_settings
    from app.modules.coach import ollama

    try:
        version, models = ollama.server_info(load_settings().ollama_host, timeout=0.5)
        installed = version is not None and len(models) > 0
    except Exception:  # noqa: BLE001 - any failure means "not installed" here
        installed = False
    _ai_probe = (now, installed)
    return installed


def ai_enabled(db: Session) -> bool:
    """The user's switch when they set it; otherwise on only when local AI is installed
    (v1.2: the app is rules-first, so a PC without a local model starts with AI off)."""
    row = db.get(Setting, "ai_enabled")
    if row is not None:
        return row.value == "true"
    return local_ai_installed()


def online_lookup(db: Session) -> bool:
    return get_setting(db, "online_lookup", "false") == "true"


def read_settings(db: Session) -> SettingsOut:
    return SettingsOut(
        ai_enabled=ai_enabled(db),
        units=cast(Units, get_setting(db, "units", "metric")),
        theme=cast(Theme, get_setting(db, "theme", "shadow")),
        sessions_per_week=int(get_setting(db, "sessions_per_week", "3")),
        reduce_motion=get_setting(db, "reduce_motion", "false") == "true",
        online_lookup=online_lookup(db),
        trainer=get_setting(db, "trainer", "true") == "true",
        trainer_id=cast(TrainerId, _trainer_id(get_setting(db, "trainer_id", "iskra"))),
        hide_calories=get_setting(db, "hide_calories", "false") == "true",
        photo_feedback=get_setting(db, "photo_feedback", "false") == "true" and not _minor(db),
        background_art=cast(BackgroundArt, _art(get_setting(db, "background_art", "on"))),
        avatar=cast(AvatarLook, _avatar(db, get_setting(db, "avatar", ""))),
        outfit=get_setting(db, "outfit", ""),
        relic=get_setting(db, "relic", ""),
        pet=get_setting(db, "pet", ""),
        weapon=get_setting(db, "weapon", ""),
        themed_cosmetics=get_setting(db, "themed_cosmetics", "true") == "true",
    )


def _avatar(db: Session, value: str) -> str:
    """The avatar look you picked, else the one matching your profile, else male."""
    if value in ("male", "female"):
        return value
    p = get_profile(db)
    return "female" if p is not None and p.sex == "female" else "male"


def _art(value: str) -> str:
    return value if value in ("on", "dim", "off") else "on"


def _minor(db: Session) -> bool:
    p = get_profile(db)
    return p is not None and p.age < 18


def _trainer_id(value: str) -> str:
    return value if value in ("iskra", "vera", "kai", "dario") else "iskra"


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
    """Every muscle's status from the recovery-v2 engine (personal factors, today's check-in).
    The MuscleState shape is unchanged, so quests, deload and the coach read it as before."""
    return [
        muscle_load.MuscleState(
            key=s.key,
            label=s.label,
            group=s.group,
            map_slug=s.map_slug,
            status=s.status,
            es_7d=s.es_7d,
            weekly_low=s.weekly_low,
            weekly_high=s.weekly_high,
            fatigue=s.fatigue,
            readiness=s.readiness,
            ready_at=s.ready_at,
        )
        for s in recovery_service.states(db, now)
    ]


def _e1rm_before(db: Session, exercise_id: int, at: datetime, set_id: int) -> float | None:
    return db.scalar(
        select(func.max(WorkoutSet.e1rm)).where(
            WorkoutSet.exercise_id == exercise_id,
            WorkoutSet.performed_at < at,
            WorkoutSet.id != set_id,
        )
    )


def on_set_logged(db: Session, event: SetLogged | SetUpdated | SetImported) -> None:
    """Event handler: turn one logged set into per-muscle recovery-v2 dose rows."""
    exercise = db.get(Exercise, event.exercise_id)
    if exercise is None:
        return
    pairs = doses.set_dose(
        muscles={link.muscle: link.weight for link in exercise.muscles},
        at=event.performed_at,
        measure=exercise.measure,
        section=exercise.section,
        reps=event.reps,
        weight_kg=event.weight_kg,
        rpe=event.rpe,
        duration_s=event.duration_s,
        e1rm_ref=_e1rm_before(db, event.exercise_id, event.performed_at, event.set_id),
    )
    for muscle, es in pairs:
        db.add(
            MuscleLoadEvent(
                set_id=event.set_id,
                muscle=muscle,
                es=es,
                at=event.performed_at,
                formula_version=recovery.ALGO_VERSION,
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
