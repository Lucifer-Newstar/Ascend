"""Progress photos: add, list, view and delete (v1.3: the AI photo feedback is removed;
photos are compared side by side by the user, never judged by a model)."""

from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_now
from app.modules.photos import service
from app.modules.photos.models import ProgressPhoto
from app.modules.photos.schemas import (
    PhotoData,
    PhotoIn,
    PhotoOut,
    PhotosDeleted,
)

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


@router.delete("", response_model=PhotosDeleted)
def delete_all_photos(request: Request, db: Session = Depends(get_db)) -> PhotosDeleted:
    """Delete every progress photo and its file from this PC (Settings > Privacy). Backups
    you made earlier keep their copies until you delete those backups."""
    return PhotosDeleted(deleted=service.delete_all(db, _data_dir(request)))


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
