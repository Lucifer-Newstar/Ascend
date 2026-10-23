def test_profile_missing_before_onboarding(client):
    assert client.get("/profile").status_code == 404


def test_onboarding_computes_estimated_targets(client, profile):
    e = profile["energy"]
    assert e["bmr"] == 1694  # 10*70 + 6.25*175 - 5*21 + 5
    assert e["tdee"] == round(1693.75 * 1.55)
    assert e["kcal_target"] == round(1693.75 * 1.55 + 300)
    assert e["is_estimate"] is True


def test_underweight_lose_fat_gets_a_maintenance_target_not_a_deficit(client):
    """QA pass 4: 45 kg at 170 cm (BMI 15.6) picking "Lose fat" got 1,442 kcal, a 500 kcal
    deficit, although the planner refuses deficits below a BMI of 18.5."""
    body = {
        "age": 21,
        "sex": "male",
        "height_cm": 170,
        "weight_kg": 45,
        "goal": "cut",
        "activity": "sedentary",
    }
    e = client.put("/profile", json=body).json()["energy"]
    assert e["kcal_target"] == e["tdee"]
    adaptive = client.get("/intelligence/tdee").json()
    assert adaptive["formula_target_kcal"] == e["tdee"]


def test_profile_validation(client):
    r = client.put(
        "/profile",
        json={"age": 5, "sex": "male", "height_cm": 175, "weight_kg": 70, "goal": "bulk"},
    )
    assert r.status_code == 422


def test_ai_toggle_round_trip(client):
    defaults = {
        # v1.2: off by default when no local AI is installed (tests stub the probe to "none").
        "ai_enabled": False,
        "units": "metric",
        "theme": "shadow",  # v1.2 default for a new player
        "background_art": "on",
        "sessions_per_week": 3,
        "reduce_motion": False,
        "online_lookup": False,
        "trainer": True,
        "trainer_id": "iskra",
        "hide_calories": False,
        "photo_feedback": False,
        "avatar": "male",
        "outfit": "",
        "relic": "",
        "pet": "",
        "weapon": "",
        "themed_cosmetics": True,
        "reminders": True,
    }
    assert client.get("/settings").json() == defaults
    assert client.put("/settings", json={"ai_enabled": True}).json() == {
        **defaults,
        "ai_enabled": True,
    }
    assert client.get("/settings").json()["ai_enabled"] is True
    assert client.put("/settings", json={"ai_enabled": False}).json()["ai_enabled"] is False


def test_settings_partial_update_keeps_other_values(client):
    client.put("/settings", json={"theme": "light", "units": "imperial"})
    r = client.put("/settings", json={"sessions_per_week": 4}).json()
    assert r == {
        "ai_enabled": False,
        "units": "imperial",
        "theme": "light",
        "sessions_per_week": 4,
        "reduce_motion": False,
        "online_lookup": False,
        "trainer": True,
        "trainer_id": "iskra",
        "hide_calories": False,
        "photo_feedback": False,
        "background_art": "on",
        "avatar": "male",
        "outfit": "",
        "relic": "",
        "pet": "",
        "weapon": "",
        "themed_cosmetics": True,
        "reminders": True,
    }


def test_reduce_motion_round_trip(client):
    assert client.put("/settings", json={"reduce_motion": True}).json()["reduce_motion"] is True
    assert client.get("/settings").json()["reduce_motion"] is True
    # Other updates leave it alone; it switches back off explicitly.
    assert client.put("/settings", json={"theme": "light"}).json()["reduce_motion"] is True
    assert client.put("/settings", json={"reduce_motion": False}).json()["reduce_motion"] is False


def test_trainer_toggle_is_persisted(client):
    assert client.put("/settings", json={"trainer": False}).json()["trainer"] is False
    assert client.get("/settings").json()["trainer"] is False  # plain mode survives a restart
    assert client.put("/settings", json={"trainer": True}).json()["trainer"] is True


def test_settings_validation(client):
    assert client.put("/settings", json={"theme": "neon"}).status_code == 422
    assert client.put("/settings", json={"sessions_per_week": 9}).status_code == 422
    assert client.put("/settings", json={"reduce_motion": "sometimes"}).status_code == 422


def test_ai_defaults_on_only_when_local_ai_is_installed(client, monkeypatch):
    from app.modules.progress import service as progress_service

    monkeypatch.setattr(progress_service, "local_ai_installed", lambda: True)
    assert client.get("/settings").json()["ai_enabled"] is True
    client.put("/settings", json={"ai_enabled": False})  # the user's own choice wins
    assert client.get("/settings").json()["ai_enabled"] is False
