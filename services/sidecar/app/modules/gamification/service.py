"""Gamification use-cases + event handlers.

Writes happen only in response to events (or an explicit quest check-off);
reads of other modules go through their query functions.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.events import (
    CheckinRecorded,
    EventBus,
    MealLogged,
    QuestCompleted,
    SetDeleted,
    SetLogged,
    SetUpdated,
    SkillStepRevoked,
    SkillStepUnlocked,
    WorkoutLogged,
)
from app.modules.gamification import formulas as f
from app.modules.gamification.models import QuestItem, XpEvent
from app.modules.gamification.quests import (
    GENERATOR_VERSION,
    TRAINING_XP,
    ExerciseRef,
    QuestItemSpec,
    Tuning,
    generate_daily_quest,
)
from app.modules.gamification.schemas import (
    CalmStreakOut,
    GameSummary,
    QuestItemOut,
    StreakOut,
    XpOut,
)
from app.modules.gamification.streaks import (
    StreakState,
    compute_streak,
    next_milestone,
    week_start,
    weeks_in_a_row,
)


class QuestNotFound(Exception):
    pass


# --- XP ledger ---------------------------------------------------------------


def earned_on(db: Session, day: date) -> int:
    return int(
        db.scalar(select(func.coalesce(func.sum(XpEvent.amount), 0)).where(XpEvent.day == day)) or 0
    )


def total_xp(db: Session) -> int:
    return int(db.scalar(select(func.coalesce(func.sum(XpEvent.amount), 0))) or 0)


def award(
    db: Session, at: datetime, source: str, ref_id: int | None, amount: int, note: str = ""
) -> int:
    """Append an XP event, clipped by the daily cap. Returns the XP actually granted."""
    granted = f.apply_daily_cap(amount, earned_on(db, at.date()))
    if granted > 0:
        db.add(
            XpEvent(
                day=at.date(),
                at=at,
                source=source,
                ref_id=ref_id,
                amount=granted,
                formula_version=f.FORMULA_VERSION,
                note=note,
            )
        )
        db.flush()
    return granted


def _grant_day(db: Session, sources: Iterable[str], ref_id: int) -> date | None:
    """The day the XP for these refs was first granted."""
    return db.scalar(
        select(func.min(XpEvent.day)).where(
            XpEvent.source.in_(list(sources)), XpEvent.ref_id == ref_id, XpEvent.amount > 0
        )
    )


def reverse(
    db: Session,
    at: datetime,
    sources: Iterable[str],
    ref_id: int,
    note: str,
    amount: int | None = None,
) -> int:
    """Append a correction that cancels the XP paid for these refs (all of it, or
    `amount`; never below zero overall for them). The ledger stays append-only: history
    shows the grant and the reversal. Returns the XP taken back.

    The correction is booked on the day of the original grant, not today: booked today it
    would lower today's total and so free room under today's daily cap (review L8)."""
    sources = list(sources)
    paid = xp_for_refs(db, sources, ref_id)
    take = paid if amount is None else min(paid, amount)
    if take <= 0:
        return 0
    db.add(
        XpEvent(
            day=_grant_day(db, sources, ref_id) or at.date(),
            at=at,
            source=sources[0],
            ref_id=ref_id,
            amount=-take,
            formula_version=f.FORMULA_VERSION,
            note=note[:120],
        )
    )
    db.flush()
    return take


def xp_for_refs(db: Session, sources: Iterable[str], ref_id: int) -> int:
    stmt = select(func.coalesce(func.sum(XpEvent.amount), 0)).where(
        XpEvent.source.in_(list(sources)), XpEvent.ref_id == ref_id
    )
    return int(db.scalar(stmt) or 0)


# --- streaks -----------------------------------------------------------------


def active_days(db: Session) -> set[date]:
    """Days that keep the streak (v1.3, review S2): training days only, a finished workout
    or at least one logged set. Meals, weigh-ins and quest ticks still earn XP and quest
    progress, but logging a meal no longer keeps a training streak alive."""
    from app.modules.workouts.models import Workout, WorkoutSet

    days = set(db.scalars(select(Workout.day).where(Workout.finished_at.is_not(None))).all())
    days |= set(
        db.scalars(
            select(Workout.day).join(WorkoutSet, WorkoutSet.workout_id == Workout.id).distinct()
        ).all()
    )
    return days


def planned_rest_days(db: Session, today: date) -> set[date]:
    """Days the followed program planned as rest (review S1): the weekdays none of its
    days falls on, for each stretch a program was followed. Neutral for the streak."""
    from app.modules.workouts import programs_service
    from app.modules.workouts.models import PlanEnrollment

    out: set[date] = set()
    for e in db.scalars(select(PlanEnrollment).order_by(PlanEnrollment.id)).all():
        try:
            p = programs_service.get_program(db, e.program_key)
        except Exception:  # a broken custom program must never break the streak
            p = None
        if p is None or not p.days:
            continue
        training = {d.weekday % 7 for d in p.days}
        if len(training) >= 7:
            continue
        end = e.ended_at.date() if e.ended_at is not None else today
        day = e.started_on
        while day <= min(end, today):
            if day.weekday() not in training:
                out.add(day)
            day += timedelta(days=1)
    # v1.4 (schedule-v1): from the day the user picked their own training days, those
    # decide which weekdays are planned rest, week by week.
    from app.modules.schedule import service as schedule

    first = schedule.since(db)
    if first is not None and first <= today:
        own = schedule.scheduled_rest_days(db, first, today) or set()
        out = {d for d in out if d < first} | own
    return out


def is_rest_day(db: Session, day: date) -> bool:
    return day in planned_rest_days(db, day)


def streak_reasons(db: Session) -> dict[date, date]:
    """Missed day -> the day its reason was given."""
    from app.modules.gamification.models import StreakReason

    return {r.day: r.given_on for r in db.scalars(select(StreakReason)).all()}


def streak(db: Session, today: date) -> StreakState:
    return compute_streak(active_days(db), today, streak_reasons(db), planned_rest_days(db, today))


def calm_days(db: Session) -> set[date]:
    """Days with at least one logged meditation set."""
    from app.modules.workouts.models import Exercise, Workout, WorkoutSet

    stmt = (
        select(Workout.day)
        .join(WorkoutSet, WorkoutSet.workout_id == Workout.id)
        .join(Exercise, Exercise.id == WorkoutSet.exercise_id)
        .where(Exercise.section == "meditation")
    )
    return set(db.scalars(stmt).all())


def calm_streak(db: Session, today: date) -> StreakState:
    return compute_streak(calm_days(db), today, streak_reasons(db))


# --- quests --------------------------------------------------------------------


def _exercise_refs(db: Session) -> list[ExerciseRef]:
    """Exercises a quest may suggest: ASCEND's core list, the user's own (custom)
    exercises and any other library exercise they have actually logged; never archived
    ones. (Suggesting one of 873 imported library entries at random reads as noise.)
    Only exercises that fit the equipment the user said they have."""
    from app.modules.workouts.equipment import allowed_for_profile, fits_exercise
    from app.modules.workouts.models import Exercise, WorkoutSet

    allowed = allowed_for_profile(db)
    logged = select(WorkoutSet.exercise_id).distinct()
    stmt = select(Exercise).where(
        Exercise.archived.is_(False),
        (Exercise.source.in_(("ascend", "custom"))) | (Exercise.id.in_(logged)),
    )
    return [
        ExerciseRef(e.id, e.name, {m.muscle: m.weight for m in e.muscles})
        for e in db.scalars(stmt).all()
        if fits_exercise(e.name, e.equipment, allowed)
    ]


def _completion_rate(db: Session, today: date) -> float | None:
    rows = db.scalars(
        select(QuestItem).where(QuestItem.day >= today - timedelta(days=7), QuestItem.day < today)
    ).all()
    if not rows:
        return None
    return sum(1 for r in rows if r.completed_at) / len(rows)


def _band_today(db: Session, today: date) -> str | None:
    from app.modules.progress import checkins

    c = checkins.for_day(db, today)
    return c.band if c else None


def training_quest_started(db: Session, day: date) -> bool:
    """True once a set has counted towards today's training item (or it is done)."""
    row = db.scalars(
        select(QuestItem).where(QuestItem.day == day, QuestItem.kind == "training")
    ).first()
    return row is not None and (row.completed_at is not None or row.progress > 0)


