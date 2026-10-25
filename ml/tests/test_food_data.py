"""Roboflow COCO -> crops converter and the Open Images not-food picker (no network)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from coco_to_cls import convert, list_classes, load_map, norm, photo_stem
from fetch_not_food import is_food, pick
from PIL import Image


def make_export(root: Path) -> Path:
    export = root / "South Indian Food"
    split = export / "train"
    split.mkdir(parents=True)
    names = ["idli_1_jpg.rf.abc123.jpg", "idli_1_jpg.rf.def456.jpg", "plate_9.jpg"]
    for n in names:
        Image.new("RGB", (400, 300), (200, 180, 150)).save(split / n)
    coco = {
        "categories": [
            {"id": 0, "name": "foods"},
            {"id": 1, "name": "Idly"},
            {"id": 2, "name": "Medu-Vada"},
            {"id": 3, "name": "Salad"},
            {"id": 4, "name": "Kulfi"},
        ],
        "images": [{"id": i, "file_name": n} for i, n in enumerate(names)]
        + [{"id": 9, "file_name": "gone.jpg"}],
        "annotations": [
            {"id": 10, "image_id": 0, "category_id": 1, "bbox": [10, 10, 120, 100]},
            {"id": 11, "image_id": 0, "category_id": 2, "bbox": [200, 50, 90, 90]},
            {"id": 12, "image_id": 1, "category_id": 1, "bbox": [12, 8, 118, 104]},
            {"id": 13, "image_id": 2, "category_id": 3, "bbox": [0, 0, 300, 200]},
            {"id": 14, "image_id": 2, "category_id": 4, "bbox": [0, 0, 100, 100]},
            {"id": 15, "image_id": 2, "category_id": 1, "bbox": [0, 0, 20, 20]},
            {"id": 16, "image_id": 9, "category_id": 1, "bbox": [0, 0, 100, 100]},
        ],
    }
    (split / "_annotations.coco.json").write_text(json.dumps(coco))
    return export


def test_names_normalise_and_augmented_copies_share_a_photo_stem() -> None:
    assert norm(" Medu-Vada ") == norm("medu vada") == "medu_vada"
    assert (
        photo_stem("idli_1_jpg.rf.abc123.jpg") == photo_stem("idli_1_jpg.rf.def456.jpg") == "idli_1"
    )
    assert photo_stem("plate 9.png") == "plate-9"


def test_repo_class_map_points_only_at_known_labels() -> None:
    aliases = load_map()
    assert aliases["idly"] == "idli" and aliases["salad"] == "skip"


def test_converter_crops_mapped_boxes_and_reports_the_rest(tmp_path: Path) -> None:
    export = make_export(tmp_path)
    out = tmp_path / "raw"
    rep = convert([export], out, load_map(), min_side=64).as_dict()
    assert rep["written"] == {"idli": 2, "medu_vada": 1}
    assert rep["skipped_classes"] == {"Salad": 1}
    assert rep["unmapped_classes"] == {"Kulfi": 1}
    assert rep["too_small"] == 1 and rep["missing_images"] == 1
    files = sorted(p.name for p in (out / "idli").iterdir())
    assert files == ["south_indian_food__idli_1__10.jpg", "south_indian_food__idli_1__12.jpg"]
    w, h = Image.open(out / "idli" / files[0]).size
    # 120x100 box plus 10% padding per side, clipped at the photo's left and top edges
    assert (w, h) == (142, 120)


def test_list_classes_counts_boxes(tmp_path: Path) -> None:
    counts = list_classes([make_export(tmp_path)])
    assert counts["Idly"] == 4 and counts["Kulfi"] == 1


def test_bad_class_map_is_refused(tmp_path: Path) -> None:
    bad = tmp_path / "map.yaml"
    bad.write_text("aliases:\n  idly: idlee\n")
    with pytest.raises(SystemExit, match="idlee"):
        load_map(bad)


def test_not_food_picker_skips_any_photo_with_food() -> None:
    names = {
        "/m/p": "Person",
        "/m/d": "Dog",
        "/m/f": "Fast food",
        "/m/b": "Banana",
        "/m/t": "Tableware",
    }
    rows = [
        {"ImageID": "a", "LabelName": "/m/p", "Confidence": "1"},
        {"ImageID": "b", "LabelName": "/m/d", "Confidence": "1"},
        {"ImageID": "c", "LabelName": "/m/p", "Confidence": "1"},
        {"ImageID": "c", "LabelName": "/m/f", "Confidence": "1"},
        {"ImageID": "d", "LabelName": "/m/t", "Confidence": "1"},
        {"ImageID": "d", "LabelName": "/m/b", "Confidence": "1"},
        {"ImageID": "e", "LabelName": "/m/t", "Confidence": "1"},
        {"ImageID": "f", "LabelName": "/m/d", "Confidence": "0"},
    ]
    chosen = pick(rows, names, limit=10)
    assert sorted(i for i, _ in chosen) == ["a", "b", "e"]
    assert len(pick(rows, names, limit=2)) == 2
    assert is_food("Baked goods") and not is_food("Person")
