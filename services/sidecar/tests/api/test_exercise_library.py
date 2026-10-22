def test_library_is_filled_from_free_exercise_db(client):
    rows = client.get("/exercises").json()
    assert len(rows) > 900
    sources = {r["source"] for r in rows}
    assert sources == {"ascend", "free-exercise-db"}
    with_images = [r for r in rows if r["image"]]
    assert len(with_images) > 800
    assert all(
        r["image"].startswith("exercises/") and r["image"].endswith(".webp") for r in with_images
    )
    slugs = [r["slug"] for r in rows]
    assert len(slugs) == len(set(slugs)) and all(slugs)


def test_duplicates_are_merged_not_listed_twice(client):
    names = [r["name"] for r in client.get("/exercises", params={"q": "pull"}).json()]
    assert "Pull-up" in names and "Pullups" not in names
    plank = [
        r for r in client.get("/exercises", params={"q": "plank"}).json() if r["name"] == "Plank"
    ]
    assert len(plank) == 1 and plank[0]["measure"] == "hold"


def test_search_finds_aliases(client):
    names = {r["name"] for r in client.get("/exercises", params={"q": "pullups"}).json()}
    assert "Pull-up" in names
    names = {r["name"] for r in client.get("/exercises", params={"q": "australian"}).json()}
    assert "Inverted Row" in names


def test_filters_by_muscle_equipment_and_difficulty(client):
    lats = client.get(
        "/exercises", params={"muscle": "latissimus_dorsi", "difficulty": "expert"}
    ).json()
    assert lats and all(r["difficulty"] == "expert" for r in lats)
    assert all(
        any(m["muscle"] == "latissimus_dorsi" and m["weight"] >= 0.5 for m in r["muscles"])
        for r in lats
    )
    kb = client.get("/exercises", params={"equipment": "kettlebell"}).json()
    assert kb and all(r["equipment"] == "kettlebell" for r in kb)
    assert client.get("/exercises", params={"muscle": "wings"}).status_code == 422
    assert client.get("/exercises", params={"difficulty": "god"}).status_code == 422
    assert client.get("/exercises", params={"custom": True}).json() == []


def test_detail_has_instructions_and_sources(client):
    pull = next(
        r
        for r in client.get("/exercises", params={"q": "Pull-up"}).json()
        if r["name"] == "Pull-up"
    )
    d = client.get(f"/exercises/{pull['id']}").json()
    assert d["instructions"] and d["source_ref"] == "Pullups"
    assert d["field_sources"]["muscles"] == "library"
    assert d["sets_logged"] == 0
    assert client.get("/exercises/999999").status_code == 404


def test_calisthenics_progressions_exist_with_holds(client):
    cal = {
        r["name"]: r for r in client.get("/exercises", params={"section": "calisthenics"}).json()
    }
    for name in ("Tuck Front Lever", "L-sit", "Planche Lean", "Wall Handstand", "Dragon Flag"):
        assert name in cal, name
    assert cal["Tuck Front Lever"]["measure"] == "hold"
    assert cal["Pistol Squat"]["measure"] == "reps"
