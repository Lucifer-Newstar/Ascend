"""Base classes for request bodies."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StrictIn(BaseModel):
    """Request body that rejects unknown fields and trims whitespace around free text.

    A typo such as `{"weigth_kg": 80}` used to be dropped silently and the default
    used instead; now it is a 422 naming the field, which surfaces client bugs early.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
