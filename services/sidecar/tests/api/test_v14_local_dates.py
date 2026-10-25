"""v1.4: seasons, drops and the local clock (Navin, 2026-10-25)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.modules.gamification import boss


def _catalog_ids() -> set[str] | None:
    for parent in Path(__file__).resolve().parents:
        f = parent / "apps/desktop/src/lib/cosmetics.ts"
        if f.is_file():
            return set(re.findall(r'id: "([a-z0-9_]+)"', f.read_text("utf-8")))
    return None


def test_every_seasonal_drop_is_a_real_cosmetic() -> None:
    ids = _catalog_ids()
    if ids is None:
        pytest.skip("no apps/desktop in this checkout")
    assert {s.drop for s in boss.SEASONS} <= ids
