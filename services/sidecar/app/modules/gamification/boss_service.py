"""Weekly boss raid service (boss-v2, ADR-0022): spawn, damage, defeat and titles.

boss-v2 (v1.2) adds tiers (E to S, scaling HP and bonus) and seasonal bosses."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.gamification import boss
from app.modules.gamification.models import BossRaid, XpEvent
from app.modules.gamification.service import reverse

SOURCE = "boss"


def _set_times(db: Session, start: date, end: date) -> list[datetime]:
    """When each training set between start (inclusive) and end (exclusive) was logged."""
    from app.modules.workouts.models import Exercise, WorkoutSet

    stmt = (
        select(WorkoutSet.performed_at)
        .join(Exercise, Exercise.id == WorkoutSet.exercise_id)
        .where(
            WorkoutSet.performed_at >= datetime.combine(start, time.min),
            WorkoutSet.performed_at < datetime.combine(end, time.min),
            Exercise.section.in_(boss.DAMAGE_SECTIONS),
        )
        .order_by(WorkoutSet.performed_at)
    )
    return list(db.scalars(stmt).all())


def _hp(db: Session, week: date) -> boss.Hp:
    from app.modules.workouts import programs_service
    from app.modules.workouts.deload_service import _last_deload_week

    enrollment = programs_service.active(db)
    program = programs_service.get_program(db, enrollment.program_key) if enrollment else None
    program_sets = sum(s.sets for d in program.days for s in d.slots) if program else None
    weekly = [
        len(_set_times(db, week - timedelta(weeks=n), week - timedelta(weeks=n - 1)))
        for n in range(boss.HISTORY_WEEKS, 0, -1)
    ]
    return boss.hp_for(
        program_sets,
        program.name if program else None,
        _last_deload_week(db) == week,
        weekly,
    )


def _spawn(db: Session, week: date, now: datetime) -> BossRaid:
    # The boss is gated by the player's level and readiness (select-v1, BOSS_GATES).
    from app.modules.selector.service import player_state

    state = player_state(db, now)
    name, title = boss.boss_for(
        week, state.level, state.most_under(), state.low_readiness, seasonal=True
    )
    tier = boss.tier_of(name, state.level)
    hp = boss.scaled(_hp(db, week), tier)
    raid = BossRaid(
        week_start=week,
        name=name,
        title=title,
        hp=hp.hp,
        hp_source=hp.source,
        hp_note=hp.note[:160],
        algo_version=boss.ALGO_VERSION,
        created_at=now,
        xp_awarded=0,
        tier=tier,
    )
    # Two first requests of the week (Today's boss card and the summary at app start) can
    # both find no raid; the second insert then hits the unique week_start index. A
    # savepoint keeps that from failing the request: the loser reads the other's raid.
    try:
        with db.begin_nested():
            db.add(raid)
    except IntegrityError:
        existing = db.scalar(select(BossRaid).where(BossRaid.week_start == week))
        if existing is None:
            raise
        return existing
    return raid


def tier(raid: BossRaid) -> str:
    return raid.tier or boss.tier_of(raid.name)


def bonus(raid: BossRaid) -> int:
    """The bonus for beating it: by tier from boss-v2 on; boss-v1 raids keep 150."""
    if raid.algo_version == "boss-v1":
        return boss.BONUS_XP
    return boss.bonus_for(tier(raid))


def settle(db: Session, raid: BossRaid, now: datetime) -> boss.Outcome:
    """Recount the damage and grant (or take back) the bonus. The bonus is a weekly
    one-off outside the daily XP cap; if deleted sets bring the boss back above 0 HP
    before the week ends, the bonus and title are taken back like any other XP."""
    times = _set_times(db, raid.week_start, raid.week_start + timedelta(days=7))
    out = boss.outcome(raid.hp, [t.date() for t in times])
    if out.defeated_on is not None and raid.defeated_at is None:
        at = times[raid.hp - 1]
        raid.defeated_at = at
        raid.xp_awarded = bonus(raid)
        db.add(
            XpEvent(
                day=at.date(),
                at=at,
                source=SOURCE,
                ref_id=raid.id,
                amount=raid.xp_awarded,
                formula_version=boss.ALGO_VERSION,
                note=f"Boss raid cleared: {raid.name}",
            )
        )
    elif out.defeated_on is None and raid.defeated_at is not None:
        reverse(db, now, [SOURCE], raid.id, f"Boss raid no longer cleared: {raid.name}")
        raid.defeated_at = None
        raid.xp_awarded = 0
    db.flush()
    return out


def current(db: Session, now: datetime) -> tuple[BossRaid, boss.Outcome]:
    """This week's raid, spawned on first use; last week's raid is settled first."""
    week = boss.week_start(now.date())
    previous = db.scalar(select(BossRaid).where(BossRaid.week_start == week - timedelta(weeks=1)))
    if previous is not None:
        settle(db, previous, now)
    raid = db.scalar(select(BossRaid).where(BossRaid.week_start == week))
    if raid is None:
        raid = _spawn(db, week, now)
    return raid, settle(db, raid, now)


def titles(db: Session) -> list[BossRaid]:
    """Every boss beaten, newest first: the only source of titles on the Hunter profile."""
    stmt = (
        select(BossRaid)
        .where(BossRaid.defeated_at.is_not(None))
        .order_by(BossRaid.week_start.desc())
    )
    return list(db.scalars(stmt).all())
