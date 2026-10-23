from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.schemas import StrictIn

Mood = Literal["neutral", "proud", "warning", "hyped"]
TrainerId = Literal["iskra", "vera", "kai", "dario"]


class ChatIn(StrictIn):
    text: str = Field(default="", max_length=1000)


class ChatAction(BaseModel):
    """Something the UI can do for the user from a reply: open a section, start a tour,
    open the planner or the trainer picker, or show an action card (proposal_id)."""

    kind: Literal["navigate", "tour", "planner", "trainer_picker", "proposal", "share"]
    target: str | None = None
    label: str


class ChatOut(BaseModel):
    reply: str
    mood: Mood
    intent: str
    source: Literal["rules", "faq", "ollama"]
    # Why a rule-based answer stands in for the model's: ai_disabled | ollama_unavailable |
    # timeout | model_error | guard_rejected. None when the rules were the right answer.
    fallback_reason: str | None = None
    actions: list[ChatAction] = []
    suggestions: list[str] = []
    faq_id: str | None = None
    proposal: dict[str, Any] | None = None


class FeedMessage(BaseModel):
    id: int
    kind: str
    mood: Mood
    text: str
    action_kind: str | None
    action_target: str | None
    share: dict[str, Any] | None
    # Why the trainer posted it (select-v1); the trainer can repeat it when asked "why?".
    why: list[str] = []
    created_at: datetime
    read: bool


class FeedOut(BaseModel):
    messages: list[FeedMessage]
    unread: int
    algo_version: str


class FeedReadIn(StrictIn):
    ids: list[int] | None = None  # None: mark everything read


class TrainerState(BaseModel):
    onboarded: bool
    has_profile: bool
    has_history: bool
    demo_data: bool
    trainer_id: TrainerId
    tours_done: list[str]


class TrainerStateIn(StrictIn):
    onboarded: bool | None = None
    tour_done: str | None = Field(default=None, max_length=24)


class KbEntryOut(BaseModel):
    id: str
    question: str
    section: str | None
