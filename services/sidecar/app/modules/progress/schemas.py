from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import LocalDatetime, StrictIn


class ProfileIn(BaseModel):
    # PUT /profile is a whole-object update and clients echo back what GET returned,
    # so read-only fields such as `energy` are ignored rather than rejected.
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    name: str = Field(default="", max_length=80)
    age: int = Field(ge=13, le=100)
    sex: Literal["male", "female"]
    height_cm: float = Field(ge=100, le=250)
    weight_kg: float = Field(ge=30, le=300)
    goal: Literal["cut", "maintain", "bulk"]
    activity: Literal["sedentary", "light", "moderate", "active", "very_active"] = "moderate"
    target_weight_kg: float | None = Field(default=None, ge=30, le=300)
    # Onboarding answers. Equipment: an empty list means "not stated" (nothing filtered).
    focus: Literal["strength", "muscle", "skills", "fat_loss"] | None = None
    equipment: list[Literal["none", "pullup_bar", "rings", "dumbbells", "bench", "gym"]] = Field(
        default_factory=list, max_length=5
    )
    # v1.1: training age (the planner sizes volume and the goal check its limits by it).
    experience: Literal["beginner", "intermediate", "advanced"] | None = None


class BaselineIn(StrictIn):
    """The Awakening baseline test. Zero or null means "not done"; at least one result."""

    pushups: int | None = Field(default=None, ge=0, le=200)
    pullups: int | None = Field(default=None, ge=0, le=60)
    dead_hang_s: int | None = Field(default=None, ge=0, le=600)
    plank_s: int | None = Field(default=None, ge=0, le=1800)
    squats_60s: int | None = Field(default=None, ge=0, le=120)
    bodyweight_kg: float | None = Field(default=None, ge=30, le=300)


class BaselineResult(BaseModel):
    pushups: int | None = None
    pullups: int | None = None
    dead_hang_s: int | None = None
    plank_s: int | None = None
    squats_60s: int | None = None
    bodyweight_kg: float | None = None
    taken_at: datetime


class BaselineOut(BaseModel):
    baseline: BaselineResult
    workout_id: int
    sets_logged: int
    xp_awarded: int
    level: int
    rank: str
    # Skill-tree steps the baseline sets unlocked ("Skill: Step"); often none, since most
    # steps need two sessions.
    steps_unlocked: list[str]


class EnergyTargets(BaseModel):
    bmr: int
    tdee: int
    kcal_target: int
    protein_target_g: int
    formula_version: str
    is_estimate: bool = True


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)
    energy: EnergyTargets
    baseline: BaselineResult | None = None


class MuscleStateOut(BaseModel):
    key: str
    label: str
    group: str
    map_slug: str
    status: Literal["under", "optimal", "recovering", "over", "no_data"]
    es_7d: float
    weekly_low: float
    weekly_high: float
    readiness: float
    ready_at: datetime | None
    # recovery-v2: the same muscle with the population decay (k = 1), for "population vs
    # you", and the engine version that produced these numbers.
    readiness_population: float = 1.0
    algo_version: str = "recovery-v2"
    # taxonomy v2 (muscles-v2): where the muscle sits and how the map draws it.
    region: str = ""
    parent: str = ""
    deep: bool = False
    readiness_only: bool = False


Units = Literal["metric", "imperial"]
TrainerId = Literal["iskra", "vera", "kai", "dario"]
# v1.2: "dark" / "light" / "system" are the v1.1 looks (kept as free themes); the rest are
# the v1.2 themes (gamification/themes.py says which are unlocked).
Theme = Literal["dark", "light", "system", "shadow", "crimson", "frost", "emerald", "solar"]
BackgroundArt = Literal["on", "dim", "off"]
AvatarLook = Literal["male", "female"]
# A cosmetic id from the app's catalog ("" = nothing in that slot). The catalog and its
# unlock rules live in the app (new item = art + one entry); the sidecar stores the pick.
CosmeticId = Annotated[str, Field(max_length=40, pattern=r"^[a-z0-9_]*$")]