def refresh_training_item(db: Session, now: datetime) -> None:
    """v1.2: re-pick today's untouched training item after the profile (equipment, focus)
    changes, so a quest drawn before setup never suggests gear the user does not have."""
    resize_training_for_readiness(db, now, _band_today(db, now.date()))


def resize_training_for_readiness(db: Session, now: datetime, band: str | None) -> None:
    """Regenerate today's training item for a new check-in band.

    Only an untouched item is resized: once a set has counted towards it, a later
    check-in leaves the quest as it is."""
    from app.modules.progress import service as progress

    items = ensure_quest(db, now)
    row = next((i for i in items if i.kind == "training"), None)
    if row is None or row.completed_at or row.progress > 0:
        return
    profile = progress.get_profile(db)
    protein = progress.energy_for(profile).protein_target_g if profile else None
    spec = generate_daily_quest(
        now.date(),
        progress.muscle_states(db, now),
        _exercise_refs(db),
        protein,
        _completion_rate(db, now.date()),
        readiness_band=band,
        tuning=_tuning(db, now),
    )[0]
    row.code, row.title, row.detail = spec.code, spec.title, spec.detail
    row.metric, row.target, row.xp = spec.metric, spec.target, spec.xp
    row.generator_version = GENERATOR_VERSION
    db.flush()


