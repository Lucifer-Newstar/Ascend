from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_bus, get_db, get_now
from app.core.events import EventBus
from app.modules.gamification import boss, boss_service, service, stats, themes, unlocks
from app.modules.gamification.schemas import (
    BossLadderOut,
    BossOut,
    BossWhy,
    GameSummary,
    QuestItemOut,
    StatOut,
    StatsOut,
    StreakOut,
    StreakReasonIn,
    ThemeOut,
    TitleOut,
    UnlockOut,
    UnlocksSyncIn,
    UnlocksSyncOut,
)

router = APIRouter(prefix="/game", tags=["gamification"])


@router.get("/summary", response_model=GameSummary)
def summary(
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_bus),
    now: datetime = Depends(get_now),
) -> GameSummary:
    return service.summary(db, bus, now)


@router.post("/streak/reason", response_model=StreakOut)
def streak_reason(
    body: StreakReasonIn,
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> StreakOut:
    """v1.2: say why a day was missed. Given by the end of the next day, it keeps the
    streak; two missed days in a row still reset it."""
    try:
        return service.streak_out(
            service.give_reason(db, body.day, body.reason, now), db, now.date()
        )
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


@router.post("/quests/{item_id}/complete", response_model=QuestItemOut)
def complete(
    item_id: int,
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_bus),
    now: datetime = Depends(get_now),
) -> QuestItemOut:
    try:
        return QuestItemOut.model_validate(service.complete_manual(db, bus, item_id, now))
    except service.QuestNotFound as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(409, str(e)) from e


@router.get("/themes", response_model=list[ThemeOut])
def list_themes(db: Session = Depends(get_db), now: datetime = Depends(get_now)) -> list[ThemeOut]:
    """v1.2 app themes: Light, Dark and Shadow are free; the rest unlock from your record
    (best streak, rank, bosses beaten) and stay unlocked once earned."""
    have = themes.unlocked(db, now)
    r = themes.record(db, now)
    return [
        ThemeOut(
            key=t.key,
            name=t.name,
            tagline=t.tagline,
            free=t.rule is None,
            unlocked=t.key in have,
            requirement=themes.requirement(t),
            progress="" if t.key in have else themes.progress_text(t, r),
        )
        for t in themes.THEMES
    ]


@router.get("/stats", response_model=StatsOut)
def hunter_stats(
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> StatsOut:
    """STR, AGI, END, VIT and INT (0-100), each with its formula and inputs (stats-v1)."""
    rows = stats.compute_stats(stats.gather(db, now))
    return StatsOut(
        stats=[
            StatOut(key=s.key, label=s.label, value=s.value, formula=s.formula, inputs=s.inputs)
            for s in rows
        ],
        version=stats.STATS_VERSION,
        window_days=stats.WINDOW_DAYS,
    )


@router.get("/boss", response_model=BossOut)
def boss_raid(db: Session = Depends(get_db), now: datetime = Depends(get_now)) -> BossOut:
    raid, out = boss_service.current(db, now)
    season = boss.SEASON_BY_BOSS.get(raid.name)
    week_end = raid.week_start + timedelta(days=6)
    return BossOut(
        week_start=raid.week_start,
        week_end=week_end,
        name=raid.name,
        title=raid.title,
        hp=raid.hp,
        damage=out.damage,
        hp_left=max(0, raid.hp - out.damage),
        days_left=max(0, (week_end - now.date()).days),
        defeated=raid.defeated_at is not None,
        defeated_at=raid.defeated_at,
        bonus_xp=raid.xp_awarded or boss_service.bonus(raid),
        hp_source=raid.hp_source,
        hp_note=raid.hp_note,
        titles_earned=len(boss_service.titles(db)),
        algo_version=raid.algo_version,
        why=BossWhy(
            formula=(
                "HP = a week of your training (program sets, else the median sets per week "
                "over the last 4 weeks, else 20), clamped 12-150; each training set this "
                "week deals 1 damage; the tier scales it (E 80% to S 130%); beaten at 0 HP "
                "by Sunday"
            ),
            inputs={
                "hp": raid.hp,
                "hp_source": raid.hp_source,
                "sets_this_week": out.damage,
                "bonus_xp": raid.xp_awarded or boss_service.bonus(raid),
                "tier": boss_service.tier(raid),
            },
        ),
        tier=boss_service.tier(raid),
        category=boss.category_of(raid.name),
        seasonal=season is not None,
        season=season.name if season else None,
        season_ends=boss.season_end(raid.week_start) if season else None,
        drop=season.drop if season else None,
    )


@router.get("/bosses", response_model=list[BossLadderOut])
def boss_ladder(db: Session = Depends(get_db)) -> list[BossLadderOut]:
    """The boss ladder (boss-v2): the twelve weekly bosses by tier, then the four seasonal
    ones. `beaten` counts your wins against each."""
    wins: dict[str, int] = {}
    for r in boss_service.titles(db):
        wins[r.name] = wins.get(r.name, 0) + 1
    out = [
        BossLadderOut(
            name=name,
            title=title,
            tier=boss.BOSS_TIER[name],
            category=boss.BOSS_CATEGORY[name],
            min_level=boss.BOSS_GATES[name][0],
            seasonal=False,
            season=None,
            months=[],
            drop=None,
            beaten=wins.get(name, 0),
        )
        for name, title in boss.BOSSES
    ]
    out.sort(key=lambda b: boss.TIERS.index(b.tier))
    out += [
        BossLadderOut(
            name=s.boss,
            title=s.title,
            tier="level",
            category=s.category,
            min_level="beginner",
            seasonal=True,
            season=s.name,
            months=list(s.months),
            drop=s.drop,
            beaten=wins.get(s.boss, 0),
        )
        for s in boss.SEASONS
    ]
    return out


@router.get("/titles", response_model=list[TitleOut])
def titles(db: Session = Depends(get_db)) -> list[TitleOut]:
    return [
        TitleOut(title=r.title, boss=r.name, week_start=r.week_start, earned_at=r.defeated_at)
        for r in boss_service.titles(db)
        if r.defeated_at is not None
    ]


@router.get("/unlocks", response_model=list[UnlockOut], summary="Your unlocks, newest first")
def list_unlocks(db: Session = Depends(get_db)) -> list[UnlockOut]:
    """v1.4: every skill step, boss clear, rank and cosmetic you have unlocked, with the
    date it first appeared (for the Unlocks page and its replays)."""
    return [UnlockOut.model_validate(r) for r in unlocks.list_unlocks(db)]


@router.post("/unlocks/sync", response_model=UnlocksSyncOut, summary="Record what is unlocked now")
def sync_unlocks(
    body: UnlocksSyncIn, db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> UnlocksSyncOut:
    """The desktop reports what is unlocked; the ones not seen before come back as `new`
    (to play as a reveal). The very first sync records everything quietly."""
    new, total = unlocks.sync(db, now, body.items)
    return UnlocksSyncOut(new=[UnlockOut.model_validate(r) for r in new], total=total)
