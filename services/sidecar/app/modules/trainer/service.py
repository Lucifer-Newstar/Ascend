"""Trainer service: the watcher's feed, the first-run state, and the facts it reads."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.modules.gamification import service as game
from app.modules.gamification.models import BossRaid
from app.modules.intelligence import progression_service
from app.modules.nutrition.models import Meal
from app.modules.progress import service as progress
from app.modules.progress.models import BodyMetric
from app.modules.skills.catalog import SKILL_BY_KEY
from app.modules.skills.models import SkillUnlock
from app.modules.trainer import monitor
from app.modules.trainer.models import TrainerMessage
from app.modules.trainer.schemas import FeedMessage, FeedOut, TrainerState
from app.modules.workouts import programs_service
from app.modules.workouts import service as workouts
from app.modules.workouts.models import Workout

TRAINERS = ("iskra", "vera", "kai", "dario")
FEED_LIMIT = 30


def _step_name(skill_key: str, step_key: str) -> tuple[str, str]:
    skill = SKILL_BY_KEY.get(skill_key)
    if skill is None:
        return skill_key, step_key
    step = next((s for s in skill.steps if s.key == step_key), None)
    return skill.name, step.name if step else step_key


def photos_last_day(db: Session) -> tuple[bool, datetime | None]:
    """(photos supported, the newest progress photo's date). Filled in by the photos module."""
    return False, None


def facts(db: Session, now: datetime) -> monitor.Facts:
    today = now.date()
    p = progress.get_profile(db)
    last = db.scalar(select(func.max(Workout.day)))
    total = db.scalar(select(func.count(Workout.id))) or 0
    prs = [
        (r.set_id, r.exercise, round(r.value, 1), r.achieved_at.date())
        for r in workouts.personal_records(db)
        if (today - r.achieved_at.date()).days <= 3
    ]
    over = [s.label.lower() for s in progress.muscle_states(db, now) if s.status == "over"]
    stalled = [e.name for e, _ in progression_service.stalled_lifts(db, now)]
    weights = [
        (m.measured_at.date(), m.weight_kg)
        for m in db.scalars(
            select(BodyMetric)
            .where(BodyMetric.measured_at >= now - timedelta(days=60))
            .order_by(BodyMetric.measured_at)
        )
    ]
    unlocks = []
    for u in db.scalars(
        select(SkillUnlock).where(SkillUnlock.unlocked_at >= now - timedelta(days=3))
    ):
        skill, step = _step_name(u.skill_key, u.step_key)
        unlocks.append((u.id, skill, step, u.unlocked_at.date()))
    week = today - timedelta(days=today.weekday())
    raid = db.scalars(
        select(BossRaid).where(BossRaid.week_start == week, BossRaid.defeated_at.is_not(None))
    ).first()
    plan = programs_service.plan(db, now)
    program_done = None
    if plan is not None and plan.sessions_done and plan.days_per_week:
        block = plan.days_per_week * 4
        if plan.sessions_done % block == 0:
            program_done = (plan.name, plan.sessions_done)
    supported, last_photo = photos_last_day(db)
    return monitor.Facts(
        today=today,
        has_profile=p is not None,
        profile_since=p.created_at.date() if p is not None and p.created_at else None,
        sessions_per_week=int(progress.get_setting(db, "sessions_per_week", "3")),
        last_workout=last,
        workouts_total=int(total),
        streak=game.streak(db, today).current,
        prs=prs,
        over_muscles=over,
        stalled=stalled,
        weights=weights,
        goal=p.goal if p is not None else None,
        unlocks=unlocks,
        boss=(raid.week_start, raid.name, raid.title) if raid else None,
        photos_supported=supported,
        last_photo=last_photo.date() if last_photo else None,
        program_done=program_done,
    )


def scan(db: Session, now: datetime) -> int:
    """Run the watcher and store new notices. Returns how many were new."""
    if progress.get_profile(db) is None:
        return 0
    known = set(db.scalars(select(TrainerMessage.key)))
    new = 0
    for n in monitor.watch(facts(db, now)):
        if n.key in known:
            continue
        db.add(
            TrainerMessage(
                key=n.key,
                kind=n.kind,
                mood=n.mood,
                text=n.text,
                action_kind=n.action_kind,
                action_target=n.action_target,
                share_json=json.dumps(n.share) if n.share else None,
                created_at=now,
            )
        )
        known.add(n.key)
        new += 1
    db.commit()
    return new


def feed(db: Session, now: datetime) -> FeedOut:
    scan(db, now)
    rows = db.scalars(
        select(TrainerMessage).order_by(TrainerMessage.id.desc()).limit(FEED_LIMIT)
    ).all()
    unread = db.scalar(
        select(func.count(TrainerMessage.id)).where(TrainerMessage.read_at.is_(None))
    )
    return FeedOut(
        messages=[
            FeedMessage(
                id=r.id,
                kind=r.kind,
                mood=r.mood,  # type: ignore[arg-type]
                text=r.text,
                action_kind=r.action_kind,
                action_target=r.action_target,
                share=r.share,
                created_at=r.created_at,
                read=r.read_at is not None,
            )
            for r in rows
        ],
        unread=int(unread or 0),
        algo_version=monitor.WATCH_VERSION,
    )


def mark_read(db: Session, ids: list[int] | None, now: datetime) -> None:
    stmt = update(TrainerMessage).where(TrainerMessage.read_at.is_(None)).values(read_at=now)
    if ids is not None:
        stmt = stmt.where(TrainerMessage.id.in_(ids))
    db.execute(stmt)
    db.commit()


def has_history(db: Session) -> bool:
    return any(
        db.scalar(select(func.count()).select_from(model)) for model in (Workout, Meal, BodyMetric)
    )


def tours_done(db: Session) -> list[str]:
    raw = progress.get_setting(db, "tours_done", "")
    return [t for t in raw.split(",") if t]


def state(db: Session) -> TrainerState:
    p = progress.get_profile(db)
    # A database from before 1.1 has a profile but no "onboarded" flag: it counts as
    # onboarded only once the user has seen the 1.1 welcome (which offers "start fresh").
    trainer_id = progress.get_setting(db, "trainer_id", "iskra")
    return TrainerState(
        onboarded=progress.get_setting(db, "onboarded", "false") == "true",
        has_profile=p is not None,
        has_history=has_history(db),
        demo_data=bool(progress.get_setting(db, "demo_seed", "")),
        trainer_id=trainer_id if trainer_id in TRAINERS else "iskra",  # type: ignore[arg-type]
        tours_done=tours_done(db),
    )


def update_state(db: Session, onboarded: bool | None, tour_done: str | None) -> TrainerState:
    if onboarded is not None:
        progress.set_setting(db, "onboarded", "true" if onboarded else "false")
        if onboarded:
            progress.set_setting(db, "demo_seed", "")
    if tour_done:
        done = tours_done(db)
        if tour_done not in done:
            progress.set_setting(db, "tours_done", ",".join([*done, tour_done])[:250])
    db.commit()
    return state(db)