def _tuning(db: Session, now: datetime) -> Tuning | None:
    """personalize-v1 from the player state; None before there is a profile."""
    from app.modules.progress import service as progress
    from app.modules.selector import service as selector
    from app.modules.selector.personalize import personalize

    if progress.get_profile(db) is None:
        return None
    return personalize(selector.player_state(db, now)).tuning


def _plan_item(db: Session, now: datetime) -> QuestItemSpec | None:
    """v1.2 "follow your program": with a program followed, today's training item is its
    next session (one set of each of its exercises counts it done)."""
    from app.modules.workouts import programs_service

    try:
        plan = programs_service.plan(db, now)
    except Exception:  # a broken custom program must never break the quest
        return None
    if plan is None or not plan.next.items:
        return None
    n = len([i for i in plan.next.items if i.exercise_id is not None])
    if n == 0:
        return None
    first = ", ".join(i.exercise for i in plan.next.items[:3])
    return QuestItemSpec(
        kind="training",
        code="plan_session",
        title=f"Today's session: {plan.next.name}"[:80],
        detail=f"From {plan.name}: log a set of each of its {n} exercises ({first}…).",
        metric=f"plan:{plan.id}:{plan.next.key}"[:40],
        target=n,
        xp=TRAINING_XP,
    )


REST_DAY_XP = 10


def _rest_item(db: Session, now: datetime) -> QuestItemSpec | None:
    """v1.3: on a planned rest day the training item is "Rest day ✓" (already done) and
    the streak is safe; nothing asks you to train."""
    from app.modules.workouts import programs_service

    today = now.date()
    if today not in planned_rest_days(db, today) or today in active_days(db):
        return None
    plan = programs_service.active(db)
    if plan is None:
        return None
    return QuestItemSpec(
        kind="training",
        code="rest_day",
        title="Rest day \u2713",
        detail="A planned rest day in your program: your streak is safe. A walk or a stretch "
        "is a bonus, not a must.",
        metric="rest_day",
        target=1,
        xp=REST_DAY_XP,
    )


def follow_plan_today(db: Session, now: datetime) -> None:
    """A program chosen mid-day takes over today's training item too, as long as nothing
    has been counted on it yet (no progress, not completed)."""
    spec = _plan_item(db, now)
    if spec is None:
        return
    row = db.scalars(
        select(QuestItem).where(QuestItem.day == now.date(), QuestItem.kind == "training")
    ).first()
    if row is None or row.completed_at is not None:
        return
    if row.code != "plan_session" and (_metric_value(db, row.metric, now.date()) or 0) > 0:
        return
    if db.scalar(
        select(QuestItem.id).where(
            QuestItem.day == now.date(), QuestItem.code == "plan_session", QuestItem.id != row.id
        )
    ):
        return
    row.code, row.title, row.detail = spec.code, spec.title, spec.detail
    row.metric, row.target, row.xp = spec.metric, spec.target, spec.xp
    db.flush()