class SettingsOut(BaseModel):
    ai_enabled: bool
    units: Units = "metric"
    theme: Theme = "shadow"
    sessions_per_week: int = 3
    reduce_motion: bool = False
    # Off by default: when on, "Add your own exercise" may ask wger.de (the only
    # feature that contacts the internet, and only when the user asks per exercise).
    online_lookup: bool = False
    # v8: insights spoken by the trainer character (Instructor Iskra Vey); off = plain mode.
    trainer: bool = True
    # v1.1: which trainer speaks (iskra, vera, kai, dario).
    trainer_id: TrainerId = "iskra"
    # v1.1: hide calorie numbers across the app (targets still work underneath).
    hide_calories: bool = False
    # v1.1: local AI feedback on progress photos. Off by default; always off under 18.
    photo_feedback: bool = False
    # v1.2: the theme's background art behind the pages: on, dimmed, or off (plain colour).
    background_art: BackgroundArt = "on"
    # v1.2: the avatar's look (body-neutral: rank shows as gear and aura, never body
    # changes), what it wears, and whether faith-flavoured themed cosmetics are shown.
    avatar: AvatarLook = "male"
    outfit: str = ""
    relic: str = ""
    pet: str = ""
    weapon: str = ""
    themed_cosmetics: bool = True
    # v1.2: the trainer's reminders (today's workout, a missed day's reason, streak at
    # risk, water, check-in) as a desktop notification and a bubble on Today.
    reminders: bool = True


class SettingsIn(StrictIn):
    """Partial update: only the fields sent are changed."""

    ai_enabled: bool | None = None
    units: Units | None = None
    theme: Theme | None = None
    sessions_per_week: int | None = Field(default=None, ge=1, le=7)
    reduce_motion: bool | None = None
    online_lookup: bool | None = None
    trainer: bool | None = None
    trainer_id: TrainerId | None = None
    hide_calories: bool | None = None
    photo_feedback: bool | None = None
    background_art: BackgroundArt | None = None
    avatar: AvatarLook | None = None
    outfit: CosmeticId | None = None
    relic: CosmeticId | None = None
    pet: CosmeticId | None = None
    weapon: CosmeticId | None = None
    themed_cosmetics: bool | None = None
    reminders: bool | None = None


class BodyMetricIn(StrictIn):
    measured_at: LocalDatetime | None = None
    weight_kg: float = Field(ge=20, le=300)
    waist_cm: float | None = Field(default=None, ge=30, le=250)
    resting_hr: int | None = Field(default=None, ge=25, le=150)


class BodyMetricOut(BaseModel):
    id: int
    measured_at: datetime
    weight_kg: float
    trend_kg: float
    waist_cm: float | None
    resting_hr: int | None


MeasurementSite = Literal["waist", "hips", "chest", "arm", "thigh", "calf", "neck"]


class MeasurementIn(StrictIn):
    measured_at: LocalDatetime | None = None
    site: MeasurementSite
    cm: float = Field(ge=10, le=250)


class MeasurementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    measured_at: datetime
    site: str
    cm: float
    change_cm: float | None = None


class EtaOut(BaseModel):
    goal_kg: float | None
    current_trend_kg: float | None
    rate_kg_per_week: float | None
    eta_from: date | None
    eta_to: date | None
    confidence: Literal["low", "medium", "high"]
    on_track: bool
    reason: str | None
    formula_version: str
    note: Literal["Estimate, not a promise"] = "Estimate, not a promise"


class CheckinIn(StrictIn):
    sleep: int = Field(ge=1, le=5)
    energy: int = Field(ge=1, le=5)
    soreness: Literal["none", "some", "a_lot"]
    mood: int = Field(ge=1, le=5)


class CheckinOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    day: date
    sleep: int
    energy: int
    soreness: str
    mood: int
    readiness: int
    band: Literal["green", "amber", "red"]
    quest_adjustment: str
    algo_version: str
