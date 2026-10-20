"""Online research for custom exercises (ADR-0013): consent, the no-network guarantee,
confidence and "not enough offline data", the research report, failures and the log."""

import socket

import httpx
import pytest

from app.modules.workouts import custom

SPOTO_DESC = "<p>Lower the bar and pause an inch above the chest.</p><p>Press up.</p>"
SPOTO_INFO = {
    "category": {"name": "Chest"},
    "muscles": [{"name_en": "Chest"}],
    "muscles_secondary": [
        {"name_en": "Triceps"},
        {"name_en": "", "name": "Anterior deltoid"},
    ],
    "equipment": [{"name": "Barbell"}, {"name": "Bench"}],
    "license": {"short_name": "CC-BY-SA 4"},
    "license_author": "someone",
}


def fake_web(calls: list[str], *, wiki: dict | None = None):
    """wger knows only "Spoto Press" (exact, case-sensitive, like the real API);
    Wikipedia answers 404 unless `wiki` is given."""

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        host, path = request.url.host, request.url.path
        if host == "wger.de" and path.endswith("/exercise-translation/"):
            if request.url.params["name"] == "Spoto Press":
                tr = {"exercise": 77, "name": "Spoto Press", "description": SPOTO_DESC}
                return httpx.Response(200, json={"results": [tr]})
            return httpx.Response(200, json={"results": []})
        if host == "wger.de" and path.endswith("/exerciseinfo/77/"):
            return httpx.Response(200, json=SPOTO_INFO)
        if host == "en.wikipedia.org":
            if wiki is None:
                return httpx.Response(404, json={"type": "not_found"})
            return httpx.Response(200, json=wiki)
        return httpx.Response(500)

    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)


def analyze(client, name, **kw):
    r = client.post("/exercises/analyze", json={"name": name, **kw})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
def no_ai(client):
    client.put("/settings", json={"ai_enabled": False})


@pytest.fixture
def web(client):
    calls: list[str] = []
    client.app.state.research_client = fake_web(calls)
    return calls


def test_zero_network_calls_when_research_is_off(client, no_ai, monkeypatch):
    """With the setting off and no allow-once, nothing may touch the network: no HTTP
    client is created by the research code and no socket connects anywhere."""
    built: list[object] = []
    connects: list[object] = []
    real_connect = socket.socket.connect

    def spy_client(*a, **k):
        built.append(k)
        raise AssertionError("an HTTP client was created while online research is off")

    def spy_connect(self, address):
        if self.family != getattr(socket, "AF_UNIX", None):
            connects.append(address)
            raise AssertionError(f"network connect to {address!r}")
        return real_connect(self, address)

    def spy_dns(*a, **k):
        connects.append(a)
        raise AssertionError("DNS lookup while online research is off")

    monkeypatch.setattr(custom.httpx, "Client", spy_client)
    monkeypatch.setattr(socket.socket, "connect", spy_connect)
    monkeypatch.setattr(socket, "getaddrinfo", spy_dns)
    assert client.get("/settings").json()["online_lookup"] is False
    for name in ("spoto press", "zzq qqz", "Barbell Bench Press", "Banded Pallof Hold"):
        for body in ({}, {"online": True}, {"online": True, "allow_once": False}):
            a = analyze(client, name, **body)
            assert a["online"]["status"] == "off"
            assert a["research"] is None
    assert built == [] and connects == []
    assert client.get("/exercises/online-log").json() == []


def test_not_enough_offline_data_is_flagged_with_per_field_confidence(client, no_ai):
    weak = analyze(client, "zzq qqz")
    assert weak["insufficient"], "a name nothing recognises must be flagged"
    assert set(weak["insufficient"]) <= {"section", "equipment", "measure", "pattern", "muscles"}
    for key in weak["insufficient"]:
        assert weak["confidence"][key] == "low"
    assert set(weak["confidence"].values()) <= {"high", "medium", "low"}

    strong = analyze(client, "Barbell Bench Press")
    assert strong["insufficient"] == []
    assert strong["confidence"]["muscles"] == "high"  # near-identical library exercise

    rules = analyze(client, "Banded Pallof Hold")
    assert rules["confidence"]["equipment"] == "medium"  # a keyword rule matched
    assert rules["online"]["status"] == "off"


def test_allow_once_researches_without_turning_the_setting_on(client, no_ai, web):
    a = analyze(client, "spoto press", online=True, allow_once=True)
    assert a["online"]["status"] == "ok"
    assert client.get("/settings").json()["online_lookup"] is False
    # Casing variants: "spoto press" was tried as typed, then as "Spoto Press".
    names = [httpx.URL(u).params.get("name") for u in web if "exercise-translation" in u]
    assert names[:2] == ["spoto press", "Spoto Press"]
    p = a["proposal"]
    muscles = {m["muscle"]: m["weight"] for m in p["muscles"]}
    assert muscles == {"lower_chest": 1.0, "upper_chest": 0.5, "triceps": 0.5, "front_delts": 0.5}
    assert p["equipment"] == "barbell" and a["field_sources"]["equipment"] == "wger"
    assert a["confidence"]["muscles"] == "high"
    r = a["research"]
    assert r["consent"] == "once" and r["outcome"] == "ok" and r["query"] == "spoto press"
    by_field = {f["field"]: f for f in r["fields"]}
    assert {"muscles", "equipment", "instructions"} <= set(by_field)
    assert by_field["equipment"]["url"] == "https://wger.de/en/exercise/77/view/"
    assert by_field["equipment"]["offline_value"] == "other"
    assert by_field["equipment"]["conflict"] is True
    # The offline guess travels with it, so the user can keep it instead.
    assert a["offline"]["equipment"] == "other" and a["offline_sources"]["equipment"] == "rules"
    assert a["attribution"][0]["license"] == "CC-BY-SA 4"
    assert "someone" in a["attribution"][0]["title"]
    statuses = [(c["source"], c["status"]) for c in r["calls"]]
    assert ("wikipedia", "not_found") in statuses
    log = client.get("/exercises/online-log").json()
    assert len(log) == 1 and log[0]["consent"] == "once" and log[0]["outcome"] == "ok"
    assert log[0]["query"] == "spoto press"
    assert {s["source"] for s in log[0]["sources"]} == {"wger", "wikipedia"}


