"""System notices: deload advised, target raised, muscle recovered. Each has a stable id
and appears only while it is true."""

from datetime import timedelta

from tests.api.test_deload import _week_of_sessions
from tests.api.test_intelligence_progression import session
from tests.api.test_workouts import exercise_id


def codes(client):
    return [n["code"] for n in client.get("/intelligence/notices").json()]


def test_a_new_user_hears_nothing(client, profile):
    assert client.get("/intelligence/notices").json() == []


def test_target_raised_after_the_session_that_earned_it(client, profile, clock):
    bench = exercise_id(client, "Barbell Bench Press")
    session(client, clock, bench, [(60, 10, 8)] * 3, days_later=0.5)
    notices = client.get("/intelligence/notices").json()
    raised = next(n for n in notices if n["code"] == "raised")
    assert raised["title"] == "Target raised"
    assert raised["text"].startswith("Barbell Bench Press: next time 3 \u00d7 6 @ 62.5 kg.")
    assert raised["id"].endswith(f":{bench}")
    # 36 hours after the session it is old news
    clock.now += timedelta(hours=40)
    assert "raised" not in codes(client)


def test_muscle_recovered_when_todays_quest_trains_it(client, profile, clock):
    bench = exercise_id(client, "Barbell Bench Press")
    session(client, clock, bench, [(60, 8, 9)] * 2, days_later=0)
    clock.now += timedelta(hours=80)  # 2 ES on lower chest: 95 % ready after 72 h
    notices = client.get("/intelligence/notices").json()
    rec = next(n for n in notices if n["code"] == "recovered")
    assert rec["title"] == "Muscle recovered"
    assert rec["text"].startswith("Mid and lower chest is ") and "Today's quest:" in rec["text"]
    clock.now += timedelta(days=3)  # trained too long ago to be news
    assert "recovered" not in codes(client)


def test_deload_advised(client, profile, clock):
    bench = exercise_id(client, "Barbell Bench Press")
    clock.now -= timedelta(days=clock.now.weekday())
    for _ in range(3):
        _week_of_sessions(client, clock, bench, 3)
    d = next(n for n in client.get("/intelligence/notices").json() if n["code"] == "deload")
    assert d["title"] == "Deload advised" and "3 training weeks in a row" in d["text"]
    client.post("/deload/start")
    assert "deload" not in codes(client)
