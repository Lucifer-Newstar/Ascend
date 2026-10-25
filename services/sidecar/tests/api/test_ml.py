"""On-device ML endpoints and the trainer's learned router (ml/ in the repo)."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.modules.ml import food_photo

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "tiny_food.onnx"
CLASSES = ["idli", "plain_dosa", "sambar", "not_food"]


def chat(client: TestClient, text: str) -> dict:
    r = client.post("/trainer/chat", json={"text": text})
    assert r.status_code == 200, r.text
    return r.json()


def photo(color: tuple[int, int, int], size: tuple[int, int] = (320, 240)) -> str:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def install_model(folder: Path, gate: bool = True, sha: str | None = None) -> None:
    """A 232-byte stand-in model: average colour -> logits (red -> idli). It tests the
    plumbing only; it is not a food model."""
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURE, folder / "food_clf.onnx")
    manifest = {
        "version": "test-0",
        "file": "food_clf.onnx",
        "sha256": sha or hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
        "classes": CLASSES,
        "food_names": {"idli": "Idli", "plain_dosa": "Plain dosa", "sambar": "Sambar"},
        "gate": {"passed": gate},
    }
    (folder / food_photo.MANIFEST).write_text(json.dumps(manifest))


@pytest.fixture
def model_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "food-model"
    monkeypatch.setenv("ASCEND_FOOD_MODEL_DIR", str(folder))
    food_photo._sessions.clear()
    return folder


def test_status_lists_bundled_models_and_hides_food_scan_without_a_model(
    client: TestClient, model_dir: Path
) -> None:
    s = client.get("/ml/status").json()
    assert s["intent"]["available"] and s["intent"]["threshold"] == 0.55
    assert "log_set" in s["intent"]["labels"] and "out_of_scope" in s["intent"]["labels"]
    assert s["knowledge"]["available"] and s["knowledge"]["passages"] > 1000
    assert {"free_exercise_db", "pag_2018", "usda_fdc_sr", "who_pa_2020"} <= set(
        s["knowledge"]["sources"]
    )
    assert s["food_photo"] == {
        "available": False,
        "reason": "missing",
        "version": None,
        "classes": 0,
    }


def test_intent_endpoint_scores_a_message(client: TestClient) -> None:
    r = client.post("/ml/intent", json={"text": "did 3 sets of 10 pushups"}).json()
    assert r["intent"] == "log_set" and r["trusted"] and r["confidence"] >= r["threshold"]
    assert len(r["top"]) == 3 and r["top"][0]["intent"] == "log_set"


def test_intent_endpoint_without_the_model_says_so(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ASCEND_INTENT_MODEL", "off")
    r = client.post("/ml/intent", json={"text": "did 3 sets of 10 pushups"}).json()
    assert r["intent"] is None and not r["trusted"] and r["top"] == []


def test_knowledge_search_returns_cited_passages(client: TestClient) -> None:
    r = client.get("/ml/knowledge", params={"q": "is creatine safe", "k": 3}).json()
    top = r["hits"][0]
    assert top["id"] == "note:nutrition_basics:creatine" and top["confident"]
    assert top["citation"]["licence"] and top["citation"]["url"].startswith("https://")
    assert len(r["hits"]) <= 3


def test_knowledge_search_is_bounded(client: TestClient) -> None:
    assert client.get("/ml/knowledge", params={"q": "x" * 501}).status_code == 422
    assert client.get("/ml/knowledge", params={"q": "squat", "k": 11}).status_code == 422


def test_food_photo_is_refused_without_a_model(client: TestClient, model_dir: Path) -> None:
    r = client.post("/ml/food-photo", json={"data_url": photo((200, 30, 30))})
    assert r.status_code == 409 and "missing" in r.json()["detail"]


def test_food_photo_needs_a_gated_model_with_a_matching_checksum(
    client: TestClient, model_dir: Path
) -> None:
    install_model(model_dir, gate=False)
    assert client.get("/ml/status").json()["food_photo"]["reason"] == "not_gated"
    install_model(model_dir, sha="0" * 64)
    assert client.get("/ml/status").json()["food_photo"]["reason"] == "checksum"


def test_food_photo_suggests_three_foods_and_logs_nothing(
    client: TestClient, profile: dict, model_dir: Path
) -> None:
    install_model(model_dir)
    s = client.get("/ml/status").json()["food_photo"]
    assert s == {"available": True, "reason": None, "version": "test-0", "classes": 4}
    before = client.get("/meals/day").json()
    r = client.post("/ml/food-photo", json={"data_url": photo((230, 20, 20))})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["must_confirm"] is True and out["result"] == "food"
    assert out["suggestions"][0]["label"] == "idli" and out["suggestions"][0]["name"] == "Idli"
    assert out["suggestions"][0]["food_id"] is not None
    assert all(s["label"] != "not_food" for s in out["suggestions"])
    assert client.get("/meals/day").json() == before


def test_food_photo_rejects_files_that_are_not_photos(client: TestClient, model_dir: Path) -> None:
    install_model(model_dir)
    bad = "data:image/jpeg;base64," + base64.b64encode(b"not an image at all").decode()
    assert client.post("/ml/food-photo", json={"data_url": bad}).status_code == 422
    tiny = client.post("/ml/food-photo", json={"data_url": photo((1, 2, 3), (20, 20))})
    assert tiny.status_code == 422 and "too small" in tiny.json()["detail"]


def test_preprocess_matches_the_training_contract() -> None:
    buf = io.BytesIO()
    Image.new("RGB", (640, 480), (255, 0, 0)).save(buf, format="PNG")
    x = food_photo.preprocess(buf.getvalue())
    assert x.shape == (1, 3, 224, 224) and str(x.dtype) == "float32"
    assert abs(float(x[0, 0].mean()) - (1 - 0.485) / 0.229) < 1e-4
    assert abs(float(x[0, 1].mean()) - (0 - 0.456) / 0.224) < 1e-4


def test_trainer_answers_a_knowledge_question_with_its_source(
    client: TestClient, profile: dict
) -> None:
    # v1.3's help notes now answer "is creatine safe" outright (a sure rule keeps it), so this
    # asks in words the notes only half match.
    r = chat(client, "is creatine worth taking for strength")
    assert r["source"] == "knowledge" and r["intent"] == "nutrition_question"
    assert r["citations"][0]["passage_id"] == "note:nutrition_basics:creatine"
    assert "Creatine" in r["reply"]


def test_pain_questions_say_to_see_a_professional_first(client: TestClient, profile: dict) -> None:
    r = chat(client, "sharp pain in my shoulder during bench press")
    assert r["intent"] == "injury_pain" and r["source"] == "knowledge"
    assert r["reply"].startswith("If it hurts, stop") and "physiotherapist" in r["reply"]
    assert r["citations"]


def test_sure_rules_keep_their_messages(client: TestClient, profile: dict) -> None:
    assert chat(client, "bench 60x5")["intent"] == "action"
    assert chat(client, "hello")["intent"] == "greeting"
    assert chat(client, "hello")["citations"] == []


def test_out_of_scope_never_gets_a_knowledge_passage(client: TestClient, profile: dict) -> None:
    r = chat(client, "what is the meaning of life")
    assert r["source"] != "knowledge" and r["citations"] == []


def test_without_the_intent_model_the_rules_answer(
    client: TestClient, profile: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ASCEND_INTENT_MODEL", "off")
    r = chat(client, "sharp pain in my shoulder during bench press")
    assert r["intent"] != "injury_pain"
