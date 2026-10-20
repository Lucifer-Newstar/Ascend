def test_profile_missing_before_onboarding(client):
    assert client.get("/profile").status_code == 404


def test_onboarding_computes_estimated_targets(client, profile):
    e = profile["energy"]
    assert e["bmr"] == 1694  # 10*70 + 6.25*175 - 5*21 + 5
    assert e["tdee"] == round(1693.75 * 1.55)
    assert e["kcal_target"] == round(1693.75 * 1.55 + 300)
    assert e["is_estimate"] is True


def test_profile_validation(client):
    r = client.put("/profile", json={"age": 5, "sex": "male", "height_cm": 175, "weight_kg": 70,
                                     "goal": "bulk"})
    assert r.status_code == 422


def test_ai_toggle_round_trip(client):
    assert client.get("/settings").json() == {"ai_enabled": True}
    assert client.put("/settings", json={"ai_enabled": False}).json() == {"ai_enabled": False}
    assert client.get("/settings").json() == {"ai_enabled": False}
