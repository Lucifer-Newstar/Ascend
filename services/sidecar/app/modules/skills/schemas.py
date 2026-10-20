from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class CriterionOut(BaseModel):
    text: str
    exercise: str
    exercise_id: int | None
    sets: int
    target: int
    unit: str  # "reps" | "s"
    added_kg: float = 0
    per_side: bool = False
    best_value: int | None
    best_score: float
    sessions_met: int
    sessions_needed: int
    pct: float
    met: bool
    # Holds longer than the plausibility limit, not counted.
    ignored_sets: int = 0


class StepOut(BaseModel):
    key: str
    name: str
    exercise: str
    exercise_id: int | None
    measure: str
    # unlocked | next (all prerequisites done) | locked
    status: str
    pct: float
    unlocked_at: datetime | None
    criteria: list[CriterionOut]
    requires: list[str]
    xp: int
    uncertain: bool
    note: str = ""


class SkillEtaOut(BaseModel):
    """Days until the next step at the current trend. Always an estimate; None when
    there is not enough data (the reason says what is missing)."""

    days: float | None
    date: date | None
    reason: str
    is_estimate: bool = True


class FeederOut(BaseModel):
    exercise_id: int | None
    name: str
    measure: str
    sets_28d: int


class SourceOut(BaseModel):
    key: str
    title: str
    url: str


class SkillSummary(BaseModel):
    key: str
    name: str
    family: str
    summary: str
    stretch: bool
    current_step: str | None
    current_step_name: str | None
    next_step: str | None
    next_step_name: str | None
    pct_to_next: float | None
    steps_unlocked: int
    steps_total: int
    acquired: bool
    last_trained: datetime | None
    sessions_28d: int
    rusty: bool


class SkillDetail(SkillSummary):
    steps: list[StepOut]
    feeders: list[FeederOut]
    eta: SkillEtaOut
    sources: list[SourceOut]
    engine_version: str


class SkillUnlockOut(BaseModel):
    id: int
    skill_key: str
    skill_name: str
    step_key: str
    step_name: str
    unlocked_at: datetime
    xp: int
    # True when this unlock completes the whole tree.
    final: bool
    next_step_name: str | None = None
    source: str = "log"


class TrainOut(BaseModel):
    skill_key: str
    added: int
    already_planned: int
    # Titles of today's skill quest items after the call.
    items: list[str]
    message: str
