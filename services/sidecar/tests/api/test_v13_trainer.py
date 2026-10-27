"""v1.3 trainer chat: food matching, multi-item meals, kit-aware exercises, text replies."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

KIT = {
    "name": "Navin", "age": 21, "sex": "male", "height_cm": 170, "weight_kg": 42,
    "goal": "bulk", "activity": "moderate", "equipment": ["dumbbells", "rings"],
}  # fmt: skip


@pytest.fixture
def kit(client: TestClient) -> TestClient:
    assert client.put("/profile", json=KIT).status_code == 200
    return client


def chat(client: TestClient, text: str) -> dict:
    r = client.post("/trainer/chat", json={"text": text})
    assert r.status_code == 200, r.text
    return r.json()


def summary(r: dict) -> str:
    return " ".join((r.get("proposal") or {}).get("summary") or [])


@pytest.mark.parametrize(
    ("text", "food"),
    [
        ("2 egg", "Boiled egg"),
        ("2 eggs", "Boiled egg"),
        ("had milk", "Milk (toned)"),
        ("2 dosa", "Plain dosa"),
        ("2 vada", "Medu vada"),
        ("1 tea", "Masala chai"),
        ("had paneer", "Paneer (plain)"),
        ("rice 150g", "Steamed rice"),
        ("chicken 200g", "Chicken breast (grilled)"),
        ("3 chapathi", "Chapati"),
        ("2 parotta", "Parotta"),
        ("pongal for breakfast", "Ven pongal"),
        ("ven pongal", "Ven pongal"),
        ("tender coconut water", "Tender coconut water"),
    ],
)
def test_the_food_people_mean(kit: TestClient, text: str, food: str) -> None:
    r = chat(kit, text)
    assert r["proposal"] and r["proposal"]["kind"] == "log_meal", r
    assert food in summary(r)


def test_two_different_dishes_get_a_question(kit: TestClient) -> None:
    r = chat(kit, "1 biryani for lunch")
    assert r["proposal"] is None and "Which biryani" in r["reply"]
    assert "1 chicken biryani for lunch" in r["suggestions"]


def test_a_food_not_in_the_table_offers_to_add_it(kit: TestClient) -> None:
    r = chat(kit, "1 kuzhi paniyaram")
    assert r["proposal"] is None and "add it as your own food" in r["reply"]
    assert r["actions"][0]["target"] == "diet/add-food/kuzhi%20paniyaram"


def test_kozhukattai_asks_which_one(kit: TestClient) -> None:
    # v1.4: three kozhukattai dishes are in the table now
    r = chat(kit, "1 kozhukattai")
    assert r["proposal"] is None and "Which kozhukattai" in r["reply"]
    assert "Pidi kozhukattai" in summary(chat(kit, "1 pidi kozhukattai"))
    assert "Coconut chutney" in summary(chat(kit, "1 thengai chutney"))


def test_a_multi_item_meal_is_one_card(kit: TestClient) -> None:
    r = chat(kit, "1 ven pongal and 1 coconut chutney for breakfast")
    p = r["proposal"]
    assert p["kind"] == "log_meal" and p["params"]["meal_type"] == "breakfast"
    assert "Ven pongal" in summary(r) and "Coconut chutney" in summary(r)
    done = kit.post(f"/actions/{p['id']}/confirm", json={}).json()
    assert done["status"] == "executed"
    meal = kit.get(f"/meals/{done['result']['meal_id']}")
    if meal.status_code == 200:
        assert len(meal.json()["items"]) == 2
    assert kit.post(f"/actions/{p['id']}/undo").json()["status"] == "undone"


def test_sets_follow_the_kit_on_every_path(kit: TestClient) -> None:
    assert "Bodyweight Squat" in summary(chat(kit, "3x12 squats"))
    assert "Bodyweight Squat" in summary(chat(kit, "10 squats"))
    r = chat(kit, "pushups 3x10")
    assert r["proposal"]["params"]["sets"] == 3 and r["proposal"]["params"]["weight_kg"] == 0
    assert "Dumbbell Bench Press" in summary(chat(kit, "bench 20kg 8 reps"))
    assert "Ring Dip" in summary(chat(kit, "dips 12"))
    assert "Pull-up" in summary(chat(kit, "pullups 7"))


def test_typos_and_new_moves(kit: TestClient) -> None:
    assert "Push-up" in summary(chat(kit, "15 pushpus"))
    assert "Burpee" in summary(chat(kit, "15 burpees"))
    assert "Wall Sit" in summary(chat(kit, "wall sit 45s"))
    assert "Dead Hang" in summary(chat(kit, "hang 60s"))


def test_holds_in_minutes_and_sets(kit: TestClient) -> None:
    r = chat(kit, "3x30s plank")
    assert r["proposal"]["params"] | {"seconds": 30, "sets": 3} == r["proposal"]["params"]
    p = chat(kit, "plank 1:30")["proposal"]
    assert p["params"]["seconds"] == 90 and "1:30 min" in p["summary"][0]


def test_yes_no_and_undo_typed_after_a_card(kit: TestClient) -> None:
    card = chat(kit, "10 pushups")["proposal"]
    r = chat(kit, "yes")
    assert r["proposal"]["id"] == card["id"] and r["proposal"]["status"] == "executed"
    r = chat(kit, "undo")
    assert r["proposal"]["status"] == "undone"
    card = chat(kit, "2 idli")["proposal"]
    assert chat(kit, "no")["proposal"]["status"] == "cancelled"
    assert kit.get("/actions/log").status_code in (200, 404)


def test_yes_never_confirms_an_erase(kit: TestClient) -> None:
    card = chat(kit, "delete everything")["proposal"]
    assert card["kind"] == "erase_data"
    r = chat(kit, "yes")
    assert (r.get("proposal") or {}).get("status") != "executed"


def test_scoped_deletes_never_offer_the_full_erase(kit: TestClient) -> None:
    for text in ("remove all meals", "delete all workouts"):
        r = chat(kit, text)
        assert r["intent"] == "scoped_delete" and r["proposal"] is None, text


def test_my_numbers(kit: TestClient, clock) -> None:
    card = chat(kit, "2 idli for breakfast")["proposal"]
    kit.post(f"/actions/{card['id']}/confirm", json={})
    assert "kcal" in chat(kit, "how many calories today")["reply"]
    assert "Idli" in chat(kit, "what did i eat today")["reply"]
    assert "14.5" in chat(kit, "what is my bmi")["reply"]
    assert "streak is 0" in chat(kit, "what's my streak")["reply"]
    assert chat(kit, "how much protein should I eat")["intent"] == "faq"


def test_add_food_from_the_chat(kit: TestClient) -> None:
    r = chat(kit, "add food kozhukattai 120 kcal 3g protein 22g carbs 2g fat per piece")
    p = r["proposal"]
    assert p["kind"] == "add_food" and p["params"]["kcal"] == 120
    assert p["params"]["protein_g"] == 3 and p["params"]["portion_label"] == "1 piece"
    kit.post(f"/actions/{p['id']}/confirm", json={})
    assert "Kozhukattai" in summary(chat(kit, "1 kozhukattai"))
    assert "calories too" in chat(kit, "add food ragi dosa")["reply"]


def test_workout_today_and_short_replies(kit: TestClient) -> None:
    assert chat(kit, "what's my workout today")["intent"] == "train_today"
    for text in ("ok", "lol", "bye", "\U0001f44d"):
        assert chat(kit, text)["intent"] == "small_talk", text


def test_programs_swap_moves_the_kit_cant_do(kit: TestClient, clock) -> None:
    p = chat(kit, "follow ppl")["proposal"]
    kit.post(f"/actions/{p['id']}/confirm", json={})
    clock.now += timedelta(days=1)
    reply = chat(kit, "what should i train today")["reply"]
    assert "Barbell" not in reply, reply


def test_gaining_from_underweight_is_not_blocked(kit: TestClient) -> None:
    r = chat(kit, "can I gain 5 kg in 2 months")
    assert "won't plan" not in r["reply"] and "healthy pace" in r["reply"]
