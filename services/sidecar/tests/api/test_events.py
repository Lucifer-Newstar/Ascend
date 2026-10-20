from __future__ import annotations

import json


def messages(text: str) -> list[dict]:
    out = []
    for block in text.strip().split("\n\n"):
        fields = dict(
            line.split(": ", 1)
            for line in block.splitlines()
            if ": " in line and not line.startswith(":")
        )
        if "event" in fields:
            out.append(
                {
                    "id": int(fields["id"]),
                    "event": fields["event"],
                    "data": json.loads(fields["data"]),
                }
            )
    return out


def log_set(client, weight: float = 40, reps: int = 8) -> None:
    ex = client.get("/exercises", params={"q": "bench", "section": "gym"}).json()[0]
    w = client.get("/workouts/active").json() or client.post("/workouts").json()
    client.post(
        f"/workouts/{w['id']}/sets",
        json={"exercise_id": ex["id"], "weight_kg": weight, "reps": reps},
    )


def test_events_backlog_maps_domain_events(client, profile):
    log_set(client)
    log_set(client, weight=60)  # beats the first set: a PR
    r = client.get("/events", params={"once": True})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    msgs = messages(r.text)
    names = [m["event"] for m in msgs]
    assert "dashboard.changed" in names
    assert names.count("pr.achieved") == 1
    first = next(m for m in msgs if m["data"]["type"] == "SetLogged")
    assert first["data"]["payload"]["weight_kg"] == 40
    assert first["data"]["version"] == 1


def test_last_event_id_resumes_after_the_given_event(client, profile):
    log_set(client)
    first = messages(client.get("/events", params={"once": True}).text)
    last = max(m["id"] for m in first)
    log_set(client, weight=42.5)
    later = messages(
        client.get("/events", params={"once": True}, headers={"Last-Event-ID": str(last)}).text
    )
    assert later and all(m["id"] > last for m in later)
    assert any(m["data"]["payload"].get("weight_kg") == 42.5 for m in later)


def test_bad_last_event_id_starts_from_the_beginning(client, profile):
    log_set(client)
    r = client.get("/events", params={"once": True}, headers={"Last-Event-ID": "not-a-number"})
    assert messages(r.text)


def test_events_requires_the_token(client):
    r = client.get("/events", params={"once": True}, headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401
