"""Base classes for request bodies."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict


def to_local_naive(value: datetime) -> datetime:
    """The app stores naive local times. A client timestamp with an offset ("...Z",
    "+05:30") is converted to local time first instead of having its offset dropped,
    and it can then be compared with the stored ones (review L3)."""
    return value.astimezone().replace(tzinfo=None) if value.tzinfo is not None else value


# A datetime field of a request body, normalised to naive local time.
LocalDatetime = Annotated[datetime, AfterValidator(to_local_naive)]


class StrictIn(BaseModel):
    """Request body that rejects unknown fields and trims whitespace around free text.

    A typo such as `{"weigth_kg": 80}` used to be dropped silently and the default
    used instead; now it is a 422 naming the field, which surfaces client bugs early.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
