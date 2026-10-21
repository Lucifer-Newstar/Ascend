"""Two first requests of the day both build today's quest: the second must read the first's
rows instead of failing on the unique (day, code) index."""

from app.modules.gamification import service as game
from app.modules.gamification.models import QuestItem


def test_a_quest_written_by_a_concurrent_request_is_read_not_a_500(client, monkeypatch):
    factory = client.app.state.session_factory
    real = game.generate_daily_quest

    def racing(day, *args, **kwargs):
        specs = real(day, *args, **kwargs)
        # The other request commits the same quest while this one is still building it.
        with factory() as other:
            for s in specs:
                other.add(
                    QuestItem(
                        day=day, kind=s.kind, code=s.code, title=s.title, detail=s.detail,
                        metric=s.metric, target=s.target, xp=s.xp,
                        generator_version=game.GENERATOR_VERSION,
                    )
                )  # fmt: skip
            other.commit()
        return specs

    monkeypatch.setattr(game, "generate_daily_quest", racing)
    r = client.get("/game/summary")
    assert r.status_code == 200, r.text
    with factory() as db:
        assert db.query(QuestItem).count() == len(r.json()["quest"])
