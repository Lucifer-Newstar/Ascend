"""GET /game/boss and /game/titles (boss-v1, ADR-0022)."""

from datetime import timedelta

from tests.api.test_workouts import exercise_id


def _sets(client, ex, n, rpe=8):
    w = client.post("/workouts").json()["id"]
    for _ in range(n):
        r = client.post(
            f"/workouts/{w}/sets", json={"exercise_id": ex, "weight_kg": 50, "reps": 8, "rpe": rpe}
        )
        assert r.status_code == 201
    return w


def test_a_new_hunter_meets_a_starter_boss(client, profile, clock):
    b = client.get("/game/boss").json()
    assert b["hp_source"] == "starter" and b["hp"] == 20 and b["damage"] == 0
    assert b["defeated"] is False and b["bonus_xp"] == 150 and b["algo_version"] == "boss-v1"
    assert b["week_end"] > b["week_start"] and 0 <= b["days_left"] <= 6
    assert b["why"]["inputs"]["hp_source"] == "starter"
    assert client.get("/game/titles").json() == []


def test_logged_sets_damage_the_boss_and_beating_it_pays_once(client, profile, clock):
    clock.now -= timedelta(days=clock.now.weekday())  # Monday
    bench = exercise_id(client, "Barbell Bench Press")
    xp0 = client.get("/game/summary").json()["xp"]["total"]
    _sets(client, bench, 12)
    b = client.get("/game/boss").json()
    assert (b["damage"], b["hp_left"]) == (12, 8)
    clock.now += timedelta(days=2)
    _sets(client, bench, 8)
    b = client.get("/game/boss").json()
    assert b["defeated"] is True and b["hp_left"] == 0
    titles = client.get("/game/titles").json()
    assert [t["title"] for t in titles] == [b["title"]]
    xp1 = client.get("/game/summary").json()["xp"]["total"]
    client.get("/game/boss")  # settling again pays nothing more
    assert client.get("/game/summary").json()["xp"]["total"] == xp1
    assert xp1 - xp0 >= 150


def test_deleting_sets_takes_the_win_back_and_missing_costs_nothing(client, profile, clock):
    clock.now -= timedelta(days=clock.now.weekday())
    bench = exercise_id(client, "Barbell Bench Press")
    w = _sets(client, bench, 20)
    assert client.get("/game/boss").json()["defeated"] is True
    xp_won = client.get("/game/summary").json()["xp"]["total"]
    last = client.get(f"/workouts/{w}").json()["sets"][-1]["id"]
    assert client.delete(f"/workouts/{w}/sets/{last}").status_code == 204
    b = client.get("/game/boss").json()
    assert b["defeated"] is False and b["hp_left"] == 1
    assert client.get("/game/titles").json() == []
    assert client.get("/game/summary").json()["xp"]["total"] < xp_won

    # A week later: a new boss, sized from last week's 19 sets; the miss took nothing.
    xp_before = client.get("/game/summary").json()["xp"]["total"]
    clock.now += timedelta(days=7)
    nxt = client.get("/game/boss").json()
    assert nxt["name"] != b["name"] and nxt["hp_source"] == "history"
    assert nxt["hp"] == 12  # median of 0, 0, 0, 19 -> 0, clamped to the minimum
    assert client.get("/game/summary").json()["xp"]["total"] == xp_before
