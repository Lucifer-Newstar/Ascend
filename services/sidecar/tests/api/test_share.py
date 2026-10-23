from urllib.parse import unquote

import pytest


@pytest.mark.parametrize(
    ("payload", "headline", "words"),
    [
        ({"kind": "pr", "exercise": "Back Squat", "e1rm_kg": 120.5}, "Back Squat: 120.5 kg", "PR"),
        ({"kind": "skill", "skill": "Muscle-up", "step": "Pull-up"}, "Pull-up", "Unlocked"),
        ({"kind": "streak", "days": 30}, "30 days", "streak"),
        ({"kind": "boss", "boss": "The Iron Warden", "title": "Wardenbreaker"}, "The Iron Warden",
         "boss"),
        ({"kind": "program", "program": "5x5", "sessions": 12}, "5x5", "block"),
        ({"kind": "rank", "rank": "C"}, "Rank C", "rank"),
    ],
)  # fmt: skip
def test_cards(client, payload, headline, words):
    r = client.post("/share/card", json={"payload": payload})
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["headline"] == headline and words in c["caption"]
    assert c["caption"].endswith("#ASCEND #calisthenics") and len(c["caption"]) <= 280
    assert c["x_url"].startswith("https://x.com/intent/tweet?text=")
    assert unquote(c["x_url"].split("=", 1)[1]) == c["caption"]


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "selfie"},
        {"kind": "pr", "exercise": "Bench Press"},
        {"kind": "pr", "exercise": "Bench Press", "e1rm_kg": -5},
        {"kind": "streak", "days": True},
    ],
)
def test_bad_cards(client, payload):
    assert client.post("/share/card", json={"payload": payload}).status_code == 422


def test_profile_data_never_enters_a_caption(client, profile):
    c = client.post(
        "/share/card",
        json={"payload": {"kind": "streak", "days": 7, "weight_kg": 70, "name": "Navin"}},
    ).json()
    assert "70" not in c["caption"] and "Navin" not in c["caption"]
