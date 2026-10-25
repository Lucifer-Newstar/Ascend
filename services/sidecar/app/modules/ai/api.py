"""AI setup endpoints: what this PC can run, which model to use, and a quick test."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.schemas import StrictIn
from app.modules.ai import setup

router = APIRouter(prefix="/ai", tags=["ai"])


class ModelInfo(BaseModel):
    name: str
    size_gb: float


class RecommendationOut(BaseModel):
    model: str | None
    size_gb: float | None
    reason: str
    pull_command: str | None


class HardwareOut(BaseModel):
    ram_gb: float | None
    vram_gb: float | None
    gpu: str | None


class AiSetup(BaseModel):
    ai_enabled: bool
    tier: Literal["rules", "ai"]
    ollama_installed: bool
    ollama_running: bool
    ollama_version: str | None
    models: list[ModelInfo]
    model: str
    model_installed: bool
    recommended: RecommendationOut
    hardware: HardwareOut
    failures: int
    suggestion: str | None
    smaller_model: str | None
    algo_version: str


class ModelIn(StrictIn):
    # None returns to the default model. A tag like "qwen3:1.7b" (letters, digits, . _ : / -).
    model: str | None = Field(default=None, max_length=80, pattern=r"^[A-Za-z0-9._:/-]+$")


class TestOut(BaseModel):
    ok: bool
    model: str
    seconds: float
    reason: str | None
    reply: str


@router.get("/setup", response_model=AiSetup)
def get_setup(request: Request, db: Session = Depends(get_db)) -> AiSetup:
    """Ollama installed/running, pulled models, RAM/VRAM, the recommended model (ai-tiers-v1)
    and the current tier. Tier "rules" is the full app without a model."""
    return AiSetup.model_validate(setup.setup(db, request.app.state.settings))


@router.put("/model", response_model=AiSetup)
def put_model(body: ModelIn, request: Request, db: Session = Depends(get_db)) -> AiSetup:
    """Pick the text model (it must be pulled in Ollama when Ollama is running)."""
    settings = request.app.state.settings
    if body.model is not None:
        current = setup.setup(db, settings)
        names = {m["name"] for m in current["models"]}  # type: ignore[attr-defined]
        if current["ollama_running"] and not (
            body.model in names or f"{body.model}:latest" in names
        ):
            raise HTTPException(422, f"{body.model} isn't pulled; run: ollama pull {body.model}")
    setup.choose(db, body.model)
    return AiSetup.model_validate(setup.setup(db, settings))


@router.post("/test", response_model=TestOut)
def post_test(request: Request, db: Session = Depends(get_db)) -> TestOut:
    """Ask the model one short question and time it."""
    return TestOut.model_validate(setup.run_test(db, request.app.state.settings))
