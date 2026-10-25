from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.core.schemas import StrictIn


class IntentStatus(BaseModel):
    available: bool
    version: str | None
    threshold: float
    labels: list[str]
    reason: str | None


class KnowledgeStatus(BaseModel):
    available: bool
    passages: int
    sources: list[str]


class FoodPhotoStatus(BaseModel):
    available: bool
    # missing | not_gated | checksum | runtime_missing | disabled | error; None when available
    reason: str | None
    version: str | None
    classes: int


class MlStatus(BaseModel):
    """What on-device ML this install has. The UI hides "Scan meal" unless
    food_photo.available is true."""

    intent: IntentStatus
    knowledge: KnowledgeStatus
    food_photo: FoodPhotoStatus


class IntentIn(StrictIn):
    text: str = Field(min_length=1, max_length=1000)


class IntentScore(BaseModel):
    intent: str
    confidence: float


class IntentOut(BaseModel):
    intent: str | None
    confidence: float | None
    # True when confidence reaches the threshold, i.e. the chat would follow the model.
    trusted: bool
    threshold: float
    top: list[IntentScore]
    model_version: str | None


class Citation(BaseModel):
    passage_id: str
    title: str
    source: str
    licence: str
    url: str
    ref: str


class KnowledgeHit(BaseModel):
    id: str
    title: str
    text: str
    score: float
    coverage: float
    confident: bool
    citation: Citation


class KnowledgeOut(BaseModel):
    query: str
    hits: list[KnowledgeHit]


class FoodPhotoIn(StrictIn):
    # A base64 data URL (data:image/jpeg;base64,...), like progress photos.
    data_url: str = Field(min_length=20)


class FoodSuggestion(BaseModel):
    label: str
    food_id: int | None
    name: str
    confidence: float


class FoodPhotoOut(BaseModel):
    """Suggestions only: nothing is logged until the user confirms a food in the meal form."""

    suggestions: list[FoodSuggestion]
    result: Literal["food", "not_food", "unsure"]
    model_version: str
    must_confirm: Literal[True] = True
