"""Review L16, L17, L20, L22: concurrency, pagination, shutdown and dev-mode CORS."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import event

from app.main import exit_via
from app.modules.workouts import service


def _ex(client, q: str) -> int:
    return next(e["id"] for e in client.get("/exercises", params={"q": q}).json())


def test_l16_two_quick_starts_make_one_active_session(client, profile, monkeypatch) -> None:
    real = service.active_workout
    barrier = threading.Barrier(2, timeout=5)

    def slow_active(db):
        found = real(db)
        try:
            barrier.wait()  # both requests have looked before either inserts
        except threading.BrokenBarrierError:
            pass
        time.sleep(0.05)
        return found

    monkeypatch.setattr(service, "active_workout", slow_active)
    with ThreadPoolExecutor(2) as pool:
        ids = list(pool.map(lambda _: client.post("/workouts").json()["id"], range(2)))
    monkeypatch.setattr(service, "active_workout", real)
    assert ids[0] == ids[1]
    assert len([w for w in client.get("/workouts").json() if w["finished_at"] is None]) == 1


def test_l17_pages_do_not_skip_workouts_that_share_a_start_time(client, profile) -> None:
    squat = _ex(client, "Back Squat")
    made = []
    for _ in range(3):  # the fixed test clock: all three start in the same second
        w = client.post("/workouts").json()["id"]
        client.post(f"/workouts/{w}/sets", json={"exercise_id": squat, "weight_kg": 50, "reps": 5})
        client.post(f"/workouts/{w}/finish")
        made.append(w)
    seen, before, before_id = [], None, None
    for _ in range(5):
        params = {"limit": 1}
        if before:
            params.update(before=before, before_id=before_id)
        page = client.get("/workouts", params=params).json()
        if not page:
            break
        seen.append(page[0]["id"])
        before, before_id = page[0]["started_at"], page[0]["id"]
    assert sorted(seen) == sorted(made)


def test_l17_listing_does_not_query_per_set(client, profile) -> None:
    squat = _ex(client, "Back Squat")

    def log(n_sets: int) -> None:
        w = client.post("/workouts").json()["id"]
        for _ in range(n_sets):
            client.post(
                f"/workouts/{w}/sets", json={"exercise_id": squat, "weight_kg": 50, "reps": 5}
            )
        client.post(f"/workouts/{w}/finish")

    engine = client.app.state.engine

    def count() -> int:
        n = [0]

        def on(*_a):
            n[0] += 1

        event.listen(engine, "before_cursor_execute", on)
        try:
            assert client.get("/workouts", params={"limit": 50}).status_code == 200
        finally:
            event.remove(engine, "before_cursor_execute", on)
        return n[0]

    log(2)
    small = count()
    for _ in range(4):
        log(6)
    assert count() == small  # same number of queries for 1 workout x 2 sets and 5 x ~6


def test_l20_shutdown_asks_the_server_to_exit_instead_of_killing_itself() -> None:
    class Server:
        should_exit = False

    s = Server()
    exit_via(s)()
    assert s.should_exit is True


def test_l22_dev_mode_sends_no_cors_headers(tmp_path) -> None:
    from fastapi.testclient import TestClient

    from app.core.config import Settings
    from app.main import create_app

    app = create_app(Settings(data_dir=tmp_path, token="dev", dev=True), outbox_interval=0)
    with TestClient(app) as c:
        r = c.options(
            "/profile",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
        assert "access-control-allow-origin" not in r.headers
        r = c.get(
            "/profile", headers={"Origin": "http://localhost:5173", "Authorization": "Bearer dev"}
        )
        assert "access-control-allow-origin" not in r.headers
