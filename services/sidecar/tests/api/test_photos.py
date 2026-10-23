import base64
import struct
import zipfile
import zlib
from pathlib import Path

import pytest

from app.modules.photos import strip, vision

GPS = b"GPSLatitude 12.97 GPSLongitude 77.59 SerialNumber ABC123"


def seg(marker: int, payload: bytes) -> bytes:
    return bytes([0xFF, marker]) + struct.pack(">H", len(payload) + 2) + payload


def jpeg_with_exif() -> bytes:
    return (
        b"\xff\xd8"
        + seg(0xE0, b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00")
        + seg(0xE1, b"Exif\x00\x00" + GPS)
        + seg(0xE1, b"http://ns.adobe.com/xap/1.0/\x00<x:xmpmeta/>")
        + seg(0xFE, b"taken by someone")
        + seg(0xDB, bytes(65))
        + seg(0xC0, b"\x08\x00\x01\x00\x01\x01\x01\x11\x00")
        + seg(0xDA, b"\x01\x01\x00\x00\x3f\x00")
        + b"\x12\x34\x56"
        + b"\xff\xd9"
    )


def chunk(ctype: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + ctype + data + struct.pack(">I", zlib.crc32(ctype + data))


def png_with_text() -> bytes:
    return (
        strip.PNG_SIG
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + chunk(b"tEXt", b"Comment\x00" + GPS)
        + chunk(b"eXIf", b"MM\x00*" + GPS)
        + chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00"))
        + chunk(b"IEND", b"")
    )


def data_url(raw: bytes, mime: str = "image/jpeg") -> str:
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"


def add(client, raw=None, **over):
    body = {"data_url": data_url(raw or jpeg_with_exif()), "taken_on": "2026-03-10"}
    body.update(over)
    return client.post("/photos", json=body)


def test_strip_removes_exif_xmp_and_comments_but_keeps_the_image():
    out = strip.strip_jpeg(jpeg_with_exif())
    assert GPS not in out and b"Exif" not in out and b"xmpmeta" not in out
    assert b"taken by someone" not in out
    assert out.startswith(b"\xff\xd8") and out.endswith(b"\x12\x34\x56\xff\xd9")
    assert b"JFIF" in out
    clean = strip.strip_png(png_with_text())
    assert GPS not in clean and b"IDAT" in clean and clean.endswith(chunk(b"IEND", b""))
    with pytest.raises(strip.NotAnImage):
        strip.strip(b"GIF89a....")


def test_add_list_view_and_delete(client, settings):
    r = add(client, pose="side", note="morning, window light")
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["pose"] == "side" and p["mime"] == "image/jpeg"
    files = list((Path(settings.data_dir) / "photos").iterdir())
    assert len(files) == 1 and GPS not in files[0].read_bytes()
    img = client.get(f"/photos/{p['id']}/file")
    assert img.status_code == 200 and img.headers["content-type"] == "image/jpeg"
    assert GPS not in img.content and img.headers["cache-control"] == "no-store"
    data = client.get(f"/photos/{p['id']}/data").json()
    assert data["data_url"] == "data:image/jpeg;base64," + base64.b64encode(img.content).decode()
    png = add(client, png_with_text(), taken_on="2026-04-10")
    png = png.json()
    assert png["mime"] == "image/png"
    assert [x["id"] for x in client.get("/photos").json()] == [png["id"], p["id"]]
    assert client.delete(f"/photos/{p['id']}").status_code == 204
    assert client.get(f"/photos/{p['id']}/file").status_code == 404
    assert len(list((Path(settings.data_dir) / "photos").iterdir())) == 1


@pytest.mark.parametrize(
    ("over", "message"),
    [
        ({"data_url": "data:text/plain;base64,aGVsbG8gd29ybGQ="}, "data URL"),
        ({"data_url": data_url(b"GIF89a" + bytes(20), "image/gif")}, "JPEG and PNG"),
        ({"taken_on": "2027-01-01"}, "future"),
        ({"pose": "flex"}, None),
    ],
)
def test_bad_photos_are_refused(client, over, message):
    r = add(client, **over)
    assert r.status_code == 422
    if message:
        assert message in r.json()["detail"]


def test_photos_travel_with_backups(client, settings, profile):
    p = add(client).json()
    made = client.post("/backup").json()
    with zipfile.ZipFile(made["path"]) as z:
        names = z.namelist()
    assert any(n.startswith("photos/") for n in names)
    client.delete(f"/photos/{p['id']}")
    assert client.post("/restore", json={"path": made["path"]}).status_code == 200
    assert client.get(f"/photos/{p['id']}/file").status_code == 200


def test_erase_removes_photo_files(client, settings, profile):
    add(client)
    r = client.post("/data/erase", json={"confirm": "erase", "keep_preferences": True})
    assert r.status_code == 200, r.text
    assert client.get("/photos").json() == []
    assert not (Path(settings.data_dir) / "photos").exists() or not any(
        (Path(settings.data_dir) / "photos").iterdir()
    )


def test_feedback_is_off_by_default_and_never_for_minors(client, profile):
    st = client.get("/photos/feedback/status").json()
    assert not st["enabled"] and not st["available"] and "Settings" in st["reason"]
    a, b = add(client).json(), add(client, taken_on="2026-04-10").json()
    r = client.post("/photos/feedback", json={"older_id": a["id"], "newer_id": b["id"]})
    assert r.status_code == 409
    client.put("/settings", json={"photo_feedback": True})
    st = client.get("/photos/feedback/status").json()
    assert st["enabled"] and not st["available"] and "ollama pull" in st["reason"]
    client.put("/profile", json={**profile_body(), "age": 16})
    assert client.get("/settings").json()["photo_feedback"] is False
    st = client.get("/photos/feedback/status").json()
    assert st == {**st, "enabled": False, "reason": "Off for under-18s."}


def profile_body():
    return {
        "name": "Navin",
        "age": 21,
        "sex": "male",
        "height_cm": 175,
        "weight_kg": 70,
        "goal": "bulk",
        "activity": "moderate",
    }


def test_feedback_runs_through_the_guard(client, profile, monkeypatch):
    client.put("/settings", json={"photo_feedback": True})
    monkeypatch.setattr("app.modules.coach.ollama.is_available", lambda *a, **k: True)
    seen = {}

    def fake(host, model, older, newer, timeout=120.0):
        seen["n"] = (older, newer)
        return (
            "Your shoulders look broader and your posture is straighter. "
            "You look about 3 kg lighter with less body fat. "
            "Keep training rows for your upper back."
        )

    monkeypatch.setattr(vision, "compare", fake)
    a, b = add(client).json(), add(client, taken_on="2026-04-10").json()
    r = client.post("/photos/feedback", json={"older_id": b["id"], "newer_id": a["id"]})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["guarded"] and out["is_ai"]
    assert "kg" not in out["text"] and "fat" not in out["text"]
    assert out["text"].startswith("Your shoulders look broader")


@pytest.mark.parametrize(
    "reply",
    [
        "You are about 15% body fat.",
        "You look skinny. Your weight dropped.",
        "You look really attractive now!",
    ],
)
def test_guard_falls_back_when_nothing_safe_is_left(reply):
    text, removed = vision.guard(reply)
    assert removed and text == vision.FALLBACK
