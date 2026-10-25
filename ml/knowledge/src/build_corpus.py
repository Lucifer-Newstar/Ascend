"""Build the knowledge base the trainer cites: chunked, attributed passages.

Sources (all licences in ../SOURCES.md and ../sources.yaml):
  free_exercise_db   one passage per exercise: level, equipment, muscles, the steps
  pag_2018           Physical Activity Guidelines for Americans 2nd ed. (public domain),
                     text from the PDF, chunked to ~110-170 words, reference lists dropped
  usda_fdc_sr        per-100 g energy and macros for ~60 foods common in Indian kitchens
  ascend_food_table  the app's own household-portion values for Indian dishes
  who_pa_2020, ascend_notes  hand-written notes in our own words (notes/*.md)

Output: build/knowledge.jsonl.gz (one passage per line: id, source, title, text, ref) and
build/knowledge-sources.json. Deterministic for the same inputs. Retrieval itself (BM25)
lives in the sidecar: services/sidecar/app/modules/ml/knowledge.py.

    python knowledge/src/build_corpus.py            # needs knowledge/raw/ (fetch_sources.py)
"""

from __future__ import annotations

import ast
import csv
import gzip
import io
import json
import re
import subprocess
import zipfile
from pathlib import Path
from typing import Any

import yaml

KB = Path(__file__).resolve().parents[1]
REPO = KB.parents[1]
RAW = KB / "raw"
BUILD = KB / "build"
FEDB = REPO / "services/sidecar/app/modules/workouts/library_data/free_exercise_db.json"
SEEDS = [
    REPO / "services/sidecar/app/modules/nutrition/seed.py",
    REPO / "services/sidecar/app/modules/nutrition/seed_v12.py",
]
SR_DIR = "FoodData_Central_sr_legacy_food_csv_2018-04/"
NUTRIENTS = {
    "1008": "kcal",
    "1003": "protein_g",
    "1005": "carbs_g",
    "1004": "fat_g",
    "1079": "fibre_g",
}

Passage = dict[str, Any]


def _words(text: str) -> int:
    return len(text.split())


def exercise_passages() -> list[Passage]:
    data = json.loads(FEDB.read_text(encoding="utf-8"))
    out = []
    for e in data["exercises"]:
        steps = " ".join(e.get("instructions") or [])
        if not steps:
            continue
        muscles = ", ".join(e.get("primary") or []) or "not listed"
        extra = ", ".join(e.get("secondary") or [])
        head = (
            f"How to do {e['name']} ({e.get('level') or 'any'} level, "
            f"equipment: {e.get('equipment') or 'none'}). Main muscles: {muscles}."
            + (f" Also works: {extra}." if extra else "")
        )
        out.append(
            {
                "id": f"fedb:{e['id']}",
                "source": "free_exercise_db",
                "title": f"How to do {e['name']}",
                "text": f"{head} Steps: {steps}",
                "ref": e["id"],
            }
        )
    return out


_FOOTER = re.compile(r"^(Chapter \d+\..*|Physical Activity Guidelines for Americans.*|\d{1,3})$")
_CITATION = re.compile(r"(doi|https?://|\bet al\.|\bJ\b|\d{4};\s*\d+)", re.I)


def _split_long(paragraph: str, target: int) -> list[str]:
    """A long paragraph (the glossary, long lists) -> sentence groups of ~target words."""
    if _words(paragraph) <= target + 60:
        return [paragraph]
    out: list[str] = []
    buf = ""
    for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
        if buf and _words(buf) + _words(sentence) > target:
            out.append(buf)
            buf = sentence
        else:
            buf = f"{buf} {sentence}".strip()
    return out + ([buf] if buf else [])


def pdf_text(pdf: Path) -> list[str]:
    """Pages of plain text (pdftotext, reading order)."""
    out = subprocess.run(
        ["pdftotext", str(pdf), "-"], capture_output=True, text=True, check=True, timeout=120
    )
    return out.stdout.split("\f")


def pag_passages(pages: list[str], target: int = 140) -> list[Passage]:
    out: list[Passage] = []
    chapter = "Physical Activity Guidelines for Americans"
    for no, page in enumerate(pages, start=1):
        lines = [x.strip() for x in page.splitlines()]
        for x in lines:
            if x.startswith("Chapter ") and "." in x[:12]:
                chapter = x.split(".", 1)[1].strip() or chapter
        body = [x for x in lines if not _FOOTER.match(x)]
        text = re.sub(r"-\n(?=[a-z])", "", "\n".join(body))
        paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text)]
        paras = [p for p in paras if _words(p) >= 12]
        paras = [piece for p in paras for piece in _split_long(p, target)]
        if not paras:
            continue
        cites = sum(bool(_CITATION.search(p)) for p in paras)
        if no < 7 or cites > len(paras) / 2 or "References" in lines[:3]:
            continue  # front matter and reference lists
        buf: list[str] = []
        for p in paras + [""]:
            if p and (_words(" ".join(buf)) + _words(p) <= target + 30 or not buf):
                buf.append(p)
                if _words(" ".join(buf)) < target:
                    continue
            if buf:
                chunk = " ".join(buf)
                if _words(chunk) >= 25:
                    out.append(
                        {
                            "id": f"pag:{no}:{len(out)}",
                            "source": "pag_2018",
                            "title": f"PAG 2018, {chapter}",
                            "text": chunk,
                            "ref": f"PDF page {no}",
                        }
                    )
            buf = [p] if p else []
    return out


