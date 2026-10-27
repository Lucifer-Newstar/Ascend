"""v1.3 food search: the whole table, everyday names, and foods of your own."""

from __future__ import annotations

from fastapi.testclient import TestClient


def names(client: TestClient, q: str) -> list[str]:
    return [f["name"] for f in client.get("/foods", params={"q": q}).json()]


def test_an_empty_search_lists_every_food(client: TestClient) -> None:
    every = names(client, "")
    assert len(every) > 150 and "Ven pongal" in every and every == sorted(every)
    assert len(client.get("/foods", params={"q": "", "limit": 10}).json()) == 10


def test_the_plain_dish_comes_first(client: TestClient) -> None:
    assert names(client, "pongal")[:2] == ["Ven pongal", "Sakkarai pongal"]
    assert names(client, "milk")[0] == "Milk (toned)"
    assert names(client, "tea")[0] == "Masala chai (milk, sugar)"
    assert names(client, "chapathi")[0] == "Chapati"
    assert names(client, "dosa")[0] == "Plain dosa"


def test_a_food_of_your_own_is_searchable(client: TestClient) -> None:
    r = client.post(
        "/foods",
        json={"name": "Kozhukattai", "portion_label": "1 piece", "portion_g": 60, "kcal": 120,
              "protein_g": 3, "carbs_g": 22, "fat_g": 2},
    )  # fmt: skip
    assert r.status_code == 201
    found = names(client, "kozhu")  # v1.4 also has three kozhukattai dishes in the table
    assert found[0] == "Kozhukattai" and "Pidi kozhukattai" in found
