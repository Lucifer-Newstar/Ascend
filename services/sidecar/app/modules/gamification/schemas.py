from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


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
    current: int
    best: int
    freezes_held: int
    freezes_used: int
    active_today: bool


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


class CalmStreakOut(BaseModel):
    """Days in a row with at least one meditation sit (same freeze rules)."""

    current: int
    best: int
    active_today: bool


class GameSummary(BaseModel):
    xp: XpOut
    streak: StreakOut
    calm: CalmStreakOut = CalmStreakOut(current=0, best=0, active_today=False)
    quest: list[QuestItemOut]


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
