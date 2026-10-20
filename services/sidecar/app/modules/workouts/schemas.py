from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.schemas import StrictIn


class MuscleWeight(BaseModel):
    muscle: str
    weight: float


class ExerciseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    equipment: str
    section: str = "gym"
    met: float | None = None
    time_based: bool = False
    muscles: list[MuscleWeight]
    slug: str | None = None
    # reps | hold (seconds per set) | time (cardio, stretching, meditation)
    measure: str = "reps"
    difficulty: str | None = None
    pattern: str = "other"
    image: str | None = None
    # ascend | free-exercise-db | custom
    source: str = "ascend"
    is_custom: bool = False
    aliases: list[str] = []


class SkillLinkOut(BaseModel):
    skill_key: str
    skill_name: str
    step_name: str | None = None
    # "step": the exercise is a step of the tree; "feeder": it builds strength for it
    role: str


class AttributionOut(BaseModel):
    source: str
    title: str
    url: str
    license: str


class ExerciseDetail(ExerciseOut):
    instructions: list[str] = []
    mechanic: str | None = None
    rep_low: int | None = None
    rep_high: int | None = None
    # field -> library | rules | local_ai | wger | wikipedia | user
    field_sources: dict[str, str] = {}
    attribution: list[AttributionOut] = []
    source_ref: str | None = None
    created_at: datetime | None = None
    skills: list[SkillLinkOut] = []
    sets_logged: int = 0


FieldSource = Literal["library", "rules", "local_ai", "wger", "user"]


class ExerciseAnalyzeIn(StrictIn):
    name: str = Field(min_length=2, max_length=80)
    equipment: str | None = Field(default=None, max_length=20)
    notes: str = Field(default="", max_length=300)
    # Ask for online research (wger.de, Wikipedia). Honoured only when Settings ->
    # "Online research" is on or allow_once is set; otherwise no request is sent.
    online: bool = False
    # The user allowed online research for this one lookup ("Allow once").
    allow_once: bool = False


class ExerciseProposal(BaseModel):
    section: str
    equipment: str
    measure: str
    pattern: str
    difficulty: str | None = None
    muscles: list[MuscleWeight] = []
    rep_low: int | None = None
    rep_high: int | None = None
    met: float | None = None
    instructions: list[str] = []
    aliases: list[str] = []


class ExerciseMatch(BaseModel):
    id: int
    name: str
    score: float
    # exact | alias | fuzzy
    via: str
    section: str
    image: str | None = None


class StageStatus(BaseModel):
    """What one optional stage did. local_ai: ok | off | unavailable | error | invalid.
    online: off | not_requested | ok | not_found | offline | timeout | rate_limited |
    error."""

    status: str
    detail: str = ""
    model: str | None = None
    applied: list[str] = []


class ResearchCall(BaseModel):
    source: str  # wger | wikipedia
    url: str
    # ok | not_found | offline | timeout | rate_limited | error | skipped
    status: str


class ResearchField(BaseModel):
    field: str
    label: str
    value: str
    source: str
    url: str
    offline_value: str
    offline_source: str
    # The online value differs from the offline guess.
    conflict: bool


class ResearchReport(BaseModel):
    """What online research asked, where, and which fields it would fill. Nothing is
    saved until the user confirms the review form."""

    query: str
    # setting | once
    consent: str
    outcome: str
    calls: list[ResearchCall] = []
    fields: list[ResearchField] = []
    summary: str = ""
    summary_url: str = ""


class ExerciseAnalysis(BaseModel):
    name: str
    proposal: ExerciseProposal
    # field -> library | rules | local_ai | wger
    field_sources: dict[str, str]
    # field -> high | medium | low
    confidence: dict[str, str] = {}
    # Core fields the offline stages could not support; non-empty means "not enough
    # offline data" and the client offers online research.
    insufficient: list[str] = []
    # The proposal before online research changed it (to compare or revert a field).
    offline: ExerciseProposal | None = None
    offline_sources: dict[str, str] = {}
    research: ResearchReport | None = None
    attribution: list[AttributionOut] = []
    matches: list[ExerciseMatch] = []
    # Set when the name (or an alias) already exists: creating it would be refused.
    duplicate_of: ExerciseMatch | None = None
    ai: StageStatus
    online: StageStatus


