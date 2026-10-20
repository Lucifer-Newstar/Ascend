from fastapi.testclient import TestClient

from app.main import create_app


def test_health_is_open_and_reports_wal(settings):
    with TestClient(create_app(settings)) as c:
        r = c.get("/health")
    assert r.status_code == 200
    assert r.json()["journal_mode"] == "wal"


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
