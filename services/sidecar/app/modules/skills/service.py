"""Skill trees: evaluate progress from logged sets, store unlocks, plan training.

Side effects follow the event rules: this module stores its own unlocks and publishes
SkillStepUnlocked / SkillStepRevoked; gamification pays or reverses the XP.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.events import (
    EventBus,
    SetDeleted,
    SetLogged,
    SetUpdated,
    SkillStepRevoked,
    SkillStepUnlocked,
    WorkoutsImported,
)
from app.modules.skills import engine
from app.modules.skills.catalog import (
    SOURCES,
    Criterion,
    Skill,
    Step,
    all_exercise_names,
)
from app.modules.skills.custom import all_skills, custom_skills, skill_by_key
from app.modules.skills.models import SkillUnlock
from app.modules.skills.schemas import (
    CriterionOut,
    FeederOut,
    SkillDetail,
    SkillEtaOut,
    SkillSummary,
    SkillUnlockOut,
    SourceOut,
    StepOut,
    TrainOut,
)
from app.modules.workouts.equipment import allowed_for_profile, fits
from app.modules.workouts.models import Exercise, WorkoutSet
from app.modules.workouts.schemas import SkillLinkOut


class SkillNotFound(Exception):
    pass


# --- data access ----------------------------------------------------------------------


def exercises_by_name(db: Session) -> dict[str, Exercise]:
    names = all_exercise_names() | {n for k in custom_skills(db) for n in _skill_names(k)}
    rows = db.scalars(select(Exercise).where(Exercise.name.in_(names))).all()
    return {e.name: e for e in rows}


def load_records(
    db: Session,
    names: set[str],
    until: datetime,
    days: int = engine.WINDOW_DAYS,
    exclude: set[int] | None = None,
) -> list[engine.SetRecord]:
    since = until - timedelta(days=days + 1)
    stmt = (
        select(WorkoutSet, Exercise.name)
        .join(Exercise, Exercise.id == WorkoutSet.exercise_id)
        .where(
            Exercise.name.in_(names),
            WorkoutSet.performed_at >= since,
            WorkoutSet.performed_at <= until,
        )
    )
    out = []
    for ws, name in db.execute(stmt).all():
        if exclude and ws.id in exclude:
            continue
        out.append(
            engine.SetRecord(
                set_id=ws.id,
                exercise=name,
                performed_at=ws.performed_at,
                reps=ws.reps,
                duration_s=ws.duration_s,
                weight_kg=ws.weight_kg,
            )
        )
    return out


def _skill_names(skill: Skill) -> set[str]:
    names = set(skill.feeders) | {s.exercise for s in skill.steps}
    for step in skill.steps:
        names.update(c.exercise for c in step.unlock)
    return names


def stored(db: Session) -> dict[str, dict[str, SkillUnlock]]:
    out: dict[str, dict[str, SkillUnlock]] = {}
    for row in db.scalars(select(SkillUnlock)).all():
        out.setdefault(row.skill_key, {})[row.step_key] = row
    return out


def _step(skill: Skill, key: str) -> Step:
    return next(s for s in skill.steps if s.key == key)


# --- evaluation -------------------------------------------------------------------------


def evaluate(
    db: Session,
    bus: EventBus,
    now: datetime,
    skill_keys: set[str] | None = None,
    trigger_set_id: int | None = None,
    source: str = "log",
) -> list[SkillUnlock]:
    """Store every step that has become eligible (looping, since one unlock can open the
    next) and publish an event for each. Returns the new rows."""
    created: list[SkillUnlock] = []
    have_all = stored(db)
    for skill in all_skills(db):
        if skill_keys is not None and skill.key not in skill_keys:
            continue
        records = load_records(db, _skill_names(skill), now)
        have = have_all.get(skill.key, {})
        for _ in range(len(skill.steps)):
            res = engine.evaluate_skill(
                skill, records, {k: r.unlocked_at for k, r in have.items()}, now
            )
            eligible = [s for s in res.steps if s.eligible]
            if not eligible:
                break
            for s in eligible:
                evidence = sorted({i for c in s.criteria for i in c.evidence})
                row = SkillUnlock(
                    skill_key=skill.key,
                    step_key=s.step.key,
                    unlocked_at=now,
                    source=source,
                    trigger_set_id=trigger_set_id,
                    evidence_json=json.dumps(evidence),
                    engine_version=engine.ENGINE_VERSION,
                )
                db.add(row)
                db.flush()
                have[s.step.key] = row
                created.append(row)
                bus.publish(
                    db,
                    SkillStepUnlocked(
                        unlock_id=row.id,
                        skill_key=skill.key,
                        skill_name=skill.name,
                        step_key=s.step.key,
                        step_name=s.step.name,
                        at=now,
                        xp=0 if source == "import" else s.step.xp,
                        final=s.step.key == skill.steps[-1].key,
                        source=source,
                    ),
                )
    return created


def revalidate(db: Session, bus: EventBus, set_id: int, now: datetime, deleted: bool) -> int:
    """After a set was edited or deleted: drop unlocks that relied on it and no longer
    hold at the time they were earned (plus steps unlocked on top of them). Returns how
    many were revoked."""
    revoked = 0
    for skill_key, steps in stored(db).items():
        skill = skill_by_key(db, skill_key)
        if skill is None:
            continue
        doomed: set[str] = set()
        for step_key, row in steps.items():
            if set_id not in row.evidence:
                continue
            step = _step(skill, step_key)
            records = load_records(
                db, _skill_names(skill), row.unlocked_at, exclude={set_id} if deleted else None
            )
            still = all(
                engine.evaluate_criterion(c, records, row.unlocked_at).met for c in step.unlock
            )
            if not still:
                doomed.add(step_key)
        # Anything that required a revoked step goes too.
        changed = bool(doomed)
        while changed:
            changed = False
            for st in skill.steps:
                if st.key in steps and st.key not in doomed:
                    if any(r in doomed for r in skill.requires_of(st)):
                        doomed.add(st.key)
                        changed = True
        for key in doomed:
            row = steps[key]
            bus.publish(
                db,
                SkillStepRevoked(unlock_id=row.id, skill_key=skill_key, step_key=key, at=now),
            )
            db.delete(row)
            revoked += 1
    db.flush()
    return revoked


# --- read models ------------------------------------------------------------------------


def _criterion_out(c: engine.CriterionResult, ex: dict[str, Exercise]) -> CriterionOut:
    crit = c.criterion
    e = ex.get(crit.exercise)
    return CriterionOut(
        text=crit.describe(),
        exercise=crit.exercise,
        exercise_id=e.id if e else None,
        sets=crit.sets,
        target=crit.target,
        unit="s" if crit.is_hold else "reps",
        added_kg=crit.added_kg,
        per_side=crit.per_side,
        best_value=c.best_value,
        best_score=round(c.best_score, 3),
        sessions_met=c.sessions_met,
        sessions_needed=engine.CONFIRM_SESSIONS,
        pct=c.pct,
        met=c.met,
        ignored_sets=c.ignored_sets,
    )


def _evaluate_one(
    db: Session, skill: Skill, now: datetime, ex: dict[str, Exercise]
) -> engine.SkillResult:
    records = load_records(db, _skill_names(skill), now, days=max(engine.WINDOW_DAYS, 28))
    have = stored(db).get(skill.key, {})
    return engine.evaluate_skill(skill, records, {k: r.unlocked_at for k, r in have.items()}, now)


def _summary(res: engine.SkillResult) -> SkillSummary:
    skill = res.skill
    return SkillSummary(
        key=skill.key,
        name=skill.name,
        family=skill.family,
        summary=skill.summary,
        stretch=skill.stretch,
        current_step=res.current.key if res.current else None,
        current_step_name=res.current.name if res.current else None,
        next_step=res.next.step.key if res.next else None,
        next_step_name=res.next.step.name if res.next else None,
        pct_to_next=res.next.pct if res.next else None,
        steps_unlocked=sum(1 for s in res.steps if s.status == "unlocked"),
        steps_total=len(skill.steps),
        acquired=res.acquired,
        last_trained=res.last_trained,
        sessions_28d=res.sessions_28d,
        rusty=res.rusty,
        custom="custom" in skill.tags,
    )


def summaries(db: Session, now: datetime) -> list[SkillSummary]:
    ex = exercises_by_name(db)
    return [_summary(_evaluate_one(db, s, now, ex)) for s in all_skills(db)]


def detail(db: Session, key: str, now: datetime) -> SkillDetail:
    skill = skill_by_key(db, key)
    if skill is None:
        raise SkillNotFound(f"unknown skill '{key}'")
    ex = exercises_by_name(db)
    res = _evaluate_one(db, skill, now, ex)
    month_ago = now - timedelta(days=28)
    feeder_records = load_records(db, set(skill.feeders), now, days=28)
    feeders = [
        FeederOut(
            exercise_id=ex[n].id if n in ex else None,
            name=n,
            measure=ex[n].measure if n in ex else "reps",
            sets_28d=sum(
                1 for r in feeder_records if r.exercise == n and r.performed_at >= month_ago
            ),
        )
        for n in skill.feeders
    ]
    eta = res.eta
    return SkillDetail(
        **_summary(res).model_dump(),
        steps=[
            StepOut(
                key=s.step.key,
                name=s.step.name,
                exercise=s.step.exercise,
                exercise_id=ex[s.step.exercise].id if s.step.exercise in ex else None,
                measure=ex[s.step.exercise].measure if s.step.exercise in ex else "reps",
                status=s.status,
                pct=s.pct,
                unlocked_at=s.unlocked_at if s.step.unlock else None,
                criteria=[_criterion_out(c, ex) for c in s.criteria],
                requires=list(skill.requires_of(s.step)),
                xp=s.step.xp,
                uncertain=s.step.uncertain,
                note=s.step.note,
            )
            for s in res.steps
        ],
        feeders=feeders,
        eta=SkillEtaOut(
            days=eta.days,
            date=(now + timedelta(days=math.ceil(eta.days))).date()
            if eta.days is not None
            else None,
            reason=eta.reason,
        ),
        sources=[SourceOut(key=k, title=SOURCES[k][0], url=SOURCES[k][1]) for k in skill.sources],
        engine_version=engine.ENGINE_VERSION,
    )


def unlock_out(db: Session, row: SkillUnlock) -> SkillUnlockOut:
    from app.modules.gamification import service as game

    skill = skill_by_key(db, row.skill_key)
    if skill is None:
        raise SkillNotFound(f"unknown skill '{row.skill_key}'")
    step = _step(skill, row.step_key)
    idx = skill.steps.index(step)
    nxt = skill.steps[idx + 1].name if idx + 1 < len(skill.steps) else None
    return SkillUnlockOut(
        id=row.id,
        skill_key=skill.key,
        skill_name=skill.name,
        step_key=step.key,
        step_name=step.name,
        unlocked_at=row.unlocked_at,
        xp=game.xp_for_refs(db, ("skill",), row.id),
        final=step.key == skill.steps[-1].key,
        next_step_name=nxt,
        source=row.source,
    )


def unlocks_for_set(db: Session, set_id: int) -> list[SkillUnlockOut]:
    rows = db.scalars(
        select(SkillUnlock).where(SkillUnlock.trigger_set_id == set_id).order_by(SkillUnlock.id)
    ).all()
    return [unlock_out(db, r) for r in rows]


def recent_unlocks(db: Session, limit: int = 10) -> list[SkillUnlockOut]:
    rows = db.scalars(
        select(SkillUnlock).order_by(SkillUnlock.unlocked_at.desc(), SkillUnlock.id.desc())
    ).all()
    return [unlock_out(db, r) for r in rows[:limit] if skill_by_key(db, r.skill_key) is not None]


def links_for_exercise(db: Session, e: Exercise) -> list[SkillLinkOut]:
    """Skill trees an exercise belongs to (as a step) or feeds (as a feeder)."""
    out: list[SkillLinkOut] = []
    for skill in all_skills(db):
        steps = [s for s in skill.steps if s.exercise == e.name]
        if steps:
            out.append(
                SkillLinkOut(
                    skill_key=skill.key, skill_name=skill.name, step_name=steps[0].name, role="step"
                )
            )
        elif e.name in skill.feeders or any(
            c.exercise == e.name for s in skill.steps for c in s.unlock
        ):
            out.append(SkillLinkOut(skill_key=skill.key, skill_name=skill.name, role="feeder"))
    return out


# --- "train this skill" --------------------------------------------------------------------


def _threshold(c: Criterion, best: int | None) -> int:
    """A quest target the user can hit today: their best so far, capped at the goal."""
    if best is None:
        return max(1, math.ceil(c.target * 0.5))
    return max(1, min(c.target, best))


def train(db: Session, bus: EventBus, key: str, now: datetime) -> TrainOut:
    from app.modules.gamification import service as game

    skill = skill_by_key(db, key)
    if skill is None:
        raise SkillNotFound(f"unknown skill '{key}'")
    ex = exercises_by_name(db)
    res = _evaluate_one(db, skill, now, ex)
    # Never suggest an exercise the user said they cannot do (no bar, no rings...).
    allowed = allowed_for_profile(db)
    specs: list[game.SkillQuestSpec] = []
    target_step = res.next or next((s for s in res.steps if s.step.unlock), res.steps[-1])
    open_crits = [c for c in target_step.criteria if not c.met] or target_step.criteria
    for c in open_crits[:2]:
        e = ex.get(c.criterion.exercise)
        if e is None or not fits(e.equipment, allowed):
            continue
        n = _threshold(c.criterion, c.best_value)
        unit = "s" if c.criterion.is_hold else " reps"
        specs.append(
            game.SkillQuestSpec(
                code=f"skill:{skill.key}:{e.id}",
                title=f"{skill.name}: {c.criterion.sets}\u00d7{n}{unit} {e.name}",
                detail=f"Working toward {target_step.step.name} ({c.criterion.describe()}).",
                metric=f"ex:{e.id}:{'hold' if c.criterion.is_hold else 'reps'}:{n}",
                target=c.criterion.sets,
            )
        )
    used = {s.code for s in specs}
    for name in skill.feeders:
        e = ex.get(name)
        if e is None or f"skill:{skill.key}:{e.id}" in used or not fits(e.equipment, allowed):
            continue
        hold = e.measure == "hold"
        n = (e.rep_low or (10 if hold else 6)) if e.measure in ("reps", "hold") else 1
        specs.append(
            game.SkillQuestSpec(
                code=f"skill:{skill.key}:{e.id}",
                title=f"{skill.name} feeder: 3\u00d7{n}{'s' if hold else ' reps'} {e.name}",
                detail=f"Builds strength for {skill.name}.",
                metric=f"ex:{e.id}:{'hold' if hold else 'reps'}:{n}",
                target=3,
            )
        )
        break
    added, already, items = game.add_skill_items(db, bus, now, specs)
    if not specs:
        msg = f"None of {skill.name}'s exercises fit the equipment in your profile."
    elif added:
        msg = f"Added {added} {skill.name} item{'s' if added != 1 else ''} to today's quest."
    elif already:
        msg = f"{skill.name} is already in today's quest."
    else:
        msg = f"Today's quest already has {game.MAX_SKILL_ITEMS_PER_DAY} skill items."
    return TrainOut(
        skill_key=skill.key, added=added, already_planned=already, items=items, message=msg
    )


# --- event handlers ------------------------------------------------------------------------


def register(bus: EventBus) -> None:
    from app.modules.workouts import service as workouts

    workouts.register_skill_linker(links_for_exercise)
    names = all_exercise_names()

    def keys_for(db: Session, exercise_id: int) -> set[str] | None:
        e = db.get(Exercise, exercise_id)
        if e is None:
            return None
        if e.name not in names and not any(e.name in _skill_names(k) for k in custom_skills(db)):
            return None
        return {s.key for s in all_skills(db) if e.name in _skill_names(s)}

    def on_logged(db: Session, e: SetLogged) -> None:
        keys = keys_for(db, e.exercise_id)
        if keys:
            evaluate(db, bus, e.performed_at, keys, trigger_set_id=e.set_id)

    def on_updated(db: Session, e: SetUpdated) -> None:
        now = bus.clock()
        revalidate(db, bus, e.set_id, now, deleted=False)
        keys = keys_for(db, e.exercise_id)
        if keys:
            evaluate(db, bus, now, keys, trigger_set_id=e.set_id, source="edit")

    def on_deleted(db: Session, e: SetDeleted) -> None:
        revalidate(db, bus, e.set_id, bus.clock(), deleted=True)

    def on_imported(db: Session, e: WorkoutsImported) -> None:
        evaluate(db, bus, bus.clock(), source="import")

    bus.subscribe(SetLogged, on_logged)
    bus.subscribe(SetUpdated, on_updated)
    bus.subscribe(SetDeleted, on_deleted)
    bus.subscribe(WorkoutsImported, on_imported)
