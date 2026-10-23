"""Two first requests of the week both spawn the weekly boss: the second must read the
first's raid instead of failing on the unique week_start index (a 500 seen in v1.2 QA)."""

from datetime import datetime

from app.modules.gamification import boss_service
from app.modules.gamification.models import BossRaid


def test_a_boss_spawned_by_a_concurrent_request_is_read_not_a_500(client, profile, monkeypatch):
    factory = client.app.state.session_factory
    real = boss_service._hp

    def racing(db, week):
        hp = real(db, week)
        # The other request commits this week's raid while this one is still building it.
        with factory() as other:
            other.add(
                BossRaid(
                    week_start=week, name="Iron Golem", title="Golem Breaker", hp=30,
                    hp_source="starter", hp_note="race", algo_version="boss-v2",
                    created_at=datetime(2026, 10, 20, 9), xp_awarded=0, tier="E",
                )
            )  # fmt: skip
            other.commit()
        return hp

    monkeypatch.setattr(boss_service, "_hp", racing)
    r = client.get("/game/boss")
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Iron Golem"
    with factory() as db:
        assert db.query(BossRaid).count() == 1