class CustomExerciseIn(StrictIn):
    """A reviewed custom exercise. field_sources says where each field came from; the
    client marks fields the user changed as "user"."""

    name: str = Field(min_length=2, max_length=80)
    section: Literal["gym", "calisthenics", "cardio", "martial_arts", "flexibility", "meditation"]
    equipment: str = Field(min_length=2, max_length=20, pattern=r"^[a-z_]+$")
    measure: Literal["reps", "hold", "time"]
    pattern: Literal[
        "push", "pull", "squat", "hinge", "lunge", "core", "isometric",
        "carry", "olympic", "locomotion", "mobility", "other",
    ]  # fmt: skip
    difficulty: Literal["beginner", "intermediate", "expert"] | None = None
    muscles: list[MuscleWeight] = Field(default=[], max_length=8)
    rep_low: int | None = Field(default=None, ge=1, le=600)
    rep_high: int | None = Field(default=None, ge=1, le=600)
    met: float | None = Field(default=None, ge=1.0, le=23.0)
    instructions: list[Annotated[str, Field(max_length=300)]] = Field(default=[], max_length=12)
    aliases: list[Annotated[str, Field(max_length=60)]] = Field(default=[], max_length=10)
    field_sources: dict[str, FieldSource] = {}
    attribution: list[AttributionOut] = Field(default=[], max_length=3)

    @model_validator(mode="after")
    def _consistent(self) -> CustomExerciseIn:
        from app.modules.progress.taxonomy import MUSCLE_BY_KEY

        seen: set[str] = set()
        for m in self.muscles:
            if m.muscle not in MUSCLE_BY_KEY:
                raise ValueError(f"unknown muscle region '{m.muscle}'")
            if m.muscle in seen:
                raise ValueError(f"muscle '{m.muscle}' listed twice")
            if not 0.25 <= m.weight <= 1.0:
                raise ValueError("muscle weights must be between 0.25 and 1")
            seen.add(m.muscle)
        if self.section not in ("meditation", "flexibility") and not self.muscles:
            raise ValueError("pick at least one muscle region")
        if sum(1 for m in self.muscles if m.weight >= 1.0) > 3:
            # One set counts as a hard set for every primary muscle; more than 3 would let
            # a single custom exercise tick every muscle quest at once.
            raise ValueError("at most 3 primary muscles; mark the rest as secondary")
        timed = self.section in ("cardio", "martial_arts", "flexibility", "meditation")
        if timed != (self.measure == "time"):
            raise ValueError(
                "cardio, martial arts, mobility and mind exercises are measured in time; "
                "strength and calisthenics in reps or holds"
            )
        if self.rep_low and self.rep_high and self.rep_low > self.rep_high:
            raise ValueError("rep_low must not exceed rep_high")
        if self.met is not None and self.measure != "time":
            raise ValueError("met only applies to time-based exercises")
        return self


class SetIn(StrictIn):
    """One set. Lifts send weight + reps; time-based sections send duration_s
    (and distance_m for cardio). The service checks the right fields are present."""

    exercise_id: int
    weight_kg: float = Field(default=0, ge=0, le=500)
    reps: int = Field(default=1, ge=1, le=100)
    rpe: float | None = Field(default=None, ge=1, le=10)
    duration_s: int | None = Field(default=None, ge=1, le=6 * 3600)
    distance_m: float | None = Field(default=None, ge=0, le=300_000)
    avg_hr: int | None = Field(default=None, ge=30, le=230)


class SetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    exercise_id: int
    exercise_name: str
    weight_kg: float
    reps: int
    rpe: float | None
    duration_s: int | None = None
    distance_m: float | None = None
    avg_hr: int | None = None
    e1rm: float | None
    is_pr: bool
    performed_at: datetime
    # The exercise's measure, so a client can show "45 s hold" without a lookup.
    measure: str = "reps"


class PreviousSession(BaseModel):
    """GET /exercises/{id}/previous: the last finished session's sets of one exercise."""

    workout_id: int
    day: date
    source: str
    sets: list[SetOut]


class UnlockedStep(BaseModel):
    """A skill-tree step this set unlocked (mirrors skills.schemas.SkillUnlockOut)."""

    id: int
    skill_key: str
    skill_name: str
    step_key: str
    step_name: str
    unlocked_at: datetime
    xp: int
    final: bool
    next_step_name: str | None = None
    source: str = "log"


class LoggedSet(BaseModel):
    set: SetOut
    xp_awarded: int
    previous_best_e1rm: float | None
    # Skill steps unlocked by this set ("Skill acquired" moments), usually empty.
    unlocks: list[UnlockedStep] = []


class WorkoutOut(BaseModel):
    id: int
    day: date
    section: str = "gym"
    started_at: datetime
    finished_at: datetime | None
    sets: list[SetOut]
    source: str = "app"
    title: str = ""


class FinishedWorkout(BaseModel):
    workout: WorkoutOut
    xp_awarded: int
    active_minutes: float
    hard_sets: int


class WorkoutSummary(BaseModel):
    id: int
    day: date
    section: str = "gym"
    started_at: datetime
    finished_at: datetime | None
    sets: int
    volume_kg: float
    xp: int
    # "app", or the app an imported session came from ("strong", "hevy").
    source: str = "app"
    title: str = ""


class SetPatch(StrictIn):
    """Partial edit of a logged set; omitted fields keep their value."""

    weight_kg: float | None = Field(default=None, ge=0, le=500)
    reps: int | None = Field(default=None, ge=1, le=100)
    rpe: float | None = Field(default=None, ge=1, le=10)
    duration_s: int | None = Field(default=None, ge=1, le=6 * 3600)
    distance_m: float | None = Field(default=None, ge=0, le=300_000)


class PROut(BaseModel):
    exercise_id: int
    exercise: str
    type: str = "e1rm"
    value: float
    weight_kg: float
    reps: int
    formula: str = "epley"
    algo_version: str
    achieved_at: datetime
    set_id: int


class OnlineLogEntry(BaseModel):
    id: int
    at: datetime
    query: str
    sources: list[ResearchCall] = []
    outcome: str
    # setting | once
    consent: str
