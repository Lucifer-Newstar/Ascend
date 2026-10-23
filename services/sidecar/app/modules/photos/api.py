"""Progress photos: add, list, view, delete, and optional local AI comparison."""

from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_now
from app.modules.coach import ollama
from app.modules.photos import service, vision
from app.modules.photos.models import ProgressPhoto
from app.modules.photos.schemas import (
    FeedbackIn,
    FeedbackOut,
    FeedbackStatus,
    PhotoData,
    PhotoIn,
    PhotoOut,
)
from app.modules.progress import service as progress

router = APIRouter(prefix="/photos", tags=["photos"])


def _data_dir(request: Request) -> Path:
    return Path(request.app.state.settings.data_dir)


def _out(row: ProgressPhoto) -> PhotoOut:
    return PhotoOut(
        id=row.id,
        taken_on=row.taken_on,
        pose=row.pose,
        note=row.note,
        mime=row.mime,
        bytes=row.bytes,
        created_at=row.created_at,
    )


@router.get("", response_model=list[PhotoOut])
def list_photos(db: Session = Depends(get_db)) -> list[PhotoOut]:
    """Every progress photo, newest first (metadata only; the image is /photos/{id}/file)."""
    return [_out(r) for r in service.listing(db)]


@router.post("", response_model=PhotoOut, status_code=201)
def add_photo(
    body: PhotoIn,
    request: Request,
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> PhotoOut:
    """Store a progress photo in the data folder with its metadata (EXIF, GPS) removed."""
    try:
        raw = service.decode_data_url(body.data_url)
        row = service.save(db, _data_dir(request), raw, body.taken_on, body.pose, body.note, now)
    except service.PhotoError as e:
        raise HTTPException(422, str(e)) from e
    return _out(row)


@router.get(
    "/{photo_id}/file",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}, "image/png": {}}}},
)
def photo_file(photo_id: int, request: Request, db: Session = Depends(get_db)) -> Response:
    """The image itself, as stored (already without metadata). Also what Export saves."""
    try:
        row = service.get(db, photo_id)
        path = service.file_path(_data_dir(request), row)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    return Response(path.read_bytes(), media_type=row.mime, headers={"Cache-Control": "no-store"})


@router.get("/{photo_id}/data", response_model=PhotoData)
def photo_data(photo_id: int, request: Request, db: Session = Depends(get_db)) -> PhotoData:
    """The image as a data URL, for the desktop renderer (its bridge to the sidecar carries
    JSON only). Same bytes as /file: already without metadata."""
    try:
        row = service.get(db, photo_id)
        path = service.file_path(_data_dir(request), row)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    encoded = base64.b64encode(path.read_bytes()).decode()
    return PhotoData(id=row.id, mime=row.mime, data_url=f"data:{row.mime};base64,{encoded}")


@router.delete("/{photo_id}", status_code=204)
def delete_photo(photo_id: int, request: Request, db: Session = Depends(get_db)) -> None:
    """Delete the photo and its file."""
    try:
        service.delete(db, _data_dir(request), photo_id)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


def _status(request: Request, db: Session) -> FeedbackStatus:
    settings = request.app.state.settings
    model = settings.vision_model
    profile = progress.get_profile(db)
    if profile is not None and profile.age < vision.MIN_AGE:
        return FeedbackStatus(
            enabled=False, available=False, model=model, reason="Off for under-18s."
        )
    if not progress.read_settings(db).photo_feedback:
        return FeedbackStatus(
            enabled=False,
            available=False,
            model=model,
            reason="Off. Turn on Progress photo feedback in Settings to use it.",
        )
    if not ollama.is_available(settings.ollama_host, model):
        return FeedbackStatus(
            enabled=True,
            available=False,
            model=model,
            reason=f"The local vision model is not installed. Run: ollama pull {model}",
        )
    return FeedbackStatus(enabled=True, available=True, model=model, reason="Ready.")


@router.get("/feedback/status", response_model=FeedbackStatus)
def feedback_status(request: Request, db: Session = Depends(get_db)) -> FeedbackStatus:
    """Whether AI photo feedback can run: the user's switch, the age rule, the model."""
    return _status(request, db)


@router.post(
    "/feedback",
    response_model=FeedbackOut,
    responses={409: {"description": "Feedback is off or the model is missing"}},
)
def photo_feedback(
    body: FeedbackIn, request: Request, db: Session = Depends(get_db)
) -> FeedbackOut:
    """Compare two photos with the local vision model. Never estimates body fat or weight,
    never comments on looks; the reply passes a guard before you see it."""
    status = _status(request, db)
    if not status.available:
        raise HTTPException(409, status.reason)
    try:
        rows = [service.get(db, body.older_id), service.get(db, body.newer_id)]
        rows.sort(key=lambda r: (r.taken_on, r.id))
        data = [service.file_path(_data_dir(request), r).read_bytes() for r in rows]
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    settings = request.app.state.settings
    try:
        raw = vision.compare(settings.ollama_host, status.model, data[0], data[1])
    except ollama.OllamaUnavailable as e:
        raise HTTPException(409, f"The vision model did not answer: {e}") from e
    text, guarded = vision.guard(raw)
    return FeedbackOut(
        text=text, guarded=guarded, model=status.model, version=vision.VISION_VERSION
    )
