"""recovery-v2 in the app: /muscles, /intelligence/recovery, the check-in modifier, the
personal factors and the dose rebuild that migration 0014 runs."""

from datetime import timedelta

from sqlalchemy import create_engine, text

from app.modules.intelligence import doses
from tests.api.test_workouts import exercise_id


def _bench(client, w, n=3, rpe=9):
    bench = exercise_id(client, "Barbell Bench Press")
    for _ in range(n):
        client.post(
            f"/workouts/{w}/sets",
            json={"exercise_id": bench, "weight_kg": 80, "reps": 6, "rpe": rpe},
        )


def _state(rows, key):
    return next(m for m in rows if m["key"] == key)


def test_muscles_carry_population_readiness_and_version(client, profile, clock):
    w = client.post("/workouts").json()["id"]
    _bench(client, w)
    clock.now += timedelta(hours=6)
    chest = _state(client.get("/muscles").json(), "pec_major_sternal")
    assert chest["algo_version"] == "recovery-v2"
    # no personal factor yet: population and personal readiness agree
    assert chest["readiness_population"] == chest["readiness"]
    assert chest["readiness"] < 1


def test_recovery_endpoint_explains_every_number(client, profile, clock):
    w = client.post("/workouts").json()["id"]
    _bench(client, w)
    clock.now += timedelta(hours=12)
    body = client.get("/intelligence/recovery").json()
    assert body["algo_version"].startswith("recovery-v2")
    assert len(body["muscles"]) == 54  # taxonomy v2
    assert {g["group"] for g in body["groups"]} == {
        "Push",
        "Shoulders",
        "Pull",
        "Arms",
        "Core",
        "Legs",
    }
    chest = _state(body["muscles"], "pec_major_sternal")
    # 3 sets at RPE 9 (I = 1) x weight 1.0 = 3 ES, 12 h at a 36 h half-life
    assert chest["fatigue"] == round(3 * 2 ** (-12 / 36), 3)
    assert chest["why"]["inputs"]["capacity_C"] == 10
    assert chest["why"]["inputs"]["personal_k"] == 1.0
    assert chest["top_sets"][0]["exercise"] == "Barbell Bench Press"
    assert body["checkin"] is None


def test_poor_sleep_and_soreness_lower_todays_readiness(client, profile, clock):
    w = client.post("/workouts").json()["id"]
    _bench(client, w, n=4)
    clock.now += timedelta(hours=20)
    before = _state(client.get("/muscles").json(), "pec_major_sternal")["readiness"]
    r = client.post("/checkins", json={"sleep": 1, "energy": 3, "soreness": "a_lot", "mood": 3})
    assert r.status_code in (200, 201)
    after = client.get("/intelligence/recovery").json()
    chest = _state(after["muscles"], "pec_major_sternal")
    assert after["checkin"] == {"sleep": 1, "soreness": "a_lot"}
    assert chest["modifier"] == 1.45
    assert chest["readiness"] < before


def test_finishing_a_session_refits_the_personal_factors(client, profile, clock):
    w = client.post("/workouts").json()["id"]
    _bench(client, w)
    clock.now += timedelta(minutes=30)
    client.post(f"/workouts/{w}/finish")
    groups = {g["group"]: g for g in client.get("/intelligence/recovery").json()["groups"]}
    # one session is no evidence: the population value, but a stored, dated row
    assert groups["Push"]["k"] == 1.0 and groups["Push"]["personal"] is False
    assert groups["Push"]["updated_at"] is not None


def test_dose_rebuild_round_trips(client, profile, settings, clock):
    w = client.post("/workouts").json()["id"]
    _bench(client, w, rpe=7)  # RIR 3: recovery-v2 0.9 per set, load-v1 1.0
    engine = create_engine(settings.db_url)
    with engine.begin() as conn:
        v2 = conn.execute(text("SELECT muscle, es, formula_version FROM muscle_load_events")).all()
        assert {r[2] for r in v2} == {"recovery-v2"}
        assert doses.rebuild(conn, version="load-v1") == len(v2)
        v1 = {r[0]: r[1] for r in conn.execute(text("SELECT muscle, es FROM muscle_load_events"))}
        assert v1["pec_major_sternal"] == 1.0
        doses.rebuild(conn)
        again = conn.execute(text("SELECT muscle, es, formula_version FROM muscle_load_events"))
        assert sorted(again.all()) == sorted(v2)
