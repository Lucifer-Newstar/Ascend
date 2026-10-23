"""Progress photos on disk. Files live in <data dir>/photos/ and never leave the PC
unless the user exports one or makes a backup."""

from __future__ import annotations

import base64
import binascii
import secrets
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.reset import PHOTOS_DIR
from app.modules.photos import strip
from app.modules.photos.models import ProgressPhoto

MAX_BYTES = 12 * 1024 * 1024
MAX_PHOTOS = 500
POSES = ("front", "side", "back", "other")


class PhotoError(ValueError):
    pass


def photos_dir(data_dir: Path) -> Path:
    d = data_dir / PHOTOS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def decode_data_url(data_url: str) -> bytes:
    head, _, payload = data_url.partition(",")
    if not head.startswith("data:image/") or ";base64" not in head or not payload:
        raise PhotoError("send the photo as a base64 data URL")
    if len(payload) > MAX_BYTES * 4 // 3 + 4:
        raise PhotoError("that photo is larger than 12 MB")
    try:
        return base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as e:
        raise PhotoError("the photo data is not valid base64") from e


def save(
    db: Session,
    data_dir: Path,
    raw: bytes,
    taken_on: date,
    pose: str,
    note: str,
    now: datetime,
) -> ProgressPhoto:
    if pose not in POSES:
        raise PhotoError(f"pose must be one of {', '.join(POSES)}")
    if taken_on > now.date():
        raise PhotoError("a progress photo cannot be dated in the future")
    if len(raw) > MAX_BYTES:
        raise PhotoError("that photo is larger than 12 MB")
    if (db.scalar(select(func.count(ProgressPhoto.id))) or 0) >= MAX_PHOTOS:
        raise PhotoError(f"you can keep up to {MAX_PHOTOS} photos; delete some first")
    try:
        clean, mime = strip.strip(raw)
    except strip.NotAnImage as e:
        raise PhotoError(str(e)) from e
    ext = "jpg" if mime == "image/jpeg" else "png"
    name = f"{taken_on.isoformat()}-{secrets.token_hex(8)}.{ext}"
    path = photos_dir(data_dir) / name
    path.write_bytes(clean)
    row = ProgressPhoto(
        taken_on=taken_on,
        pose=pose,
        filename=name,
        mime=mime,
        bytes=len(clean),
        note=note.strip()[:200],
        created_at=now,
    )
    db.add(row)
    db.flush()
    return row


def listing(db: Session) -> list[ProgressPhoto]:
    return list(
        db.scalars(
            select(ProgressPhoto).order_by(ProgressPhoto.taken_on.desc(), ProgressPhoto.id.desc())
        ).all()
    )


def get(db: Session, photo_id: int) -> ProgressPhoto:
    row = db.get(ProgressPhoto, photo_id)
    if row is None:
        raise LookupError("photo not found")
    return row


def file_path(data_dir: Path, row: ProgressPhoto) -> Path:
    path = (data_dir / PHOTOS_DIR / row.filename).resolve()
    if path.parent != (data_dir / PHOTOS_DIR).resolve() or not path.is_file():
        raise LookupError("the photo file is missing from the data folder")
    return path


def delete(db: Session, data_dir: Path, photo_id: int) -> None:
    row = get(db, photo_id)
    path = data_dir / PHOTOS_DIR / row.filename
    db.delete(row)
    db.flush()
    path.unlink(missing_ok=True)


def last_photo(db: Session) -> date | None:
    return db.scalar(select(func.max(ProgressPhoto.taken_on)))
