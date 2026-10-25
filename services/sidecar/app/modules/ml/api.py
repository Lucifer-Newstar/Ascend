"""On-device ML endpoints: status, the intent router, knowledge search, food photo
suggestions. All offline; nothing here logs data or changes the user's records."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.modules.ml import food_photo, intent, knowledge
from app.modules.ml.schemas import (
    Citation,
    FoodPhotoIn,
    FoodPhotoOut,
    FoodPhotoStatus,
    FoodSuggestion,
    IntentIn,
    IntentOut,
    IntentScore,
    IntentStatus,
    KnowledgeHit,
    KnowledgeOut,
    KnowledgeStatus,
    MlStatus,
)
from app.modules.nutrition.models import Food
from app.modules.progress import service as progress

router = APIRouter(prefix="/ml", tags=["ml"])

# A "food" answer needs this much confidence in the top guess; below it the UI says it is
# unsure and still lets the user pick (or search).
FOOD_SURE = 0.5


def _data_dir(request: Request) -> Path:
    path: Path = request.app.state.settings.data_dir
    return path


def _food_enabled(db: Session) -> bool:
    return progress.get_setting(db, food_photo.SETTING_KEY, "true") != "false"


@router.get("/status", response_model=MlStatus)
def ml_status(request: Request, db: Session = Depends(get_db)) -> MlStatus:
    """Which models this install has and why one is unavailable."""
    i = intent.info()
    f = food_photo.status(_data_dir(request), _food_enabled(db))
    return MlStatus(
        intent=IntentStatus(
            available=i.available,
            version=i.version,
            threshold=i.threshold,
            labels=i.labels,
            reason=i.reason,
        ),
        knowledge=KnowledgeStatus(
            available=knowledge.available(),
            passages=knowledge.size(),
            sources=sorted(knowledge.sources()),
        ),
        food_photo=FoodPhotoStatus(
            available=f.available, reason=f.reason, version=f.version, classes=f.classes
        ),
    )


@router.post("/intent", response_model=IntentOut)
def classify(body: IntentIn) -> IntentOut:
    """What the trainer-chat router thinks a message is (for the chat and for debugging)."""
    p = intent.predict(body.text)
    th = intent.threshold()
    if p is None:
        return IntentOut(
            intent=None, confidence=None, trusted=False, threshold=th, top=[], model_version=None
        )
    return IntentOut(
        intent=p.intent,
        confidence=round(p.confidence, 4),
        trusted=p.confidence >= th,
        threshold=th,
        top=[IntentScore(intent=k, confidence=v) for k, v in p.top],
        model_version=intent.info().version,
    )


@router.get("/knowledge", response_model=KnowledgeOut)
def search(
    q: str = Query(min_length=1, max_length=500),
    k: int = Query(default=3, ge=1, le=10),
) -> KnowledgeOut:
    """Top passages from the bundled knowledge base, each with its source and licence."""
    p = intent.predict(q)
    hits = knowledge.retrieve(q, k, intent=p.intent if p else None)
    return KnowledgeOut(
        query=q,
        hits=[
            KnowledgeHit(
                id=h.id,
                title=h.title,
                text=h.text,
                score=h.score,
                coverage=h.coverage,
                confident=h.confident,
                citation=Citation(**knowledge.citation(h)),
            )
            for h in hits
        ],
    )


@router.post(
    "/food-photo",
    response_model=FoodPhotoOut,
    responses={409: {"description": "No usable food model on this PC (see /ml/status)"}},
)
def food_photo_suggest(
    body: FoodPhotoIn, request: Request, db: Session = Depends(get_db)
) -> FoodPhotoOut:
    """Top-3 food suggestions for a meal photo. Never logs anything: the user confirms a
    food (or searches) and logs it through the normal meal flow."""
    from app.modules.photos import service as photos

    data_dir = _data_dir(request)
    st = food_photo.status(data_dir, _food_enabled(db))
    if not st.available:
        raise HTTPException(409, f"food photo model unavailable: {st.reason}")
    try:
        raw = photos.decode_data_url(body.data_url)
        guesses, version = food_photo.suggest(data_dir, raw)
    except (photos.PhotoError, food_photo.FoodPhotoError) as e:
        raise HTTPException(422, str(e)) from e
    rows = {f.name: f.id for f in db.scalars(select(Food))}
    out = [
        FoodSuggestion(
            label=g.label,
            food_id=rows.get(g.food_name) if g.food_name else None,
            name=g.food_name or g.label.replace("_", " "),
            confidence=g.confidence,
        )
        for g in guesses
        if g.label != food_photo.NOT_FOOD
    ]
    top = guesses[0] if guesses else None
    result: Literal["food", "not_food", "unsure"]
    if top is not None and top.label == food_photo.NOT_FOOD and top.confidence >= FOOD_SURE:
        result = "not_food"
    elif top is not None and top.confidence >= FOOD_SURE:
        result = "food"
    else:
        result = "unsure"
    return FoodPhotoOut(suggestions=out, result=result, model_version=version)
