"""v1.2 wave 1: the audit fixes on the sidecar side (loadout, programs, food, chat, themes)."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient

NO_GEAR = {
    "name": "Ravi",
    "age": 20,
    "sex": "male",
    "height_cm": 170,
    "weight_kg": 45,
    "goal": "bulk",
    "activity": "light",
    "focus": "muscle",
    "equipment": ["none"],
}


def ex(client: TestClient, name: str) -> dict:
    return next(e for e in client.get("/exercises", params={"q": name}).json() if e["name"] == name)


# --- loadout ---------------------------------------------------------------------------


def test_gear_moves_are_no_longer_listed_as_bodyweight(client: TestClient) -> None:
    assert ex(client, "Pull-up")["equipment"] == "bar"
    assert ex(client, "Hanging Leg Raise")["equipment"] == "bar"
    assert ex(client, "Chest Dip")["equipment"] == "parallel_bars"
    names = {e["name"] for e in client.get("/exercises", params={"q": "BJJ"}).json()}
    assert "BJJ Rolling" not in names  # partner-only: archived


def test_a_no_gear_quest_never_suggests_gear(client: TestClient, clock) -> None:
    client.get("/game/summary")  # a quest drawn before setup (no profile, nothing filtered)
    client.put("/profile", json=NO_GEAR)
    for _ in range(10):
        q = client.get("/game/summary").json()["quest"][0]
        if q["kind"] == "training" and "Suggested:" in q["detail"]:
            name = q["detail"].split("Suggested: ")[1].split(".")[0]
            assert ex(client, name)["equipment"] in ("bodyweight", "none", "mat"), name
        clock.now += timedelta(days=1)


def test_programs_for_the_kit(client: TestClient) -> None:
    client.put("/profile", json=NO_GEAR)
    progs = {p["key"]: p for p in client.get("/plans/programs").json()}
    assert progs["bodyweight_starter_3"]["fits_equipment"] is True
    assert progs["bar_floor_starter_3"]["fits_equipment"] is False
    assert progs["full_body_3"]["fits_equipment"] is False


# --- following a program ---------------------------------------------------------------


def test_a_bodyweight_program_advances_and_shows_holds_in_seconds(
    client: TestClient, clock
) -> None:
    client.put("/profile", json=NO_GEAR)
    plan = client.put("/plans/current", json={"program_key": "bodyweight_starter_3"}).json()
    items = {i["exercise"]: i for i in plan["next"]["items"]}
    plank = items["Plank"]
    assert plank["measure"] == "hold" and (plank["rep_low"], plank["rep_high"]) == (20, 30)
    assert items["Bodyweight Squat"]["section"] == "calisthenics"
    w = client.post("/workouts", json={"section": "calisthenics"}).json()
    for name in ("Bodyweight Squat", "Incline Push-up", "Single-leg Glute Bridge"):
        client.post(
            f"/workouts/{w['id']}/sets", json={"exercise_id": ex(client, name)["id"], "reps": 8}
        )
    client.post(f"/workouts/{w['id']}/finish")
    clock.now += timedelta(days=1)
    nxt = client.get("/plans/current").json()
    assert nxt["sessions_done"] == 1 and nxt["next"]["key"] == "b1"


def test_generated_plans_respect_the_baseline(client: TestClient) -> None:
    client.put("/profile", json={**NO_GEAR, "equipment": ["none", "pullup_bar"]})
    client.post("/profile/baseline", json={"pushups": 3, "pullups": 1})
    draft = client.post(
        "/planner/workout", json={"days_per_week": 3, "minutes": 45, "focus": "muscle"}
    ).json()["draft"]
    slots = [s for d in draft["days"] for s in d["slots"]]
    names = {s["exercise"] for s in slots}
    assert not names & {"Pull-up", "Chin-up", "Push-up", "Diamond Push-up"}
    for s in slots:
        if s["exercise"] in ("Hollow Body Hold", "Plank", "Side Plank", "Dead Hang"):
            assert s["rep_low"] >= 20  # seconds, not "1-1"


def test_goal_check_for_an_underweight_gain(client: TestClient) -> None:
    client.put("/profile", json=NO_GEAR)  # 45 kg at 170 cm: BMI 15.6
    r = client.post(
        "/planner/check",
        json={"weight_kg": 45, "target_weight_kg": 55, "weeks": 12},
    ).json()
    text = " ".join(f["message"] for f in r["flags"])
    assert "63 weeks" not in text and "25 weeks" in text


# --- food ------------------------------------------------------------------------------


def test_the_food_list_has_the_staples_and_takes_your_own(client: TestClient) -> None:
    assert len(client.get("/foods", params={"q": ""}).json()) == 50  # capped page
    for q in ("milk", "oats", "paneer", "maggi", "chicken breast", "omelette"):
        assert client.get("/foods", params={"q": q}).json(), q
    mine = client.post(
        "/foods",
        json={"name": "Amma's sundal", "portion_label": "1 katori", "portion_g": 100,
              "kcal": 160, "protein_g": 8, "carbs_g": 22, "fat_g": 4},
    )  # fmt: skip
    assert mine.status_code == 201 and mine.json()["source"] == "custom"
    assert client.post("/foods", json={"name": "milk (toned)", "kcal": 1}).status_code == 409
    idli = client.get("/foods", params={"q": "idli"}).json()[0]
    assert client.delete(f"/foods/{idli['id']}").status_code == 409  # built-in stays
    assert client.delete(f"/foods/{mine.json()['id']}").status_code == 204


# --- one chat box ----------------------------------------------------------------------


def chat(client: TestClient, text: str) -> dict:
    return client.post("/trainer/chat", json={"text": text}).json()


def test_natural_logging_lines_become_proposals(client: TestClient) -> None:
    client.put("/profile", json=NO_GEAR)
    r = chat(client, "10 pushups")
    assert r["intent"] == "action" and "Push-up" in r["proposal"]["summary"][0]
    r = chat(client, "log 12 squats")
    assert "Bodyweight Squat" in r["proposal"]["summary"][0]
    r = chat(client, "2 idli for breakfast")
    assert "Idli" in r["proposal"]["summary"][0]
    r = chat(client, "chicken breast 200g")
    assert "Chicken breast" in r["proposal"]["summary"][0]


def test_beginner_questions_without_local_ai(client: TestClient) -> None:
    client.put("/profile", json=NO_GEAR)
    # No program yet: where to start for this kit, not the day's protein or muscle tip.
    first = chat(client, "What should I train today?")
    assert first["intent"] == "train_today" and first["source"] == "rules"
    assert first["reply"].startswith("You don't follow a program yet. With your kit, start with")
    assert "protein" not in first["reply"].lower()
    client.put("/plans/current", json={"program_key": "bodyweight_starter_3"})
    today = chat(client, "What should I train today?")
    assert today["source"] == "rules" and "Starter A" in today["reply"]
    missed = chat(client, "i missed yesterday because i was sick")
    assert missed["intent"] == "missed_day" and "ill" in missed["reply"]
    low = chat(client, "i feel overwhelmed")
    assert low["intent"] == "feeling" and "Local AI" not in low["reply"]
    pick = chat(client, "I only have a pull-up bar, what program?")
    assert pick["intent"] == "program_pick"
    faq = chat(client, "how many days a week should I train")
    assert faq["intent"] == "faq" and "Three days" in faq["reply"]
    unknown = chat(client, "what is the capital of peru")
    assert unknown["reply"].count("Local AI") == 0


# --- themes ----------------------------------------------------------------------------


def test_themes_free_and_locked(client: TestClient, profile) -> None:
    themes = {t["key"]: t for t in client.get("/game/themes").json()}
    assert [k for k, t in themes.items() if t["free"]] == ["shadow", "dark", "light"]
    assert themes["crimson"]["unlocked"] is False
    assert themes["crimson"]["requirement"] == "Reach a 7-day streak"
    assert client.put("/settings", json={"theme": "crimson"}).status_code == 409
    assert client.put("/settings", json={"theme": "light"}).json()["theme"] == "light"
    assert client.get("/settings").json()["theme"] == "light"


def test_new_players_start_on_shadow(client: TestClient) -> None:
    assert client.get("/settings").json()["theme"] == "shadow"


def test_background_art_can_be_dimmed_or_turned_off(client: TestClient) -> None:
    assert client.get("/settings").json()["background_art"] == "on"
    assert client.put("/settings", json={"background_art": "dim"}).json()["background_art"] == "dim"
    assert client.put("/settings", json={"background_art": "loud"}).status_code == 422


# --- plain language --------------------------------------------------------------------


def test_muscles_have_plain_names_and_the_latin_in_detail(client: TestClient, profile) -> None:
    hams = next(m for m in client.get("/muscles").json() if m["key"] == "biceps_femoris")
    assert hams["label"] == "Hamstrings (outer)"
    detail = client.get("/muscles/biceps_femoris/history").json()
    assert detail["latin"] == "Biceps femoris"
