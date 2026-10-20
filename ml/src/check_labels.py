"""Check that every classifier label resolves to a food row the app can log.

    python src/check_labels.py                 # labels.json vs the sidecar seed
    python src/check_labels.py --classes data/processed/classes.json

Exit code 1 lists what is wrong: a label with no food row, a portion the food row does
not use, or a dataset class missing from labels.json.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

from common import ML_DIR

SEED = ML_DIR.parent / "services" / "sidecar" / "app" / "modules" / "nutrition" / "seed.py"


def seed_foods(path: Path = SEED) -> dict[str, str]:
    """name -> portion label, read from the seed module's FOODS literal (no sidecar import)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        target = node.target if isinstance(node, ast.AnnAssign) else None
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == "FOODS" and node.value is not None:
            return {row[0]: row[1] for row in ast.literal_eval(node.value)}
    raise ValueError(f"FOODS not found in {path}")


def check(labels: dict, foods: dict[str, str], classes: list[str] | None = None) -> list[str]:
    errors: list[str] = []
    entries = labels["classes"]
    for cls, e in sorted(entries.items()):
        if e["food_name"] not in foods:
            errors.append(f"{cls}: food '{e['food_name']}' is not in the food table")
        elif foods[e["food_name"]] != e["default_portion"]:
            errors.append(
                f"{cls}: portion '{e['default_portion']}' != food table '{foods[e['food_name']]}'"
            )
        for key in ("en", "ta"):
            if not e.get(key):
                errors.append(f"{cls}: missing display name '{key}'")
    for cls in classes or []:
        if cls not in entries:
            errors.append(f"{cls}: dataset class has no entry in labels.json")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="check labels.json against the food table")
    ap.add_argument("--labels", type=Path, default=ML_DIR / "labels.json")
    ap.add_argument("--classes", type=Path, help="classes.json from the prepare stage")
    args = ap.parse_args()
    labels = json.loads(args.labels.read_text(encoding="utf-8"))
    classes = json.loads(args.classes.read_text()) if args.classes else None
    errors = check(labels, seed_foods(), classes)
    for e in errors:
        print(f"ERROR {e}")
    if not errors:
        print(f"ok: {len(labels['classes'])} labels resolve to food rows")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
