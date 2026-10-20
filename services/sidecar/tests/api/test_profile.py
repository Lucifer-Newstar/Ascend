def test_profile_missing_before_onboarding(client):
    assert client.get("/profile").status_code == 404


def test_onboarding_computes_estimated_targets(client, profile):
    e = profile["energy"]
    assert e["bmr"] == 1694  # 10*70 + 6.25*175 - 5*21 + 5
    assert e["tdee"] == round(1693.75 * 1.55)
    assert e["kcal_target"] == round(1693.75 * 1.55 + 300)
    assert e["is_estimate"] is True


def test_profile_validation(client):
    r = client.put(
        "/profile",
        json={"age": 5, "sex": "male", "height_cm": 175, "weight_kg": 70, "goal": "bulk"},
    )
    assert r.status_code == 422


def test_ai_toggle_round_trip(client):
    defaults = {
        "ai_enabled": True,
        "units": "metric",
        "theme": "dark",
        "sessions_per_week": 3,
        "reduce_motion": False,
        "online_lookup": False,
    }
    assert client.get("/settings").json() == defaults
    assert client.put("/settings", json={"ai_enabled": False}).json() == {
        **defaults,
        "ai_enabled": False,
    }
    assert client.get("/settings").json()["ai_enabled"] is False


def test_settings_partial_update_keeps_other_values(client):
    client.put("/settings", json={"theme": "light", "units": "imperial"})
    r = client.put("/settings", json={"sessions_per_week": 4}).json()
    assert r == {
        "ai_enabled": True,
        "units": "imperial",
        "theme": "light",
        "sessions_per_week": 4,
        "reduce_motion": False,
        "online_lookup": False,
    }


def test_reduce_motion_round_trip(client):
    assert client.put("/settings", json={"reduce_motion": True}).json()["reduce_motion"] is True
    assert client.get("/settings").json()["reduce_motion"] is True
    # Other updates leave it alone; it switches back off explicitly.
    assert client.put("/settings", json={"theme": "light"}).json()["reduce_motion"] is True
    assert client.put("/settings", json={"reduce_motion": False}).json()["reduce_motion"] is False


def test_settings_validation(client):
    assert client.put("/settings", json={"theme": "neon"}).status_code == 422
    assert client.put("/settings", json={"sessions_per_week": 9}).status_code == 422
    assert client.put("/settings", json={"reduce_motion": "sometimes"}).status_code == 422
