from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class QuestItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    day: date
    kind: str
    code: str
    title: str
    detail: str
    metric: str
    target: int
    progress: int
    xp: int
    completed_at: datetime | None


class StreakOut(BaseModel):
    """v1.2: a missed day is kept with a reason given by the next day (no more freezes)."""

    current: int
    best: int
    excused: int = 0
    active_today: bool
    reason_due: date | None = None
    # v1.3 (review S5, S6, 1.3, 1.6): numbers that never reset and today's plan.
    rest_today: bool = False
    lifetime_sessions: int = 0
    next_milestone: int | None = 1
    weeks_in_a_row: int = 0
    week_target: int = 3


class StreakReasonIn(BaseModel):
    day: date
    reason: str = Field(min_length=1, max_length=120)


class XpOut(BaseModel):
    total: int
    today: int
    level: int
    xp_into_level: int
    xp_for_next: int
    rank: str
    rank_title: str
    daily_cap: int
    formula_version: str
    # v1.3 near goals: E1-E3 style sub-ranks (display only; the XP formula is unchanged).
    sub_rank: str = "E1"
    next_sub_rank: str | None = None
    next_sub_rank_level: int | None = None


class CalmStreakOut(BaseModel):
    """Days in a row with at least one meditation sit (same reason rule)."""

    current: int
    best: int
    active_today: bool


class GameSummary(BaseModel):
    xp: XpOut
    streak: StreakOut
    calm: CalmStreakOut = CalmStreakOut(current=0, best=0, active_today=False)
    quest: list[QuestItemOut]


class ThemeOut(BaseModel):
    """v1.2: one app theme, whether it is free or earned, and how to earn it."""

    key: str
    name: str
    tagline: str
    free: bool
    unlocked: bool
    requirement: str
    progress: str = ""


class StatOut(BaseModel):
    """One computed hunter stat (0-100) with the numbers behind it."""

    key: str
    label: str
    value: int
    formula: str
    inputs: dict[str, float | int | str | None]


class StatsOut(BaseModel):
    stats: list[StatOut]
    version: str
    window_days: int


class BossWhy(BaseModel):
    formula: str
    inputs: dict[str, int | str | None]


class BossOut(BaseModel):
    """GET /game/boss: this week's boss raid (boss-v1, ADR-0022)."""

    week_start: date
    week_end: date
    name: str
    title: str
    hp: int
    damage: int
    hp_left: int
    days_left: int
    defeated: bool
    defeated_at: datetime | None
    bonus_xp: int
    hp_source: str
    hp_note: str
    titles_earned: int
    algo_version: str
    why: BossWhy
    # boss-v2 (v1.2)
    tier: str = "C"
    category: str = "strength"
    seasonal: bool = False
    season: str | None = None
    season_ends: date | None = None
    drop: str | None = None


class BossLadderOut(BaseModel):
    """GET /game/bosses: every boss, by tier and category, and how often you beat it."""

    name: str
    title: str
    tier: str  # a seasonal boss: "follows your level"
    category: str
    min_level: str
    seasonal: bool
    season: str | None
    months: list[int]
    drop: str | None
    beaten: int


class TitleOut(BaseModel):
    """A title earned by beating a weekly boss: the only source of titles."""

    title: str
    boss: str
    week_start: date
    earned_at: datetime
