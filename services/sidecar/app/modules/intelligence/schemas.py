"""API shapes of the intelligence layer (docs/contracts/intelligence.yaml)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Why(BaseModel):
    """The "Why?" of one number: the formula in words and every input with its value."""

    formula: str
    inputs: dict[str, float | int | str | None]


class TopSet(BaseModel):
    exercise: str
    dose_now: float
    hours_ago: float


class MuscleRecoveryOut(BaseModel):
    key: str
    label: str
    group: str
    status: str
    readiness: float
    readiness_population: float
    fatigue: float
    capacity: float
    half_life_h: float
    prior_half_life_h: float
    k: float
    modifier: float
    es_7d: float
    ready_at: datetime | None
    last_trained: datetime | None
    top_sets: list[TopSet]
    why: Why


class RecoveryGroupOut(BaseModel):
    group: str
    k: float
    k_low: float
    k_high: float
    n: int
    personal: bool
    alpha: float | None
    updated_at: datetime | None


class CheckinUsed(BaseModel):
    sleep: int
    soreness: str


class RecoveryOut(BaseModel):
    """GET /intelligence/recovery: every muscle with its inputs, and the personal factors."""

    algo_version: str
    formula: str
    checkin: CheckinUsed | None
    groups: list[RecoveryGroupOut]
    muscles: list[MuscleRecoveryOut]
