from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ActionLog(Base):
    """One proposed in-app action and what became of it (the audit log)."""

    __tablename__ = "action_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(24))
    params_json: Mapped[str] = mapped_column("params", Text)
    # proposed | executed | cancelled | undone | failed
    status: Mapped[str] = mapped_column(String(10), index=True)
    # chat | command | ai | trainer
    source: Mapped[str] = mapped_column(String(10))
    origin_text: Mapped[str | None] = mapped_column(String(400), nullable=True)
    summary_json: Mapped[str] = mapped_column("summary", Text, default="[]")
    result_json: Mapped[str | None] = mapped_column("result", Text, nullable=True)
    undo_json: Mapped[str | None] = mapped_column("undo", Text, nullable=True)
    error: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    undone_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    @property
    def params(self) -> dict[str, Any]:
        return dict(json.loads(self.params_json))

    @property
    def summary(self) -> list[str]:
        return [str(s) for s in json.loads(self.summary_json or "[]")]

    @property
    def result(self) -> dict[str, Any] | None:
        return dict(json.loads(self.result_json)) if self.result_json else None