def usda_passages(zip_path: Path) -> list[Passage]:
    wanted: dict[str, str] = yaml.safe_load((KB / "usda_foods.yaml").read_text())["foods"]
    z = zipfile.ZipFile(zip_path)
    foods = csv.DictReader(io.TextIOWrapper(z.open(SR_DIR + "food.csv"), encoding="utf-8"))
    ids = {r["fdc_id"]: r["description"] for r in foods if r["description"] in wanted}
    missing = set(wanted) - set(ids.values())
    if missing:
        raise SystemExit(f"not in SR Legacy: {sorted(missing)}")
    values: dict[str, dict[str, float]] = {i: {} for i in ids}
    rows = csv.DictReader(io.TextIOWrapper(z.open(SR_DIR + "food_nutrient.csv"), encoding="utf-8"))
    for r in rows:
        if r["fdc_id"] in ids and r["nutrient_id"] in NUTRIENTS:
            values[r["fdc_id"]][NUTRIENTS[r["nutrient_id"]]] = float(r["amount"])
    out = []
    for fdc_id, d in sorted(ids.items(), key=lambda kv: wanted[kv[1]]):
        v = values[fdc_id]
        name = wanted[d]
        parts = [
            f"{v['kcal']:.0f} kcal" if "kcal" in v else None,
            f"{v['protein_g']:.1f} g protein" if "protein_g" in v else None,
            f"{v['carbs_g']:.1f} g carbohydrate" if "carbs_g" in v else None,
            f"{v['fat_g']:.1f} g fat" if "fat_g" in v else None,
            f"{v['fibre_g']:.1f} g fibre" if "fibre_g" in v else None,
        ]
        facts = ", ".join(p for p in parts if p)
        text = (
            f"{name.capitalize()}: per 100 g, {facts} (USDA FoodData Central, SR Legacy "
            f'"{d}", FDC ID {fdc_id}). Values are for this food as described; home '
            f"recipes and portions vary."
        )
        out.append(
            {
                "id": f"usda:{fdc_id}",
                "source": "usda_fdc_sr",
                "title": f"Nutrition of {name}",
                "text": text,
                "ref": f"FDC {fdc_id}",
            }
        )
    return out


def _seed_rows(path: Path) -> list[tuple]:
    """FOODS / FOODS_V12 tuples, read with ast (the sidecar is not imported)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id.startswith("FOODS") and node.value is not None:
                return list(ast.literal_eval(node.value))
    return []


def food_table_passages() -> list[Passage]:
    out = []
    for path in SEEDS:
        for name, label, grams, kcal, p, c, f in _seed_rows(path):
            text = (
                f"{name}, {label} (about {grams:g} g): roughly {kcal:g} kcal, {p:g} g "
                f"protein, {c:g} g carbohydrate, {f:g} g fat. ASCEND food table, "
                f"approximate home-style values; recipes and oil vary."
            )
            out.append(
                {
                    "id": f"food:{name.lower()}",
                    "source": "ascend_food_table",
                    "title": f"{name} ({label})",
                    "text": text,
                    "ref": name,
                }
            )
    return out


def note_passages() -> list[Passage]:
    out = []
    for md in sorted((KB / "notes").glob("*.md")):
        raw = md.read_text(encoding="utf-8")
        _, front, body = raw.split("---", 2)
        meta = yaml.safe_load(front)
        for sec in re.split(r"^## ", body, flags=re.M)[1:]:
            title, _, text = sec.partition("\n")
            slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
            out.append(
                {
                    "id": f"note:{md.stem}:{slug}",
                    "source": meta["source"],
                    "title": title.strip(),
                    "text": " ".join(text.split()),
                    "ref": md.stem,
                }
            )
    return out


def build(raw: Path = RAW, out_dir: Path = BUILD) -> dict[str, Any]:
    sources = yaml.safe_load((KB / "sources.yaml").read_text())["sources"]
    passages = (
        note_passages()
        + exercise_passages()
        + pag_passages(pdf_text(raw / "pag2.pdf"))
        + usda_passages(raw / "sr_legacy.zip")
        + food_table_passages()
    )
    seen: set[str] = set()
    for p in passages:
        if p["source"] not in sources:
            raise SystemExit(f"{p['id']}: source {p['source']} is not in sources.yaml")
        if p["id"] in seen:
            raise SystemExit(f"duplicate passage id {p['id']}")
        seen.add(p["id"])
    out_dir.mkdir(parents=True, exist_ok=True)
    blob = "".join(json.dumps(p, ensure_ascii=False) + "\n" for p in passages)
    with gzip.GzipFile(out_dir / "knowledge.jsonl.gz", "wb", mtime=0) as f:
        f.write(blob.encode("utf-8"))
    (out_dir / "knowledge-sources.json").write_text(json.dumps(sources, indent=2) + "\n")
    counts: dict[str, int] = {}
    for p in passages:
        counts[p["source"]] = counts.get(p["source"], 0) + 1
    stats = {
        "passages": len(passages),
        "by_source": counts,
        "words": sum(_words(p["text"]) for p in passages),
    }
    (out_dir / "stats.json").write_text(json.dumps(stats, indent=2))
    return stats


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
