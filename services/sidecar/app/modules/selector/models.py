from __future__ import annotations

import json
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class SelectorPick(Base):
    """One thing the trainer posted on its own (select-v1), with why. Every proactive post
    goes through here: catalog items, watcher events and System notices."""

    __tablename__ = "selector_picks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    # catalog | watch | system
    source: Mapped[str] = mapped_column(String(8))
    item_id: Mapped[str] = mapped_column(String(120), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    text: Mapped[str] = mapped_column(String(400))
    why_json: Mapped[str] = mapped_column("why", Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime)

    @property
    def why(self) -> list[str]:
        return [str(w) for w in json.loads(self.why_json or "[]")]
