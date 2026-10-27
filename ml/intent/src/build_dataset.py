"""Assemble the intent dataset: weak-labelled Stack Exchange titles + CLINC150 + templates.

Outputs (intent/dataset/, one JSON object per line: text, label, source, plus ids):
  train.jsonl            what the model learns from
  val.jsonl              model selection (C, n-gram ranges) only
  test_templates.jsonl   app commands from templates held out by template id
  test_clinc.jsonl       CLINC150's own test split (out-of-scope + mapped intents)
  test_se_hand.jsonl     the 200 hand-checked Stack Exchange titles (never trained on)
  stats.json             counts per split and label

Leak rules, all enforced here and tested in tests/test_intent_dataset.py:
  * hand-checked SE ids, the external real-question ids (labels/eval_leak_ids.txt) and the
    Stack Exchange ids of the held-out gap questions (labels/gap_eval_ids.txt, v1.4) never
    reach train or val;
  * an exact duplicate text (case/space-insensitive) is kept once, in the first split
    that claims it, with test splits claiming first.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clinc  # noqa: E402
import templates  # noqa: E402
import weak_label  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ML = ROOT.parent


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", text.lower())).strip()


def read_ids(path: Path) -> set[int]:
    if not path.exists():
        return set()
    lines = (x.strip() for x in path.read_text().splitlines())
    return {int(x) for x in lines if x and not x.startswith("#")}


def leak_ids_from(real_eval: Path, se_rows: list[dict]) -> set[int]:
    """SE ids whose title, or the opening of whose body, is a question in the real eval."""
    items = [norm(t) for _, t, _ in json.loads(real_eval.read_text(encoding="utf-8"))]
    out: set[int] = set()
    for r in se_rows:
        title, body = norm(r["title"]), norm(r["body_start"])
        for h in items:
            if (
                title == h
                or (len(body) >= 40 and h.startswith(body[:60]))
                or (len(h) >= 40 and body.startswith(h[:60]))
            ):
                out.add(int(r["id"]))
                break
    return out


def build(params: dict, raw: Path, out: Path, real_eval: Path | None = None) -> dict:
    rng = random.Random(params["seed"])
    se_rows = [json.loads(line) for line in (raw / "se_questions.jsonl").open(encoding="utf-8")]
    hand = {
        int(r["se_id"]): r["label"]
        for r in csv.DictReader((ROOT / "labels" / "se_handchecked.csv").open(encoding="utf-8"))
    }
    leak = read_ids(ROOT / "labels" / "eval_leak_ids.txt")
    leak |= read_ids(ROOT / "labels" / "gap_eval_ids.txt")
    if real_eval is not None and real_eval.exists():
        leak |= leak_ids_from(real_eval, se_rows)

    splits: dict[str, list[dict]] = {
        k: [] for k in ("test_se_hand", "test_templates", "test_clinc", "val", "train")
    }
    for r in se_rows:
        if r["id"] in hand:
            splits["test_se_hand"].append(
                {"text": r["title"], "label": hand[r["id"]], "source": "se_hand", "se_id": r["id"]}
            )

    for r in templates.generate(params["per_template"], params["seed"]):
        row = {
            "text": r["text"],
            "label": r["label"],
            "source": "template",
            "template_id": r["template_id"],
        }
        if r["split"] == "test":
            splits["test_templates"].append(row)
        else:
            splits["val" if rng.random() < params["val_frac"] else "train"].append(row)

    cl = clinc.load(raw / "clinc_data_full.json", params["clinc_per_intent"])
    for split, target in (("train", "train"), ("val", "val"), ("test", "test_clinc")):
        splits[target] += [{"text": t, "label": lab, "source": "clinc"} for t, lab in cl[split]]

    se_train: list[dict] = []
    for r in se_rows:
        if r["id"] in hand or r["id"] in leak or not r["title"]:
            continue
        lab, rule = weak_label.label(r["title"], r["tags"])
        se_train.append(
            {"text": r["title"], "label": lab, "source": "se_weak", "rule": rule, "se_id": r["id"]}
        )
    rng.shuffle(se_train)
    cap = params["se_cap_per_label"]
    kept: Counter[str] = Counter()
    for row in se_train:
        if kept[row["label"]] >= cap:
            continue
        kept[row["label"]] += 1
        splits["val" if rng.random() < params["val_frac"] else "train"].append(row)

    # Exact duplicates: test splits claim a text first, then val, then train.
    seen: set[str] = set()
    for name in ("test_se_hand", "test_templates", "test_clinc", "val", "train"):
        unique = []
        for row in splits[name]:
            key = norm(row["text"])
            if key and key not in seen:
                seen.add(key)
                unique.append(row)
        splits[name] = unique

    out.mkdir(parents=True, exist_ok=True)
    stats: dict = {"leak_ids_excluded": len(leak), "hand_checked": len(hand), "splits": {}}
    for name, items in splits.items():
        with (out / f"{name}.jsonl").open("w", encoding="utf-8") as f:
            for row in items:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        stats["splits"][name] = {
            "rows": len(items),
            "labels": dict(sorted(Counter(r["label"] for r in items).items())),
            "sources": dict(sorted(Counter(r["source"] for r in items).items())),
        }
    (out / "stats.json").write_text(json.dumps(stats, indent=2))
    return stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=ROOT / "raw")
    ap.add_argument("--out", type=Path, default=ROOT / "dataset")
    ap.add_argument("--real-eval", type=Path, help="msgs_ds.json: drop its questions from training")
    ap.add_argument("--write-leak-ids", action="store_true")
    a = ap.parse_args()
    params = yaml.safe_load((ML / "params.yaml").read_text())["intent"]["data"]
    if a.write_leak_ids:
        assert a.real_eval, "--write-leak-ids needs --real-eval"
        rows = [json.loads(x) for x in (a.raw / "se_questions.jsonl").open(encoding="utf-8")]
        ids = sorted(leak_ids_from(a.real_eval, rows))
        path = ROOT / "labels" / "eval_leak_ids.txt"
        old = path.read_text().splitlines() if path.exists() else []
        head = [x for x in old if x.startswith("#")]
        path.write_text("\n".join(head + [str(i) for i in ids]) + "\n")
    stats = build(params, a.raw, a.out, a.real_eval)
    for name, s in stats["splits"].items():
        print(f"{name:15} {s['rows']:6}  {s['sources']}")


if __name__ == "__main__":
    main()