def ensure_quest(db: Session, now: datetime) -> list[QuestItem]:
    from app.modules.progress import service as progress

    today = now.date()
    items = list(
        db.scalars(select(QuestItem).where(QuestItem.day == today).order_by(QuestItem.id)).all()
    )
    if items:
        return items
    profile = progress.get_profile(db)
    protein = progress.energy_for(profile).protein_target_g if profile else None
    had_history = db.scalar(
        select(func.count()).select_from(QuestItem).where(QuestItem.day < today)
    )
    yesterday = today - timedelta(days=1)
    missed = (
        bool(had_history)
        and yesterday not in active_days(db)
        and yesterday not in planned_rest_days(db, today)
    )
    specs = generate_daily_quest(
        today,
        progress.muscle_states(db, now),
        _exercise_refs(db),
        protein,
        _completion_rate(db, today),
        missed,
        readiness_band=_band_today(db, today),
        tuning=_tuning(db, now),
    )
    plan_item = _rest_item(db, now) or _plan_item(db, now)
    if plan_item is not None and specs and specs[0].kind == "training":
        specs[0] = plan_item  # v1.2: the quest follows your program (v1.3: its rest days)
    # Two first requests of the day (the dashboard and the quest panel at app start) can
    # both find no quest and both build one; the second insert then hits the unique
    # (day, code) index. A savepoint keeps that from failing the request: the loser rolls
    # back its own rows and reads the quest the other request wrote.
    try:
        with db.begin_nested():
            for s in specs:
                db.add(
                    QuestItem(
                        day=today,
                        kind=s.kind,
                        code=s.code,
                        title=s.title,
                        detail=s.detail,
                        metric=s.metric,
                        target=s.target,
                        xp=s.xp,
                        generator_version=GENERATOR_VERSION,
                    )
                )
    except IntegrityError:
        pass
    return list(
        db.scalars(select(QuestItem).where(QuestItem.day == today).order_by(QuestItem.id)).all()
    )


def _plan_progress(db: Session, metric: str, day: date) -> int:
    from app.modules.workouts import programs_service
    from app.modules.workouts.models import Exercise, PlanEnrollment, WorkoutSet

    _, enrollment_id, day_key = metric.split(":", 2)
    e = db.get(PlanEnrollment, int(enrollment_id))
    p = programs_service.get_program(db, e.program_key) if e is not None else None
    d = next((x for x in p.days if x.key == day_key), None) if p is not None else None
    if d is None:
        return 0
    names = {s.exercise for s in d.slots}
    stmt = (
        select(func.count(func.distinct(Exercise.name)))
        .join(WorkoutSet, WorkoutSet.exercise_id == Exercise.id)
        .where(Exercise.name.in_(names), func.date(WorkoutSet.performed_at) == day.isoformat())
    )
    return int(db.scalar(stmt) or 0)


def _metric_value(db: Session, metric: str, day: date) -> int | None:
    from app.modules.nutrition import service as nutrition
    from app.modules.workouts.models import ExerciseMuscle, Workout, WorkoutSet

    if metric.startswith("sets:"):
        muscle = metric.split(":", 1)[1]
        stmt = (
            select(func.count(WorkoutSet.id))
            .join(Workout, Workout.id == WorkoutSet.workout_id)
            .join(ExerciseMuscle, ExerciseMuscle.exercise_id == WorkoutSet.exercise_id)
            .where(
                # By when the set was done, not the session's start day: a set logged
                # after midnight counts toward the new day's quest.
                func.date(WorkoutSet.performed_at) == day.isoformat(),
                ExerciseMuscle.muscle == muscle,
                ExerciseMuscle.weight >= 1.0,
                (WorkoutSet.rpe.is_(None)) | (WorkoutSet.rpe >= f.HARD_SET_RPE),
            )
        )
        return int(db.scalar(stmt) or 0)
    if metric.startswith("ex:"):
        # ex:<exercise id>:<reps|hold>:<min>: sets of one exercise today reaching the minimum.
        _, ex_id, kind, minimum = metric.split(":")
        value = WorkoutSet.duration_s if kind == "hold" else WorkoutSet.reps
        stmt = select(func.count(WorkoutSet.id)).where(
            WorkoutSet.exercise_id == int(ex_id),
            func.date(WorkoutSet.performed_at) == day.isoformat(),
            value >= int(minimum),
        )
        return int(db.scalar(stmt) or 0)
    if metric.startswith("plan:"):
        # plan:<enrollment id>:<day key>: exercises of that program day with a set today.
        return _plan_progress(db, metric, day)
    if metric == "rest_day":
        return 1
    if metric == "meals":
        return nutrition.meal_count(db, day)
    if metric == "protein_g":
        return round(nutrition.day_totals(db, day).protein_g)
    return None  # manual items are checked off by the user


