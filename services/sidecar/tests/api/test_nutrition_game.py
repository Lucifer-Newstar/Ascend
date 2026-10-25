from datetime import timedelta


def food_id(client, name):
    return next(
        f["id"] for f in client.get("/foods", params={"q": name}).json() if f["name"] == name
    )


def test_food_search_is_case_insensitive(client):
    names = [f["name"] for f in client.get("/foods", params={"q": "DOSA"}).json()]
    assert "Plain dosa" in names and "Masala dosa" in names


def test_log_meal_updates_totals_and_ring(client, profile):
    idli, sambar = food_id(client, "Idli"), food_id(client, "Sambar")
    r = client.post(
        "/meals",
        json={
            "meal_type": "breakfast",
            "items": [{"food_id": idli, "portions": 3}, {"food_id": sambar, "portions": 1}],
        },
    )
    assert r.status_code == 201
    assert r.json()["meal"]["kcal"] == 3 * 58 + 110
    assert r.json()["xp_awarded"] == 5
    day = client.get("/meals/day").json()
    assert day["totals"]["kcal"] == 284
    assert day["values_are_approximate"] is True
    dash = client.get("/dashboard").json()
    assert dash["rings"]["kcal_in"]["value"] == 284
    assert dash["rings"]["kcal_in"]["target"] == profile["energy"]["kcal_target"]


def test_meal_xp_caps_at_four_meals(client, profile):
    banana = food_id(client, "Banana")
    xps = [
        client.post(
            "/meals", json={"meal_type": "snack", "items": [{"food_id": banana, "portions": 1}]}
        ).json()["xp_awarded"]
        for _ in range(5)
    ]
    assert xps[:4] == [5, 5, 5, 5] and xps[4] == 0


def test_delete_meal(client, profile):
    banana = food_id(client, "Banana")
    meal = client.post(
        "/meals", json={"meal_type": "snack", "items": [{"food_id": banana, "portions": 1}]}
    ).json()["meal"]
    assert client.delete(f"/meals/{meal['id']}").status_code == 204
    assert client.get("/meals/day").json()["totals"]["kcal"] == 0


def test_dashboard_has_three_rings_quest_and_muscles(client, profile):
    d = client.get("/dashboard").json()
    assert set(d["rings"]) == {"tasks", "kcal_in", "kcal_out"}
    assert len(d["game"]["quest"]) == 3
    assert d["game"]["xp"]["rank"] == "E"
    assert len(d["muscles"]) == 54  # taxonomy v2


def test_meals_quest_item_completes_automatically(client, profile):
    quest = client.get("/game/summary").json()["quest"]
    nutrition_item = next(q for q in quest if q["kind"] == "nutrition")
    banana = food_id(client, "Banana")
    egg = food_id(client, "Boiled egg")
    chicken = food_id(client, "Chicken curry")
    # Enough for either variant: 3 meals, and > 112 g protein.
    for _ in range(3):
        client.post(
            "/meals",
            json={
                "meal_type": "lunch",
                "items": [
                    {"food_id": banana, "portions": 1},
                    {"food_id": egg, "portions": 4},
                    {"food_id": chicken, "portions": 1},
                ],
            },
        )
    quest = client.get("/game/summary").json()["quest"]
    done = next(q for q in quest if q["id"] == nutrition_item["id"])
    assert done["completed_at"] is not None


def test_manual_quest_item_and_streak(client, profile, clock):
    quest = client.get("/game/summary").json()["quest"]
    manual = next(q for q in quest if q["kind"] == "recovery")
    r = client.post(f"/game/quests/{manual['id']}/complete")
    assert r.status_code == 200
    summary = client.get("/game/summary").json()
    # v1.3 (review S2): a ticked quest item earns XP but only training keeps the streak.
    assert summary["streak"]["current"] == 0
    assert summary["xp"]["total"] >= manual["xp"]

    auto = next(q for q in quest if q["kind"] == "nutrition")
    assert client.post(f"/game/quests/{auto['id']}/complete").status_code == 409

    # Next day: yesterday's item no longer completable
    clock.now += timedelta(days=1)
    assert client.post(f"/game/quests/{manual['id']}/complete").status_code == 404


def test_missed_day_gets_comeback_item(client, profile, clock):
    client.get("/game/summary")
    clock.now += timedelta(days=2)
    codes = [q["code"] for q in client.get("/game/summary").json()["quest"]]
    assert "comeback" in codes


def test_only_training_keeps_the_streak(client, profile, clock):
    """v1.3 (review S2): a meal or a weigh-in earns XP but no longer keeps the streak; a
    single logged set does."""
    from tests.api.test_workouts import exercise_id

    clock.now += timedelta(days=1)
    s = client.get("/game/summary").json()["streak"]
    assert s["active_today"] is False
    client.post(
        "/meals",
        json={
            "meal_type": "snack",
            "items": [{"food_id": food_id(client, "Banana"), "portions": 1}],
        },
    )
    assert client.post("/body-metrics", json={"weight_kg": 70.4}).status_code == 201
    assert client.get("/game/summary").json()["streak"]["active_today"] is False

    w = client.post("/workouts").json()["id"]  # one set, workout left open
    bench = exercise_id(client, "Barbell Bench Press")
    client.post(f"/workouts/{w}/sets", json={"exercise_id": bench, "weight_kg": 40, "reps": 8})
    s = client.get("/game/summary").json()["streak"]
    assert s["current"] == 1 and s["active_today"] is True
