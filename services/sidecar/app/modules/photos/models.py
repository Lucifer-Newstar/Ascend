from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ProgressPhoto(Base):
    """One progress photo. The image itself is a file under <data dir>/photos/, written
    without metadata (no EXIF, no GPS, no camera serial)."""

    __tablename__ = "progress_photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    taken_on: Mapped[date] = mapped_column(Date, index=True)
    # front | side | back | other
    pose: Mapped[str] = mapped_column(String(8), default="front")
    filename: Mapped[str] = mapped_column(String(64), unique=True)
    mime: Mapped[str] = mapped_column(String(16))
    bytes: Mapped[int] = mapped_column(Integer)
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime)
