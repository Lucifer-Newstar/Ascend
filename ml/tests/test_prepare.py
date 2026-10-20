from __future__ import annotations

import json
import random
from pathlib import Path

from PIL import Image

from common import TEST_OWN, read_manifest
from make_smoke_data import draw_sample
from prepare import prepare

PARAMS = {"prepare": {"val_split": 0.2, "test_split": 0.2, "seed": 1, "min_side": 64}}


def make_raw(tmp: Path) -> Path:
    raw = tmp / "raw"
    rng = random.Random(3)
    for i, label in enumerate(["idli", "dosa"]):
        (raw / label).mkdir(parents=True)
        (raw / f"_{TEST_OWN}" / label).mkdir(parents=True)
        for j in range(10):
            draw_sample(i, rng).save(raw / label / f"{j}.png")
        for j in range(2):
            draw_sample(i, rng).save(raw / f"_{TEST_OWN}" / label / f"own{j}.png")
    first = raw / "idli" / "0.png"
    (raw / "idli" / "copy.png").write_bytes(first.read_bytes())
    Image.new("RGB", (32, 32)).save(raw / "dosa" / "tiny.png")
    return raw


def test_dedupes_and_drops_tiny(tmp_path: Path) -> None:
    report = prepare(make_raw(tmp_path), tmp_path / "out", PARAMS)
    assert report["dropped"]["exact_duplicate"] == 1
    assert report["dropped"]["too_small"] == 1
    assert report["images"] == 24
    assert json.loads((tmp_path / "out" / "classes.json").read_text()) == ["dosa", "idli"]


def test_team_photos_only_in_test(tmp_path: Path) -> None:
    prepare(make_raw(tmp_path), tmp_path / "out", PARAMS)
    rows = read_manifest(tmp_path / "out" / "manifest.csv")
    own = [r for r in rows if r.tag == TEST_OWN]
    assert len(own) == 4
    assert {r.split for r in own} == {"test"}
    assert {r.split for r in rows if r.tag == ""} == {"train", "val", "test"}


def test_split_is_deterministic(tmp_path: Path) -> None:
    raw = make_raw(tmp_path)
    prepare(raw, tmp_path / "a", PARAMS)
    prepare(raw, tmp_path / "b", PARAMS)
    a = [(r.sha256, r.split) for r in read_manifest(tmp_path / "a" / "manifest.csv")]
    b = [(r.sha256, r.split) for r in read_manifest(tmp_path / "b" / "manifest.csv")]
    assert a == b
