"""Answer samples: real questions through the real app with the AI off, for hand grading.

The questions are kept outside the repo (they come from Stack Exchange, CC BY-SA 4.0, and
are only used to measure). Give a JSON list of {"id", "text"}; the replies, the speaker, the
handoff line and the citations are written next to it for a person to grade with the
answer-quality rubric in docs/ai/evaluation.md (correct / direct / personal / voice / safe).

    cd services/sidecar && uv run python -m eval.answer_samples QUESTIONS.json OUT.json
"""

from __future__ import annotations

import argparse
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from eval.trainer_chat import PROFILE, TOKEN


def run(questions: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        settings = Settings(
            data_dir=d, db_url=f"sqlite:///{d / 'samples.db'}", token=TOKEN,
            ollama_host="http://127.0.0.1:9",
        )  # fmt: skip
        app = create_app(settings, clock=lambda: datetime(2026, 10, 25, 15, 30), outbox_interval=0)
        headers = {"Authorization": f"Bearer {TOKEN}"}
        with TestClient(app, headers=headers, raise_server_exceptions=False) as c:
            c.put("/profile", json=PROFILE)
            for q in questions:
                r = c.post("/trainer/chat", json={"text": q["text"]})
                resp = r.json() if r.status_code == 200 else {"error": r.status_code}
                out.append({
                    "id": q["id"], "text": q["text"], "reply": resp.get("reply"),
                    "intent": resp.get("intent"), "source": resp.get("source"),
                    "speaker": resp.get("speaker"), "handoff": resp.get("handoff"),
                    "suggestions": resp.get("suggestions"),
                    "citations": [x.get("passage_id") for x in resp.get("citations") or []],
                })  # fmt: skip
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("questions", type=Path)
    ap.add_argument("out", type=Path)
    a = ap.parse_args()
    rows = run(json.loads(a.questions.read_text(encoding="utf-8")))
    a.out.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(rows)} answers -> {a.out}")


if __name__ == "__main__":
    main()