def _complete(db: Session, bus: EventBus, item: QuestItem, now: datetime) -> None:
    item.completed_at = now
    item.progress = max(item.progress, item.target)
    mult = f.streak_multiplier(streak(db, now.date()).current)
    granted = award(db, now, "quest", item.id, round(item.xp * mult), note=item.title)
    bus.publish(db, QuestCompleted(quest_item_id=item.id, day=item.day, xp=granted))


def refresh_quest(db: Session, bus: EventBus, now: datetime) -> None:
    for item in ensure_quest(db, now):
        if item.completed_at:
            continue
        value = _metric_value(db, item.metric, item.day)
        if value is None:
            continue
        item.progress = min(value, item.target)
        if value >= item.target:
            _complete(db, bus, item, now)
    db.flush()


def complete_manual(db: Session, bus: EventBus, item_id: int, now: datetime) -> QuestItem:
    item = db.get(QuestItem, item_id)
    if item is None or item.day != now.date():
        raise QuestNotFound(f"quest item {item_id} is not part of today's quest")
    if item.metric != "manual":
        raise ValueError("this item completes automatically from your logs")
    if not item.completed_at:
        _complete(db, bus, item, now)
    db.flush()
    return item


# --- skill training items ---------------------------------------------------------


SKILL_QUEST_XP = 15
MAX_SKILL_ITEMS_PER_DAY = 4
SKILL_GENERATOR_VERSION = "skill-quest-v1"


@dataclass(frozen=True)
class SkillQuestSpec:
    code: str
    title: str
    detail: str
    metric: str
    target: int


def add_skill_items(
    db: Session, bus: EventBus, now: datetime, specs: list[SkillQuestSpec]
) -> tuple[int, int, list[str]]:
    """Add "train this skill" items to today's quest. Idempotent per code, at most
    MAX_SKILL_ITEMS_PER_DAY a day (so the button cannot be farmed for quest XP).
    Returns (added, already planned, titles of today's skill items)."""
    items = ensure_quest(db, now)
    codes = {i.code for i in items}
    skill_items = [i for i in items if i.kind == "skill"]
    added = already = 0
    for spec in specs:
        if spec.code in codes:
            already += 1
            continue
        if len(skill_items) >= MAX_SKILL_ITEMS_PER_DAY:
            break
        row = QuestItem(
            day=now.date(),
            kind="skill",
            code=spec.code[:40],
            title=spec.title[:120],
            detail=spec.detail[:200],
            metric=spec.metric,
            target=spec.target,
            xp=SKILL_QUEST_XP,
            generator_version=SKILL_GENERATOR_VERSION,
        )
        db.add(row)
        db.flush()
        skill_items.append(row)
        codes.add(spec.code)
        added += 1
    refresh_quest(db, bus, now)
    return added, already, [i.title for i in skill_items]


# --- summary ---------------------------------------------------------------------


def welcome_back_due(db: Session, day: date) -> bool:
    """review M8: today's session comes after at least one unplanned missed day since the
    last training day, and no welcome-back bonus was paid this week yet."""
    earlier = [d for d in active_days(db) if d < day]
    if not earlier:
        return False  # the very first session is not a comeback
    last = max(earlier)
    rest = planned_rest_days(db, day)
    gap = [last + timedelta(days=k) for k in range(1, (day - last).days)]
    if not any(d not in rest for d in gap):
        return False
    paid = db.scalar(
        select(func.count(XpEvent.id)).where(
            XpEvent.source == "welcome_back",
            XpEvent.day >= week_start(day),
            XpEvent.amount > 0,
        )
    )
    return not paid


def week_target(db: Session, today: date | None = None) -> int:
    """Training days a week the plan asks for: the days picked for this week (v1.4
    schedule), else the followed program's days, else the sessions-per-week setting
    (capped by the program when both exist)."""
    from app.modules.progress import service as progress
    from app.modules.schedule import service as schedule
    from app.modules.workouts import programs_service

    if today is not None:
        own = schedule.week_target(db, today)
        if own:
            return own
    want = int(progress.get_setting(db, "sessions_per_week", "3") or 3)
    e = programs_service.active(db)
    p = programs_service.get_program(db, e.program_key) if e is not None else None
    if p is not None and p.days:
        return max(1, min(want, len({d.weekday % 7 for d in p.days})))
    return max(1, min(want, 7))


