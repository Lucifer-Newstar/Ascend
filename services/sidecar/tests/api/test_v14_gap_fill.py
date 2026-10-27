"""v1.4: the gap-fill moves and the dataset dishes reach a migrated database."""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.core.config import Settings


def steps(settings: Settings, name: str) -> list[str]:
    engine = sa.create_engine(settings.db_url)
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT instructions FROM exercises WHERE name = :n"), {"n": name}
        ).scalar_one()
    engine.dispose()
    return json.loads(row or "[]")


def test_new_moves_and_written_steps_are_in_the_library(
    client: TestClient, settings: Settings
) -> None:
    found = [e["name"] for e in client.get("/exercises", params={"q": "knee push"}).json()]
    assert "Knee Push-up" in found
    assert len(steps(settings, "Knee Push-up")) >= 3
    assert len(steps(settings, "Box Breathing")) >= 3
    assert len(steps(settings, "Shadowboxing")) >= 3


def test_dataset_dishes_are_in_the_food_table(client: TestClient) -> None:
    every = [f["name"] for f in client.get("/foods", params={"q": ""}).json()]
    for name in ("Carrot poriyal", "Pidi kozhukattai", "Ghee rice", "Crab masala"):
        assert name in every


def test_labels_json_and_the_seed_agree() -> None:
    labels = Path(__file__).resolve().parents[4] / "ml" / "labels.json"
    if not labels.exists():  # the sidecar can be tested on its own
        return
    from app.modules.nutrition.seed import FOODS
    from app.modules.nutrition.seed_v12 import FOODS_V12
    from app.modules.nutrition.seed_v14 import FOODS_V14

    table = {row[0]: row[1] for row in [*FOODS, *FOODS_V12, *FOODS_V14]}
    for cls, e in json.loads(labels.read_text(encoding="utf-8"))["classes"].items():
        if e["food_name"] is not None:
            assert table.get(e["food_name"]) == e["default_portion"], cls
