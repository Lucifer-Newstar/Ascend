"""Trainer chat battery: 352 everyday messages through the real app with the AI off.

Each message has an expectation ("set:push-up|reps=10|sets=1", "meal:idli|p=2",
"hold:plank|s=60", "weight:42", "multi", "ask", "follow", "erase", ...). Structured ones are
checked automatically; answers, greetings and out-of-scope asks are listed for a person
to read (they are "judge" rows, never counted as passes).

    cd services/sidecar && uv run python -m eval.trainer_chat [--show-fails]
"""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

HERE = Path(__file__).parent
MESSAGES = HERE / "trainer_chat_messages.json"
RESULTS = HERE / "results" / "trainer_chat.json"
TOKEN = "trainer-chat"
PROFILE = {
    "name": "Tester", "age": 21, "sex": "male", "height_cm": 170, "weight_kg": 42,
    "goal": "bulk", "activity": "moderate", "equipment": ["dumbbells", "rings"],
}  # fmt: skip
NAMES = {
    "push-up": ("push up",),
    "pull": ("pull up", "chin up", "pull", "row"),
    "tea": ("tea", "chai"),
    "chapati": ("chapati", "roti", "phulka"),
    "parotta": ("parotta", "porotta"),
}


def norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def items(p: dict[str, Any]) -> list[dict[str, Any]]:
    params = p.get("params") or {}
    return [params, *(params.get("more") or [])]


def check(text: str, exp: str, resp: dict[str, Any]) -> bool | None:
    """True / False for a structured expectation, None when a person has to judge."""
    p = resp.get("proposal") or {}
    kind = p.get("kind")
    summ = norm(" ".join(p.get("summary") or []))
    head, _, rest = exp.partition(":")
    name, *parts = rest.split("|") if rest else [""]
    kv = dict(x.split("=", 1) for x in parts if "=" in x)
    names = NAMES.get(name, (norm(name),))
    if head == "set":
        if kind != "log_set":
            return False
        first = items(p)[0]
        ok = name == "dumbbell" and "dumbbell" in summ or any(n in summ for n in names)
        if "reps" in kv and name != "dumbbell":
            ok = ok and int(first.get("reps") or 0) == int(kv["reps"])
        if "sets" in kv:
            ok = ok and int(first.get("sets") or 1) == int(kv["sets"])
        if "kg" in kv and name != "dumbbell":
            ok = ok and abs(float(first.get("weight_kg") or 0) - float(kv["kg"])) <= 2.5
        return ok
    if head == "hold":
        first = items(p)[0]
        ok = kind == "log_hold" and any(n in summ for n in names)
        ok = ok and int(first.get("seconds") or 0) == int(kv["s"])
        if "sets" in kv:
            ok = ok and int(first.get("sets") or 1) == int(kv["sets"])
        return ok
    if head == "weight":
        got = float((p.get("params") or {}).get("weight_kg") or 0)
        return kind == "log_weight" and abs(got - float(name)) < 0.05
    if head == "meal":
        if name == "notintable":
            return kind is None and "food" in (resp.get("reply") or "").lower()
        if kind != "log_meal":
            return False
        its = items(p)
        if name == "halfp":
            return any(float(i.get("portions") or 1) % 1 for i in its)
        ok = name == "late-alpha" or any(n in summ for n in names)
        if "p" in kv:
            ok = ok and any(abs(float(i.get("portions") or 1) - float(kv["p"])) < 0.01 for i in its)
        return ok
    if head == "multi":
        # A combo ("dal rice") is one food entry that logs two foods: the card lists both.
        many = len(items(p)) >= 2 or len(p.get("summary") or []) >= 3
        return kind in ("log_meal", "log_set") and many
    if head == "follow":
        return kind == "follow_program"
    if head == "erase":
        scoped = text in ("remove all meals", "delete all workouts")
        return kind != "erase_data" if scoped else kind == "erase_data"
    if head == "ask":  # two different dishes match: the trainer asks which one
        return kind is None and "which" in (resp.get("reply") or "").lower()
    if head == "no_action":
        return kind is None
    if head == "plan":  # v1.4: a plan-builder fact becomes a "update your plan" card
        return kind == "build_plan" and norm(name) in summ
    if head == "pace":  # v1.4: too fast to plan, said plainly with realistic targets
        return kind is None and "won't plan it" in (resp.get("reply") or "")
    return None


def run() -> list[dict[str, Any]]:
    rows = json.loads(MESSAGES.read_text(encoding="utf-8"))
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        settings = Settings(
            data_dir=d, db_url=f"sqlite:///{d / 'chat.db'}", token=TOKEN,
            ollama_host="http://127.0.0.1:9",
        )  # fmt: skip
        app = create_app(settings, clock=lambda: datetime(2026, 10, 25, 15, 30), outbox_interval=0)
        headers = {"Authorization": f"Bearer {TOKEN}"}
        with TestClient(app, headers=headers, raise_server_exceptions=False) as c:
            c.put("/profile", json=PROFILE)
            for cat, text, exp in rows:
                r = c.post("/trainer/chat", json={"text": text})
                resp = r.json() if r.status_code == 200 else {"error": r.status_code}
                verdict = check(text, exp, resp)
                out.append({"cat": cat, "text": text, "exp": exp, "verdict": verdict,
                            "reply": resp.get("reply"),
                            "proposal": (resp.get("proposal") or {}).get("summary")})  # fmt: skip
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--show-fails", action="store_true")
    args = ap.parse_args()
    rows = run()
    tally = Counter(
        "judge" if r["verdict"] is None else ("pass" if r["verdict"] else "fail") for r in rows
    )
    RESULTS.write_text(json.dumps({"tally": tally, "rows": rows}, indent=1), encoding="utf-8")
    print(f"{len(rows)} messages: {tally['pass']} pass, {tally['fail']} fail, "
          f"{tally['judge']} to read by hand -> {RESULTS.relative_to(HERE.parent)}")  # fmt: skip
    if args.show_fails:
        for r in rows:
            if r["verdict"] is False:
                got = r["proposal"] or r["reply"]
                print(f"FAIL [{r['cat']}] {r['text']!r} expected {r['exp']}: {got}")


if __name__ == "__main__":
    main()