def met_weeks(db: Session, days: set[date], target: int) -> set[date]:
    """Weeks (Monday) with the plan met: `target` training days, or the weekly boss beaten."""
    from app.modules.gamification.models import BossRaid

    count: dict[date, int] = {}
    for d in days:
        count[week_start(d)] = count.get(week_start(d), 0) + 1
    met = {w for w, n in count.items() if n >= target}
    met |= set(
        db.scalars(select(BossRaid.week_start).where(BossRaid.defeated_at.is_not(None))).all()
    )
    return met


def streak_out(s: StreakState, db: Session | None = None, today: date | None = None) -> StreakOut:
    out = StreakOut(
        current=s.current,
        best=s.best,
        excused=s.excused,
        active_today=s.active_today,
        reason_due=s.reason_due,
    )
    if db is None or today is None:
        return out
    days = active_days(db)
    target = week_target(db, today)
    out.rest_today = is_rest_day(db, today)
    out.lifetime_sessions = len(days)
    out.next_milestone = next_milestone(len(days))
    out.week_target = target
    out.weeks_in_a_row = weeks_in_a_row(met_weeks(db, days, target), today)
    return out


def give_reason(db: Session, day: date, reason: str, now: datetime) -> StreakState:
    """Record why `day` was missed. Only yesterday (or today, ahead of time) can get one:
    the rule is "by the next day". Raises ValueError for anything else."""
    from app.modules.gamification.models import StreakReason

    today = now.date()
    text = " ".join(reason.split())[:120]
    if not text:
        raise ValueError("Say a few words about why.")
    if day not in (today - timedelta(days=1), today):
        raise ValueError("A reason counts for yesterday only (by the end of the next day).")
    if day in active_days(db):
        raise ValueError("That day already counts: nothing to explain.")
    if day in planned_rest_days(db, today):
        raise ValueError("That was a planned rest day: it never breaks your streak.")
    row = db.get(StreakReason, day)
    if row is None:
        db.add(StreakReason(day=day, reason=text, given_on=today, given_at=now))
    else:
        row.reason, row.given_on, row.given_at = text, today, now
    db.commit()
    return streak(db, today)


def summary(db: Session, bus: EventBus, now: datetime) -> GameSummary:
    refresh_quest(db, bus, now)
    total = total_xp(db)
    info = f.level_from_total(total)
    letter, title = f.rank_for_level(info.level)
    sub, next_sub, next_sub_level = f.sub_rank_for_level(info.level)
    s = streak(db, now.date())
    c = calm_streak(db, now.date())
    return GameSummary(
        xp=XpOut(
            total=total,
            today=earned_on(db, now.date()),
            level=info.level,
            xp_into_level=info.xp_into_level,
            xp_for_next=info.xp_for_next,
            rank=letter,
            rank_title=title,
            daily_cap=f.DAILY_CAP,
            formula_version=f.FORMULA_VERSION,
            sub_rank=sub,
            next_sub_rank=next_sub,
            next_sub_rank_level=next_sub_level,
        ),
        streak=streak_out(s, db, now.date()),
        calm=CalmStreakOut(current=c.current, best=c.best, active_today=c.active_today),
        quest=[QuestItemOut.model_validate(q) for q in ensure_quest(db, now)],
    )


# --- event handlers ------------------------------------------------------------------


# --- anti-farming helpers (xp-v3) --------------------------------------------


def _sets_before(db: Session, set_id: int, exercise_id: int, day: date) -> tuple[int, int]:
    """(sets of this exercise, sets in total) logged earlier on the same calendar day."""
    from app.modules.workouts.models import WorkoutSet

    same_day = (func.date(WorkoutSet.performed_at) == day.isoformat()) & (WorkoutSet.id < set_id)
    total = db.scalar(select(func.count(WorkoutSet.id)).where(same_day)) or 0
    of_ex = (
        db.scalar(
            select(func.count(WorkoutSet.id)).where(same_day, WorkoutSet.exercise_id == exercise_id)
        )
        or 0
    )
    return int(of_ex), int(total)


