def test_filter_exercises_by_section(client):
    cardio = client.get("/exercises", params={"section": "cardio"}).json()
    assert {e["name"] for e in cardio} >= {"Running", "Cycling", "Rowing Machine"}
    assert all(e["section"] == "cardio" and e["time_based"] for e in cardio)
    assert all(e["met"] and e["met"] > 1 for e in cardio)


def test_lifts_are_not_time_based_and_have_no_met(client):
    bench = client.get("/exercises", params={"q": "Barbell Bench Press"}).json()[0]
    assert bench["section"] == "gym"
    assert bench["time_based"] is False
    assert bench["met"] is None


def test_bodyweight_moves_are_calisthenics(client):
    names = {e["name"] for e in client.get("/exercises", params={"section": "calisthenics"}).json()}
    assert "Push-Up" in names or any("Push" in n for n in names)


def test_every_section_has_entries_and_unknown_is_rejected(client):
    for section in ("gym", "calisthenics", "cardio", "martial_arts", "flexibility", "meditation"):
        assert client.get("/exercises", params={"section": section}).json(), section
    assert client.get("/exercises", params={"section": "dance"}).status_code == 422
