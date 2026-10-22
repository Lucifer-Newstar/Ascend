"""GET /intelligence/tdee and /intelligence/insights (ADR-0018, ADR-0019): the adaptive
estimate and weekly findings over real logged meals and weigh-ins, the day target switching
to the adaptive one, and explanations behind the coach guard."""

from datetime import timedelta

import pytest

from app.modules.coach import ollama
from app.modules.intelligence import explain


@pytest.fixture(autouse=True)
def fresh_cache():
    explain.clear_cache()
    yield
    explain.clear_cache()


def food_ids(client) -> dict[str, dict]:
    return {f["name"]: f for f in client.get("/foods").json()}


def log_days(
    client,
    clock,
    n: int,
    *,
    kcal_per_day: float = 2600.0,
    start_kg: float = 70.0,
    rate_kg_day: float = 0.0,
):
    """n days ending today: a morning weigh-in and one meal of about `kcal_per_day` kcal of
    the densest food in the table (rounded to half portions)."""
    food = max(food_ids(client).values(), key=lambda f: f["kcal"])
    portions = round(kcal_per_day / food["kcal"] * 2) / 2
    today = clock.now
    for i in range(n):
        clock.now = today - timedelta(days=n - 1 - i)
        r = client.post("/body-metrics", json={"weight_kg": round(start_kg + rate_kg_day * i, 2)})
        assert r.status_code == 201
        if i < n - 1:  # today's meals are still to come
            assert (
                client.post(
                    "/meals",
                    json={
                        "meal_type": "lunch",
                        "items": [{"food_id": food["id"], "portions": portions}],
                    },
                ).status_code
                == 201
            )
    clock.now = today
    return food, portions


def test_needs_a_profile(client):
    assert client.get("/intelligence/tdee").status_code == 404
    assert client.get("/intelligence/insights").status_code == 404


def test_cold_start_shows_the_formula_range(client, profile):
    r = client.get("/intelligence/tdee").json()
    assert r["status"] == "cold_start" and r["algo_version"] == "tdee-v1"
    assert r["tdee_kcal"] == r["formula_tdee_kcal"]
    assert r["low_kcal"] == r["tdee_kcal"] - 450 and r["high_kcal"] == r["tdee_kcal"] + 450
    assert r["target_source"] == "formula" and r["target_kcal"] == r["formula_target_kcal"]
    assert r["why"]["inputs"]["status"] == "cold_start"
    day = client.get("/meals/day").json()
    assert (
        day["kcal_target"] == profile["energy"]["kcal_target"] // 10 * 10
        or day["kcal_target"] == r["formula_target_kcal"]
    )
    assert day["kcal_target_source"] == "formula"


def test_five_weeks_of_logs_make_the_estimate_adaptive(client, profile, clock):
    food, portions = log_days(client, clock, 36, start_kg=70.0, rate_kg_day=0.0)
    r = client.get("/intelligence/tdee?days=30").json()
    assert len(r["series"]) == 30
    assert r["weigh_ins"] == 36 and r["intake_days_7"] == 7
    assert r["status"] == "adaptive"
    eaten = food["kcal"] * portions
    # Weight flat on a steady intake: expenditure should land near that intake.
    assert abs(r["tdee_kcal"] - eaten) < 250
    assert r["sd_kcal"] <= 200
    assert r["target_source"] == "adaptive"
    assert all(w["week_start"] for w in r["weeks"])
    day = client.get("/meals/day").json()
    assert day["kcal_target"] == r["target_kcal"] and day["kcal_target_source"] == "adaptive"
    dash = client.get("/dashboard").json()
    assert dash["rings"]["kcal_in"]["target"] == r["target_kcal"]


def test_insights_report_checks_every_rule(client, profile, clock):
    log_days(client, clock, 15, kcal_per_day=1500)
    r = client.get("/intelligence/insights").json()
    assert r["algo_version"] == "insights-v1"
    assert len(r["findings"]) <= 3
    assert {c["code"] for c in r["checks"]} == {
        "intake_vs_target",
        "protein_short",
        "weekend_gap",
        "trend_vs_goal",
        "tdee_vs_formula",
        "logging_gap",
    }
    for f in r["findings"]:
        assert f["why"]["formula"] and f["why"]["inputs"]


def test_a_bulk_eating_far_below_target_gets_an_intake_finding(client, profile, clock):
    log_days(client, clock, 10, kcal_per_day=1500)
    r = client.get("/intelligence/insights").json()
    f = next(f for f in r["findings"] if f["code"] == "intake_vs_target")
    assert f["numbers"]["difference_kcal"] < 0
    e = client.get("/intelligence/insights/intake_vs_target/explanation").json()
    assert e["phrasing"] == "template" and e["text"] == f["text"]
    assert client.get("/intelligence/insights/nope/explanation").status_code == 404


def test_tdee_explanation_guard(client, profile, clock, monkeypatch):
    log_days(client, clock, 10)
    tdee = client.get("/intelligence/tdee").json()
    monkeypatch.setattr(ollama, "is_available", lambda host, model, timeout=1.5: True)
    monkeypatch.setattr(ollama, "chat", lambda *a, **k: "You burn about 9999 kcal a day.")
    e = client.get("/intelligence/tdee/explanation").json()
    assert e["phrasing"] == "template" and e["fallback"] == "check_failed: numbers"
    assert str(round(tdee["tdee_kcal"])) in e["template"]
