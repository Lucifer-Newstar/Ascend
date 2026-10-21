"""API shapes of the intelligence layer (docs/contracts/intelligence.yaml)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

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


# --- progression (prog-v1) ---------------------------------------------------------------


class E1rmPoint(BaseModel):
    at: datetime
    value: float


class E1rmOut(BaseModel):
    """Session performance: RIR-adjusted e1RM (kg) for loaded lifts, best reps for
    bodyweight moves, best seconds for holds."""

    unit: Literal["kg", "reps", "s"]
    current: float | None
    best: float | None
    last: float | None
    trend_pct_week: float | None
    series: list[E1rmPoint]


class SkillGoalOut(BaseModel):
    skill_name: str
    step_name: str
    criterion: str
    sessions_met: int
    confirm_sessions: int


class TargetOut(BaseModel):
    exercise_id: int
    exercise: str
    kind: Literal["reps", "hold", "none"]
    sets: int
    reps: int | None
    seconds: int | None
    weight_kg: float
    rpe: float | None
    change: str
    reason: str
    why: str
    explanation: Why
    rep_range: list[int] | None
    increment_kg: float | None
    e1rm: E1rmOut | None
    stalled: bool
    stall_sessions: int
    skill: SkillGoalOut | None
    readiness: float | None
    kept_until: datetime | None
    deload_week: bool
    phrasing: Literal["template", "model"] = "template"
    algo_version: str


class DecisionIn(BaseModel):
    choice: Literal["accepted", "kept"]


class DecisionOut(BaseModel):
    id: int
    exercise_id: int
    decided_at: datetime
    choice: str
    reason: str
    kept_until: datetime | None
    algo_version: str


class StalledLiftOut(BaseModel):
    exercise_id: int
    exercise: str
    sessions_flat: int
    best: float | None
    unit: Literal["kg", "reps", "s"]


class ExplanationOut(BaseModel):
    """A plain-language sentence for one engine number. `text` is the local model's
    sentence only when it passed the coach guard; otherwise it is the template."""

    text: str
    template: str
    phrasing: Literal["model", "template"]
    model: str | None
    fallback: str | None
    checks: dict[str, str] | None
    facts: str
    version: str


class NoticeOut(BaseModel):
    """A System notice (deload advised, target raised, muscle recovered); the id is stable
    so the app shows each notice once."""

    id: str
    code: Literal["deload", "raised", "recovered"]
    title: str
    text: str
    at: datetime


# --- diet: adaptive TDEE and weekly insights (ADR-0018, ADR-0019) ----------------------------


class TdeePointOut(BaseModel):
    """One day of tdee-v1: the morning state after that day's weigh-in."""

    day: date
    weight_kg: float | None
    intake_kcal: float | None
    intake_used: bool
    trend_kg: float
    tdee_kcal: float
    sd_kcal: float


class TdeeWeekOut(BaseModel):
    """The calorie target set on one Monday and why it changed or held."""

    week_start: date
    target_kcal: int
    tdee_kcal: float
    sd_kcal: float
    intake_days: int
    changed: bool
    from_estimate: bool
    reason: str


class TdeeOut(BaseModel):
    """GET /intelligence/tdee: expenditure with its range, trend weight and weekly target."""

    algo_version: str
    status: Literal["cold_start", "learning", "adaptive"]
    tdee_kcal: float
    sd_kcal: float
    low_kcal: float
    high_kcal: float
    formula_tdee_kcal: float
    formula_target_kcal: int
    target_kcal: int
    target_source: Literal["formula", "adaptive"]
    target_week_start: date
    trend_kg: float | None
    days_of_data: int
    weigh_ins: int
    intake_days_7: int
    weigh_ins_7: int
    gate_days: int
    paused: bool
    reason: str
    series: list[TdeePointOut]
    weeks: list[TdeeWeekOut]
    why: Why


class InsightFindingOut(BaseModel):
    code: str
    title: str
    text: str
    severity: float
    numbers: dict[str, float | int | str]
    why: Why


class InsightCheckOut(BaseModel):
    code: str
    outcome: Literal["fired", "quiet", "not_enough_data"]
    detail: str


class InsightsOut(BaseModel):
    """GET /intelligence/insights: at most three findings for the last 7 complete days, plus
    every rule that was checked and why it stayed quiet."""

    algo_version: str
    week_end: date
    findings: list[InsightFindingOut]
    checks: list[InsightCheckOut]
