"""Every library exercise either has a bundled photo that exists on disk or is meant to use
the renderer's designed tile; no row points at a missing or empty picture."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.modules.workouts.library import IMAGE_STANDINS, standin_image

PUBLIC = Path(__file__).resolve().parents[4] / "apps" / "desktop" / "public"


def _rows(settings: Settings) -> list[tuple[str, str | None, str, str]]:
    db = settings.db_url.removeprefix("sqlite:///")
    with sqlite3.connect(db) as conn:
        return list(conn.execute("SELECT name, image, source, field_sources FROM exercises"))


def _webp_width(head: bytes) -> int:
    """Width from a lossy (VP8) webp header; the thumbnails are all lossy."""
    assert head[12:16] == b"VP8 "
    return int.from_bytes(head[26:28], "little") & 0x3FFF


def test_every_image_exists_and_is_a_small_webp(client: TestClient, settings: Settings) -> None:
    rows = _rows(settings)
    with_image = [r for r in rows if r[1]]
    assert len(rows) > 900
    assert len(with_image) >= 880
    seen: set[str] = set()
    for name, image, _source, _fs in with_image:
        assert image is not None
        if image in seen:
            continue
        seen.add(image)
        path = PUBLIC / image
        assert path.is_file(), f"{name}: {image} is missing"
        assert path.stat().st_size > 500, f"{name}: {image} is empty"
        head = path.read_bytes()[:30]
        assert head[:4] == b"RIFF" and head[8:12] == b"WEBP", f"{image} is not a webp"
        assert _webp_width(head) == 320, f"{image} is not 320 px wide"


def test_bundle_stays_small() -> None:
    files = list((PUBLIC / "exercises").glob("*.webp"))
    assert len(files) >= 873
    total = sum(f.stat().st_size for f in files)
    assert total < 25 * 1024 * 1024


def test_curated_standins_are_applied_and_labelled(client: TestClient, settings: Settings) -> None:
    by_name = {r[0]: r for r in _rows(settings) if r[2] == "ascend"}
    for name in IMAGE_STANDINS:
        found = standin_image(name)
        assert found is not None
        assert by_name[name][1] == found[0]
        assert f'"image": "similar:{found[1]}"' in by_name[name][3]
