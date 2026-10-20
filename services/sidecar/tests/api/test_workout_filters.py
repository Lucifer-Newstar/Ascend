from datetime import timedelta

from tests.api.test_workouts import exercise_id


def log_session(client, clock, name, days_ago, **set_fields):
    clock.now -= timedelta(days=days_ago)
    w = client.post("/workouts").json()["id"]
    client.post(
        f"/workouts/{w}/sets", json={"exercise_id": exercise_id(client, name), **set_fields}
    )
    client.post(f"/workouts/{w}/finish")
    clock.now += timedelta(days=days_ago)
    return w


def test_filter_by_section_and_day_range(client, profile, clock):
    gym_old = log_session(client, clock, "Back Squat", 10, weight_kg=80, reps=5)
    run = log_session(client, clock, "Running", 3, duration_s=1200)
    gym_new = log_session(client, clock, "Barbell Bench Press", 1, weight_kg=60, reps=8)

    def ids(**params):
        return [w["id"] for w in client.get("/workouts", params=params).json()]

    assert ids() == [gym_new, run, gym_old]
    assert ids(section="cardio") == [run]
    assert ids(section="gym") == [gym_new, gym_old]
    today = clock.now.date()
    assert ids(since=str(today - timedelta(days=5))) == [gym_new, run]
    assert ids(until=str(today - timedelta(days=5))) == [gym_old]
    assert ids(section="gym", since=str(today - timedelta(days=5))) == [gym_new]
    assert ids(source="hevy") == []


def test_filters_combine_with_keyset_paging(client, profile, clock):
    for d in (4, 3, 2, 1):
        log_session(client, clock, "Back Squat", d, weight_kg=80, reps=5)
    first = client.get("/workouts", params={"limit": 2, "section": "gym"}).json()
    rest = client.get(
        "/workouts", params={"limit": 2, "section": "gym", "before": first[-1]["started_at"]}
    ).json()
    assert len(first) == 2 and len(rest) == 2
    assert {w["id"] for w in first}.isdisjoint({w["id"] for w in rest})


def test_bad_filters_are_rejected(client, profile):
    assert client.get("/workouts", params={"section": "yoga"}).status_code == 422
    assert client.get("/workouts", params={"source": "fitbit"}).status_code == 422
    r = client.get("/workouts", params={"since": "2026-10-10", "until": "2026-10-01"})
    assert r.status_code == 422 and "since" in r.json()["detail"]
