"""Regression tests for the LOW findings of the security/code review (L1-L7, L19)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.modules.workouts import custom
from app.modules.workouts.schemas import MAX_PRIMARY_MUSCLES
from tests.api.test_custom_exercises import analyze, body_from

MUSCLES = [{"muscle": "external_obliques", "weight": 1.0}]


def _ex(client, q: str) -> int:
    return next(e["id"] for e in client.get("/exercises", params={"q": q}).json())


def _custom(client, name: str):
    client.put("/settings", json={"ai_enabled": False})
    return client.post("/exercises", json=body_from(analyze(client, name), muscles=MUSCLES))


def test_l1_reusing_an_archived_exercise_name_is_not_a_500(client, profile) -> None:
    first = _custom(client, "Banded hip airplane")
    assert first.status_code == 201, first.text
    assert client.delete(f"/exercises/{first.json()['id']}").status_code == 204
    again = _custom(client, "Banded hip airplane")
    assert again.status_code == 201, again.text
    assert again.json()["id"] != first.json()["id"]


def test_l2_finish_never_ends_before_the_start(client, clock, profile) -> None:
    squat = _ex(client, "Back Squat")
    w = client.post("/workouts").json()["id"]
    client.post(f"/workouts/{w}/sets", json={"exercise_id": squat, "weight_kg": 60, "reps": 5})
    clock.now -= timedelta(hours=1)  # the clock moves back (DST, NTP, manual change)
    r = client.post(f"/workouts/{w}/finish")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["active_minutes"] >= 0
    wk = body["workout"]
    assert wk["finished_at"] >= wk["started_at"]
    assert wk["finished_at"] >= max(s["performed_at"] for s in wk["sets"])


def test_l3_timezone_aware_weigh_ins_are_stored_as_local_time(client, profile) -> None:
    assert client.post("/body-metrics", json={"weight_kg": 70}).status_code == 201
    r = client.post(
        "/body-metrics", json={"weight_kg": 70.4, "measured_at": "2026-10-19T03:00:00Z"}
    )
    assert r.status_code == 201, r.text
    local = datetime(2026, 10, 19, 3, 0, tzinfo=UTC).astimezone().replace(tzinfo=None)
    assert r.json()["measured_at"] == local.isoformat()
    r = client.post(
        "/measurements", json={"site": "waist", "cm": 80, "measured_at": "2026-10-19T03:00:00Z"}
    )
    assert r.status_code == 201, r.text


@pytest.mark.parametrize(
    "path", ["/workouts/9223372036854775808", "/workouts/99999999999999999999/sets"]
)
def test_l4_huge_ids_are_a_client_error(client, profile, path) -> None:
    r = client.get(path) if not path.endswith("/sets") else client.post(path, json={})
    assert r.status_code in (404, 422), r.text


def test_l4_huge_id_on_a_real_route(client, profile) -> None:
    r = client.delete("/meals/9223372036854775808")
    assert r.status_code in (404, 422), r.text


def test_l5_wikipedia_titles_are_url_encoded() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(404, request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    for name in ("90/90 stretch", "Why? #1", "../../w/index.php"):
        custom.wikipedia_summary(name, client, [])
    assert seen[0].startswith(f"{custom.WIKIPEDIA_API}/90%2F90_stretch")
    assert f"{custom.WIKIPEDIA_API}/Why%3F_%231" in seen[1]
    assert seen[2].startswith(f"{custom.WIKIPEDIA_API}/..%2F..%2Fw%2Findex.php")
    assert all(u.startswith(custom.WIKIPEDIA_API + "/") for u in seen)


def test_l6_no_sets_against_an_archived_exercise(client, profile) -> None:
    made = _custom(client, "Archived curl variant")
    ex = made.json()["id"]
    client.delete(f"/exercises/{ex}")
    w = client.post("/workouts").json()["id"]
    r = client.post(f"/workouts/{w}/sets", json={"exercise_id": ex, "weight_kg": 10, "reps": 5})
    assert r.status_code in (409, 422), r.text
    assert "archived" in r.json()["detail"]


def test_l7_an_edit_cannot_null_a_required_field(client, profile) -> None:
    run = _ex(client, "Running")
    w = client.post("/workouts").json()["id"]
    s = client.post(f"/workouts/{w}/sets", json={"exercise_id": run, "duration_s": 600}).json()
    sid = s["set"]["id"] if "set" in s else s["id"]
    r = client.patch(f"/workouts/{w}/sets/{sid}", json={"duration_s": None})
    assert r.status_code == 422, r.text
    detail = client.get(f"/workouts/{w}").json()
    assert detail["sets"][0]["duration_s"] == 600


def test_l19_one_limit_for_primary_muscles() -> None:
    p = custom.Proposal(values={"section": "gym", "measure": "reps"}, sources={})
    p.values["muscles"] = {m: 1.0 for m in ("a", "b", "c", "d", "e", "f")}
    custom._make_consistent(p)
    primaries = [k for k, w in p.values["muscles"].items() if w >= 1.0]
    assert len(primaries) == MAX_PRIMARY_MUSCLES == 4
