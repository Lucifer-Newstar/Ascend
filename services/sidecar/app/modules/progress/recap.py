"""Weekly recap (v1.2): the facts behind the short recap video the app draws for a week.

Everything comes from what you logged that week (Monday to Sunday): sessions, sets, minutes,
lifting volume, personal records, XP, the boss, the streak and the days you logged meals or
did the check-in. It is body-neutral on purpose: no weight, no body numbers, no photos.
The video itself is drawn by the desktop app on this PC; nothing is uploaded.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.gamification import formulas
from app.modules.gamification import service as game
from app.modules.gamification.boss import tier_of
from app.modules.gamification.models import BossRaid, XpEvent
from app.modules.nutrition.models import Meal
from app.modules.progress.models import Checkin
from app.modules.progress.weekly import monday
from app.modules.workouts.activity_seed import TIME_BASED_SECTIONS
from app.modules.workouts.models import Workout

ALGO_VERSION = "recap-v1"
MAX_PRS = 5


class RecapPr(BaseModel):
    exercise: str
    weight_kg: float
    reps: int
    image: str | None = None


class RecapSection(BaseModel):
    section: str
    sets: int


class RecapBoss(BaseModel):
    name: str
    title: str
    tier: str
    defeated: bool


class RecapBestDay(BaseModel):
    day: date
    sets: int


class WeekRecap(BaseModel):
    week_start: date
    week_end: date
    complete: bool
    sessions: int
    active_days: int
    sets: int
    active_minutes: float
    volume_kg: float
    xp: int
    prs: list[RecapPr]
    sections: list[RecapSection]
    best_day: RecapBestDay | None
    boss: RecapBoss | None
    streak: int
    excused_days: int
    meal_days: int
    checkins: int
    level: int
    rank: str
    rank_title: str
    last_week_sessions: int
    last_week_sets: int
    headline: str
    version: str = ALGO_VERSION


def _workouts(db: Session, start: date, end: date) -> list[Workout]:
    """Every workout of the week. Sets count even when a session was never finished (like
    the weekly chart); `sessions` counts the finished ones."""
    return list(db.scalars(select(Workout).where(Workout.day >= start, Workout.day <= end)).all())


def headline(r: WeekRecap) -> str:
    """One kind line for the first slide; it never talks about the body."""
    if r.sessions == 0:
        return "A quiet week. Rest counts too; the next session starts the climb again."
    if r.boss is not None and r.boss.defeated:
        return f"You beat {r.boss.name} this week. That is what showing up looks like."
    if r.prs:
        word = "record" if len(r.prs) == 1 else "records"
        return f"{len(r.prs)} new personal {word} this week. You are getting stronger."
    if r.sessions > r.last_week_sessions and r.last_week_sessions > 0:
        return f"{r.sessions} sessions, up from {r.last_week_sessions} last week. Nice climb."
    word = "session" if r.sessions == 1 else "sessions"
    return f"{r.sessions} {word} logged. Every one of them counts."


def week_recap(db: Session, now: datetime, week: date | None = None) -> WeekRecap:
    start = monday(week or now.date())
    end = start + timedelta(days=6)
    today = now.date()
    as_of = min(today, end)
    workouts = _workouts(db, start, end)
    sets = [s for w in workouts for s in w.sets]
    lifting = [s for s in sets if s.exercise.section not in TIME_BASED_SECTIONS]
    minutes = sum(
        min(180.0, (w.finished_at - w.started_at).total_seconds() / 60)
        for w in workouts
        if w.finished_at is not None
    )
    per_day = Counter(w.day for w in workouts for _ in w.sets)
    best = max(per_day.items(), key=lambda kv: (kv[1], kv[0]), default=None)
    sections = Counter(s.exercise.section for s in sets)

    best_pr: dict[str, RecapPr] = {}
    score: dict[str, float] = {}
    for s in sets:
        if not s.is_pr:
            continue
        value = s.e1rm or s.weight_kg * max(1, s.reps)
        name = s.exercise.name
        if value > score.get(name, -1.0):
            score[name] = value
            best_pr[name] = RecapPr(
                exercise=name, weight_kg=s.weight_kg, reps=s.reps, image=s.exercise.image
            )
    prs = [best_pr[n] for n in sorted(score, key=lambda n: -score[n])][:MAX_PRS]

    raid = db.scalar(select(BossRaid).where(BossRaid.week_start == start))
    boss = (
        RecapBoss(
            name=raid.name,
            title=raid.title,
            tier=raid.tier or tier_of(raid.name),
            defeated=raid.defeated_at is not None,
        )
        if raid is not None
        else None
    )
    xp = int(
        db.scalar(
            select(func.coalesce(func.sum(XpEvent.amount), 0)).where(
                XpEvent.day >= start, XpEvent.day <= end
            )
        )
        or 0
    )
    total = int(
        db.scalar(select(func.coalesce(func.sum(XpEvent.amount), 0)).where(XpEvent.day <= end)) or 0
    )
    lvl = formulas.level_from_total(total)
    letter, title = formulas.rank_for_level(lvl.level)
    meal_days = int(
        db.scalar(
            select(func.count(func.distinct(Meal.day))).where(Meal.day >= start, Meal.day <= end)
        )
        or 0
    )
    checkins = int(
        db.scalar(select(func.count(Checkin.id)).where(Checkin.day >= start, Checkin.day <= end))
        or 0
    )
    prev = _workouts(db, start - timedelta(days=7), start - timedelta(days=1))
    streak = game.streak(db, as_of)
    out = WeekRecap(
        week_start=start,
        week_end=end,
        complete=today > end,
        sessions=sum(1 for w in workouts if w.finished_at is not None),
        active_days=len({w.day for w in workouts if w.sets}),
        sets=len(sets),
        active_minutes=round(minutes, 1),
        volume_kg=round(sum(s.weight_kg * s.reps for s in lifting), 1),
        xp=xp,
        prs=prs,
        sections=[RecapSection(section=k, sets=n) for k, n in sections.most_common()],
        best_day=RecapBestDay(day=best[0], sets=best[1]) if best else None,
        boss=boss,
        streak=streak.current,
        excused_days=streak.excused,
        meal_days=meal_days,
        checkins=checkins,
        level=lvl.level,
        rank=letter,
        rank_title=title,
        last_week_sessions=sum(1 for w in prev if w.finished_at is not None),
        last_week_sets=sum(len(w.sets) for w in prev),
        headline="",
    )
    out.headline = headline(out)
    return out