def _pr_values(db: Session, row: Any) -> tuple[float | None, float | None]:
    """The PR set's value (e1RM, or seconds for a hold) and the best before it."""
    from app.modules.workouts.models import WorkoutSet

    hold = row.exercise.measure == "hold" and row.e1rm is None
    column = WorkoutSet.duration_s if hold else WorkoutSet.e1rm
    value = float(row.duration_s or 0) if hold else row.e1rm
    previous = db.scalar(
        select(func.max(column)).where(
            WorkoutSet.exercise_id == row.exercise_id, WorkoutSet.id != row.id
        )
    )
    return value, (float(previous) if previous is not None else None)


def _net_refs(db: Session, source: str, day: date) -> list[int]:
    rows = db.execute(
        select(XpEvent.ref_id, func.sum(XpEvent.amount))
        .where(XpEvent.source == source, XpEvent.day == day, XpEvent.ref_id.is_not(None))
        .group_by(XpEvent.ref_id)
    ).all()
    return [int(ref) for ref, total in rows if ref is not None and (total or 0) > 0]


def _prs_today(db: Session, exercise_id: int, day: date) -> tuple[int, int]:
    from app.modules.workouts.models import WorkoutSet

    refs = _net_refs(db, "pr", day)
    if not refs:
        return 0, 0
    of_ex = db.scalar(
        select(func.count(WorkoutSet.id)).where(
            WorkoutSet.id.in_(refs), WorkoutSet.exercise_id == exercise_id
        )
    )
    return int(of_ex or 0), len(refs)


def _paid_today(db: Session, source: str, day: date) -> int:
    return len(_net_refs(db, source, day))


def _session_work(sets: list[Any]) -> tuple[int, float]:
    """(working sets, timed minutes) of a session, from its sets."""
    timed = sum(
        (s.duration_s or 0) / 60
        for s in sets
        if s.exercise.section in ("cardio", "martial_arts", "flexibility", "meditation")
    )
    return len(sets), timed


TIMED_SECTIONS = ("cardio", "martial_arts", "flexibility", "meditation")


def _set_amount(
    db: Session,
    set_id: int,
    exercise_id: int,
    performed_at: datetime,
    rpe: float | None,
    duration_s: int | None,
    section: str,
) -> int:
    """XP a set earns as logged now (before the daily cap)."""
    if duration_s and section in TIMED_SECTIONS:
        amount = f.timed_set_xp(duration_s, section)
    else:
        amount = f.set_xp(rpe)
    if not f.set_xp_allowed(*_sets_before(db, set_id, exercise_id, performed_at.date())):
        return 0  # diminishing returns: logging the 41st set of the day pays nothing
    return amount


def _reverse_lost_prs(db: Session, at: datetime, exercise_id: int) -> None:
    """Take PR XP back from every set of this exercise that is no longer a PR after an
    edit or delete re-derived the PR flags (recompute_prs)."""
    from app.modules.workouts.models import WorkoutSet

    lost = db.scalars(
        select(WorkoutSet.id).where(
            WorkoutSet.exercise_id == exercise_id, WorkoutSet.is_pr.is_(False)
        )
    ).all()
    paid = {
        int(ref)
        for ref, total in db.execute(
            select(XpEvent.ref_id, func.sum(XpEvent.amount))
            .where(XpEvent.source == "pr", XpEvent.ref_id.in_(list(lost)))
            .group_by(XpEvent.ref_id)
        ).all()
        if ref is not None and (total or 0) > 0
    }
    for set_id in sorted(paid):
        reverse(db, at, ("pr",), set_id, note="no longer a PR after an edit")


