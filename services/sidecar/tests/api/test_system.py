from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import TOKEN


def test_health_is_open_and_reports_wal(settings):
    with TestClient(create_app(settings)) as c:
        r = c.get("/health")
    assert r.status_code == 200
    assert r.json()["journal_mode"] == "wal"


def test_health_reports_db_and_migration_head(settings):
    with TestClient(create_app(settings)) as c:
        body = c.get("/health").json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"
    assert body["migration"] == body["migration_head"]
    assert body["migration_head"] != "none"


def test_health_is_degraded_when_migrations_are_missing(settings):
    # migrate=False leaves an empty database: the API is up but not usable yet.
    with TestClient(create_app(settings, migrate=False)) as c:
        body = c.get("/health").json()
    assert body["status"] == "degraded"
    assert body["db"] == "migration_pending"
    assert body["migration"] == "none"


def test_requests_without_token_are_rejected(settings):
    with TestClient(create_app(settings)) as c:
        assert c.get("/exercises").status_code == 401
        assert c.get("/exercises", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_foreign_host_header_is_rejected(client):
    assert client.get("/health", headers={"Host": "evil.example"}).status_code == 403


def test_openapi_docs_are_served(settings):
    with TestClient(create_app(settings)) as c:
        assert c.get("/docs").status_code == 200
        assert "/workouts" in str(c.get("/openapi.json").json()["paths"])


def test_migrations_seed_reference_data(client):
    assert len(client.get("/exercises").json()) >= 40
    assert len(client.get("/foods").json()) >= 30


def test_shutdown_checkpoints_wal_and_requests_exit(client):
    calls: list[str] = []
    client.app.state.request_exit = lambda: calls.append("exit")
    # Write something so the WAL has frames to fold back in.
    client.put("/settings", json={"ai_enabled": False})
    r = client.post("/shutdown")
    assert r.status_code == 200
    assert r.json() == {"status": "stopping", "wal_checkpoint": "ok"}
    assert calls == ["exit"]


def test_token_is_compared_exactly(settings):
    with TestClient(create_app(settings)) as c:
        # Prefix, suffix, wrong scheme and empty bearer all fail.
        for header in (
            f"Bearer {TOKEN}x",
            f"Bearer {TOKEN[:-1]}",
            f"Basic {TOKEN}",
            "Bearer ",
            TOKEN,
        ):
            assert c.get("/exercises", headers={"Authorization": header}).status_code == 401


def test_loopback_hosts_are_accepted(client):
    for host in ("127.0.0.1:8765", "localhost:8765", "127.0.0.1"):
        assert client.get("/health", headers={"Host": host}).status_code == 200


def test_dns_rebinding_host_with_valid_token_is_rejected(client):
    # A malicious page that rebinds its domain to 127.0.0.1 still sends its own Host.
    r = client.get("/exercises", headers={"Host": "attacker.test:8765"})
    assert r.status_code == 403
