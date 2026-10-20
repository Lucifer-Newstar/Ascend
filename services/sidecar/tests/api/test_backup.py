import json
import zipfile
from pathlib import Path

import pytest

PROFILE = {
    "name": "Before",
    "age": 21,
    "sex": "male",
    "height_cm": 175,
    "weight_kg": 70,
    "goal": "bulk",
    "activity": "moderate",
}


def rewrite_manifest(path: Path, **changes) -> Path:
    """Copy a backup with some manifest fields changed (for the refusal tests)."""
    out = path.with_name("edited.ascendbak")
    with zipfile.ZipFile(path) as src, zipfile.ZipFile(out, "w") as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "manifest.json":
                manifest = json.loads(data)
                manifest.update(changes)
                data = json.dumps(manifest).encode()
            dst.writestr(item, data)
    return out


def test_backup_then_restore_brings_back_the_old_data(client, settings, profile):
    client.put("/profile", json=PROFILE)
    made = client.post("/backup")
    assert made.status_code == 201
    info = made.json()
    assert Path(info["path"]).parent == settings.data_dir / "backups"
    assert info["schema_revision"] == "0009" and len(info["sha256"]) == 64

    client.put("/profile", json={**PROFILE, "name": "After"})
    restored = client.post("/restore", json={"path": info["path"]})
    assert restored.status_code == 200
    assert client.get("/profile").json()["name"] == "Before"
    # The data that was replaced is kept as its own backup.
    reasons = [b["reason"] for b in client.get("/backups").json()]
    assert sorted(reasons) == ["manual", "pre-restore"]


def test_a_tampered_database_fails_the_checksum(client, profile):
    path = Path(client.post("/backup").json()["path"])
    bad = path.with_name("tampered.ascendbak")
    with zipfile.ZipFile(path) as src, zipfile.ZipFile(bad, "w") as dst:
        dst.writestr("manifest.json", src.read("manifest.json"))
        dst.writestr("ascend.db", src.read("ascend.db") + b"junk")
    r = client.post("/restore", json={"path": str(bad)})
    assert r.status_code == 422
    assert "checksum" in r.json()["detail"]
    assert client.get("/profile").json()["name"] == "Navin"  # untouched


def test_a_backup_from_a_newer_schema_is_refused(client, profile):
    path = Path(client.post("/backup").json()["path"])
    newer = rewrite_manifest(path, schema="0999")
    r = client.post("/restore", json={"path": str(newer)})
    assert r.status_code == 422
    assert "update ASCEND first" in r.json()["detail"]


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({"path": "/nowhere/missing.ascendbak"}, "does not exist"),
        ({"path": "/tmp/notes.txt"}, "choose a .ascendbak file"),
        ({"path": "x.ascendbak", "password": "secret"}, "not supported yet"),
    ],
)
def test_restore_refuses_bad_requests_before_touching_data(client, profile, body, message):
    r = client.post("/restore", json=body)
    assert r.status_code == 422
    assert message in r.json()["detail"]
    assert client.get("/backups").json() == []  # no safety backup was taken


def test_not_a_backup_at_all(client, settings, profile):
    junk = settings.data_dir / "junk.ascendbak"
    junk.write_bytes(b"this is not a zip")
    r = client.post("/restore", json={"path": str(junk)})
    assert r.status_code == 422 and "damaged" in r.json()["detail"]


def test_backups_are_listed_newest_first_and_skip_damaged_files(client, settings, clock, profile):
    from datetime import timedelta

    first = client.post("/backup").json()
    clock.now += timedelta(minutes=5)
    second = client.post("/backup").json()
    (settings.data_dir / "backups" / "broken.ascendbak").write_bytes(b"nope")
    listed = [b["path"] for b in client.get("/backups").json()]
    assert listed == [second["path"], first["path"]]


def test_password_backups_are_not_supported_yet(client, profile):
    r = client.post("/backup", json={"password": "hunter2"})
    assert r.status_code == 422