def make_handlers(bus: EventBus) -> None:
    def on_set_logged(db: Session, e: SetLogged) -> None:
        from app.modules.workouts.models import WorkoutSet

        day = e.performed_at.date()
        amount = _set_amount(
            db, e.set_id, e.exercise_id, e.performed_at, e.rpe, e.duration_s, e.section
        )
        if amount:
            award(db, e.performed_at, "set", e.set_id, amount)
        if e.is_pr:
            row = db.get(WorkoutSet, e.set_id)
            value, previous = _pr_values(db, row) if row else (None, None)
            prs_ex, prs_day = _prs_today(db, e.exercise_id, day)
            if f.pr_xp_allowed(value, previous, prs_ex, prs_day):
                award(db, e.performed_at, "pr", e.set_id, f.PR_XP, note="new PR")
        refresh_quest(db, bus, e.performed_at)

    def on_set_updated(db: Session, e: SetUpdated) -> None:
        now = bus.clock()
        # An edit can take XP away (the set was easier or shorter than logged) but never
        # adds any, so editing a set up after logging it earns nothing (review L8).
        due = _set_amount(
            db, e.set_id, e.exercise_id, e.performed_at, e.rpe, e.duration_s, e.section
        )
        paid = xp_for_refs(db, ("set",), e.set_id)
        if paid > due:
            reverse(db, now, ("set",), e.set_id, note="set edited", amount=paid - due)
        # PR XP: the edit can end this set's PR or another set's (a heavier older set).
        _reverse_lost_prs(db, now, e.exercise_id)
        refresh_quest(db, bus, now)

    def on_set_deleted(db: Session, e: SetDeleted) -> None:
        from app.modules.workouts.models import Workout

        now = bus.clock()
        reverse(db, now, ("set",), e.set_id, note="set deleted")
        reverse(db, now, ("pr",), e.set_id, note="set deleted")
        _reverse_lost_prs(db, now, e.exercise_id)
        workout = db.get(Workout, e.workout_id)
        if workout is not None and workout.finished_at is not None:
            remaining = [s for s in workout.sets if s.id != e.set_id]
            sets, timed = _session_work(remaining)
            if not (sets >= f.SESSION_MIN_SETS or timed >= f.SESSION_MIN_TIMED_MINUTES):
                reverse(db, now, ("session",), workout.id, note="session too short after a delete")
                reverse(db, now, ("welcome_back",), workout.id, note="session too short")
        refresh_quest(db, bus, now)

    def on_workout_logged(db: Session, e: WorkoutLogged) -> None:
        from app.modules.workouts.models import Workout

        workout = db.get(Workout, e.workout_id)
        at = workout.finished_at if workout and workout.finished_at else bus.clock()
        set_ids = [s.id for s in workout.sets] if workout else []
        already = int(
            db.scalar(
                select(func.coalesce(func.sum(XpEvent.amount), 0)).where(
                    XpEvent.source == "set", XpEvent.ref_id.in_(set_ids)
                )
            )
            or 0
        )
        sets, timed = _session_work(list(workout.sets) if workout else [])
        if f.session_qualifies(sets, timed, _paid_today(db, "session", at.date())):
            minutes = f.session_minutes(e.active_minutes, sets, timed)
            bonus = f.session_completion_xp(minutes, already)
            mult = f.streak_multiplier(streak(db, at.date()).current)
            award(db, at, "session", e.workout_id, round(bonus * mult), note="session complete")
            if welcome_back_due(db, at.date()):
                award(db, at, "welcome_back", e.workout_id, f.WELCOME_BACK_XP, note="welcome back")
        refresh_quest(db, bus, at)

    def on_meal_logged(db: Session, e: MealLogged) -> None:
        from app.modules.nutrition import service as nutrition

        meal = nutrition.get_meal(db, e.meal_id)
        meals_before = max(0, nutrition.meal_count(db, e.day) - 1)
        award(db, meal.logged_at, "meal", e.meal_id, f.meal_xp(meals_before))
        refresh_quest(db, bus, meal.logged_at)

    def on_checkin(db: Session, e: CheckinRecorded) -> None:
        resize_training_for_readiness(db, e.at, e.band)

    def on_skill_unlocked(db: Session, e: SkillStepUnlocked) -> None:
        if e.xp > 0:
            award(db, e.at, "skill", e.unlock_id, e.xp, note=f"{e.skill_name}: {e.step_name}")

    def on_skill_revoked(db: Session, e: SkillStepRevoked) -> None:
        reverse(db, e.at, ("skill",), e.unlock_id, note=f"skill step revoked: {e.step_key}")

    bus.subscribe(SetLogged, on_set_logged)
    bus.subscribe(SetUpdated, on_set_updated)
    bus.subscribe(SetDeleted, on_set_deleted)
    bus.subscribe(WorkoutLogged, on_workout_logged)
    bus.subscribe(MealLogged, on_meal_logged)
    bus.subscribe(CheckinRecorded, on_checkin)
    bus.subscribe(SkillStepUnlocked, on_skill_unlocked)
    bus.subscribe(SkillStepRevoked, on_skill_revoked)


def register(bus: EventBus) -> None:
    make_handlers(bus)
