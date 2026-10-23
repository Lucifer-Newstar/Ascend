from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class TrainerMessage(Base):
    """Something the trainer noticed (watch-v1). `key` makes each event post once."""

    __tablename__ = "trainer_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(120), unique=True)
    kind: Mapped[str] = mapped_column(String(24))
    mood: Mapped[str] = mapped_column(String(10))
    text: Mapped[str] = mapped_column(String(400))
    action_kind: Mapped[str | None] = mapped_column(String(16), nullable=True)
    action_target: Mapped[str | None] = mapped_column(String(40), nullable=True)
    share_json: Mapped[str | None] = mapped_column("share", Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    @property
    def share(self) -> dict[str, object] | None:
        return json.loads(self.share_json) if self.share_json else None