def test_setting_on_researches_only_when_offline_data_is_insufficient(client, no_ai, web):
    client.put("/settings", json={"online_lookup": True})
    strong = analyze(client, "Barbell Bench Press")
    assert strong["online"]["status"] == "not_requested" and web == []
    weak = analyze(client, "spoto press")  # not asked, but insufficient: looked up
    assert weak["online"]["status"] == "ok" and weak["research"]["consent"] == "setting"
    web.clear()
    forced = analyze(client, "Barbell Bench Press", online=True)  # explicit ask
    assert forced["online"]["status"] == "not_found" and web
    assert len(client.get("/exercises/online-log").json()) == 2


def test_nothing_is_saved_until_the_user_confirms(client, no_ai, web):
    before = len(client.get("/exercises", params={"custom": True}).json())
    analyze(client, "spoto press", online=True, allow_once=True)
    assert len(client.get("/exercises", params={"custom": True}).json()) == before


def test_a_result_with_another_name_is_not_accepted(client, no_ai):
    """If wger ever ignores the name filter it returns every exercise; take none of them."""

    def handler(request):
        if "exercise-translation" in request.url.path:
            return httpx.Response(200, json={"results": [{"exercise": 1, "name": "Abseil"}]})
        return httpx.Response(404, json={})

    client.app.state.research_client = httpx.Client(transport=httpx.MockTransport(handler))
    a = analyze(client, "spoto press", online=True, allow_once=True)
    assert a["online"]["status"] == "not_found"
    assert "wger" not in a["field_sources"].values()


def test_wikipedia_summary_only_for_a_matching_article(client, no_ai):
    calls: list[str] = []
    page = {"desktop": {"page": "https://en.wikipedia.org/wiki/Spoto_press"}}
    extract = "The Spoto press is a bench press variation. It pauses off the chest. More."
    good = {"type": "standard", "title": "Spoto press", "content_urls": page, "extract": extract}
    client.app.state.research_client = fake_web(calls, wiki=good)
    a = analyze(client, "Spoto press", online=True, allow_once=True)
    assert a["research"]["summary"].startswith("The Spoto press is a bench press variation.")
    assert "More." not in a["research"]["summary"]
    assert any(
        x["source"] == "wikipedia" and x["license"] == "CC BY-SA 4.0" for x in a["attribution"]
    )
    generic = {"type": "standard", "title": "Exercise", "extract": "Exercise is..."}
    client.app.state.research_client = fake_web(calls, wiki=generic)
    b = analyze(client, "zzq qqz", online=True, allow_once=True)
    assert b["research"]["summary"] == "" and b["online"]["status"] == "not_found"


@pytest.mark.parametrize(
    ("error", "outcome"),
    [
        (httpx.ConnectError("no route"), "offline"),
        (httpx.ReadTimeout("slow"), "timeout"),
        ("429", "rate_limited"),
    ],
)
def test_failures_never_block_the_add_flow(client, no_ai, error, outcome):
    def handler(request):
        if error == "429":
            return httpx.Response(429, json={"detail": "slow down"})
        raise error

    client.app.state.research_client = httpx.Client(transport=httpx.MockTransport(handler))
    a = analyze(client, "spoto press", online=True, allow_once=True)
    assert a["online"]["status"] == outcome and a["online"]["detail"]
    assert a["proposal"]["section"]  # the offline proposal still stands
    assert a["research"]["fields"] == []
    log = client.get("/exercises/online-log").json()
    assert log[0]["outcome"] == outcome
    if outcome in ("offline", "timeout"):
        assert ("wikipedia", "skipped") in [
            (c["source"], c["status"]) for c in a["research"]["calls"]
        ]


def test_log_lists_newest_first_and_clears(client, no_ai, web, clock):
    from datetime import timedelta

    analyze(client, "spoto press", online=True, allow_once=True)
    clock.now += timedelta(minutes=5)
    analyze(client, "zzq qqz", online=True, allow_once=True)
    log = client.get("/exercises/online-log").json()
    assert [e["query"] for e in log] == ["zzq qqz", "spoto press"]
    assert log[1]["outcome"] == "ok" and log[0]["outcome"] == "not_found"
    assert client.delete("/exercises/online-log").status_code == 204
    assert client.get("/exercises/online-log").json() == []


def test_researched_exercise_keeps_sources_and_feeds_the_event(client, no_ai, web):
    a = analyze(client, "spoto press", online=True, allow_once=True)
    p = a["proposal"]
    keys = ("section", "equipment", "measure", "pattern", "difficulty", "muscles", "rep_low",
            "rep_high", "instructions", "aliases")  # fmt: skip
    body = {k: p[k] for k in keys}
    body.update(name=a["name"], field_sources=a["field_sources"], attribution=a["attribution"])
    r = client.post("/exercises", json=body)
    assert r.status_code == 201, r.text
    e = r.json()
    assert e["field_sources"]["muscles"] == "wger"
    assert e["attribution"][0]["url"] == "https://wger.de/en/exercise/77/view/"
