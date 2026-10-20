from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class SkillUnlock(Base):
    """A skill-tree step the user has unlocked. One row per (skill, step), ever: the XP
    for a step is paid once. Removed (and its XP reversed) only if the sets that proved
    it are deleted or edited so the step no longer holds."""

    __tablename__ = "skill_unlocks"
    __table_args__ = (UniqueConstraint("skill_key", "step_key", name="uq_skill_step"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    skill_key: Mapped[str] = mapped_column(String(32), index=True)
    step_key: Mapped[str] = mapped_column(String(40))
    unlocked_at: Mapped[datetime] = mapped_column(DateTime)
    # log | import | edit
    source: Mapped[str] = mapped_column(String(12), default="log")
    trigger_set_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_json: Mapped[str] = mapped_column("evidence", Text, default="[]")
    engine_version: Mapped[str] = mapped_column(String(16))

    @property
    def evidence(self) -> list[int]:
        return [int(i) for i in json.loads(self.evidence_json or "[]")]
