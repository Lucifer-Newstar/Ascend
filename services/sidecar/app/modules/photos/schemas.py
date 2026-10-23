from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.core.schemas import StrictIn

Pose = Literal["front", "side", "back", "other"]


class PhotoIn(StrictIn):
    # A base64 data URL (data:image/jpeg;base64,...). The renderer re-encodes the photo
    # through a canvas first; the sidecar strips any metadata that is still there.
    data_url: str = Field(min_length=20)
    taken_on: date
    pose: Pose = "front"
    note: str = Field(default="", max_length=200)


class PhotoOut(BaseModel):
    id: int
    taken_on: date
    pose: str
    note: str
    mime: str
    bytes: int
    created_at: datetime


class FeedbackStatus(BaseModel):
    # The user's switch (Settings > Progress photo feedback); always off under 18.
    enabled: bool
    # True when the switch is on and the local vision model answers.
    available: bool
    model: str
    reason: str


class FeedbackIn(StrictIn):
    older_id: int
    newer_id: int


class FeedbackOut(BaseModel):
    text: str
    # True when the guard removed part of the model's reply.
    guarded: bool
    model: str
    version: str
    is_ai: bool = True
