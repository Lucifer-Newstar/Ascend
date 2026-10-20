"""Copy operations from the sidecar's real OpenAPI into a docs/contracts/*.yaml file.

The drift check (check_contract_drift.py) says *that* a contract is out of date;
this tool does the mechanical part of fixing it, so a PR that adds an endpoint
updates its contract in the same commit:

    cd services/sidecar
    uv run --with pyyaml python ../../scripts/sync_contract.py import-export /import/strong

Targets starting with "/" are paths; anything else is a component schema name,
copied on its own (use this when only a response model gained a field, so the
hand-written operation text stays as it is):

    uv run --with pyyaml python ../../scripts/sync_contract.py workouts WorkoutSummary

For each METHOD+PATH served by the code under the given paths it writes the code's
operation (parameters, request body, responses) into the contract, keeps the
contract's own `summary` when there is one, marks it `x-status: implemented`,
and copies every component schema the operation references (recursively).
Hand-written descriptions elsewhere in the file are left alone. Review the diff.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_contract_drift import CONTRACTS, METHODS, load_app_openapi  # noqa: E402


def refs(node: Any) -> set[str]:
    """Names of every #/components/schemas/X referenced anywhere inside node."""
    found: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str) and "/schemas/" in value:
                found.add(value.rsplit("/", 1)[-1])
            else:
                found |= refs(value)
    elif isinstance(node, list):
        for item in node:
            found |= refs(item)
    return found


def closure(names: set[str], schemas: dict[str, Any]) -> set[str]:
    todo, seen = list(names), set()
    while todo:
        name = todo.pop()
        if name in seen or name not in schemas:
            continue
        seen.add(name)
        todo.extend(refs(schemas[name]) - seen)
    return seen


def sync(module: str, targets: list[str], app: dict[str, Any] | None = None) -> list[str]:
    """Update docs/contracts/<module>.yaml in place; returns one line per change."""
    app = app or load_app_openapi()
    file = CONTRACTS / f"{module}.yaml"
    text = file.read_text(encoding="utf-8")
    header = "".join(line + "\n" for line in text.splitlines() if line.startswith("#"))
    contract = yaml.safe_load(text)
    changes: list[str] = []
    paths = [t for t in targets if t.startswith("/")]
    wanted: set[str] = {t for t in targets if not t.startswith("/")}
    for path in paths:
        served = app["paths"].get(path)
        if not served:
            raise SystemExit(f"the sidecar does not serve {path}")
        target = contract.setdefault("paths", {}).setdefault(path, {})
        for method in METHODS:
            if method not in served:
                continue
            op = json.loads(json.dumps(served[method]))
            old = target.get(method, {})
            if old.get("summary"):
                op["summary"] = old["summary"]
            op.pop("tags", None)
            op["x-status"] = "implemented"
            op["tags"] = old.get("tags") or [module]
            target[method] = op
            wanted |= refs(op)
            changes.append(f"{method.upper()} {path}")
    schemas = app.get("components", {}).get("schemas", {})
    for name in wanted - set(schemas):
        raise SystemExit(f"the sidecar has no schema {name}")
    dest = contract.setdefault("components", {}).setdefault("schemas", {})
    for name in sorted(closure(wanted, schemas)):
        if dest.get(name) != schemas[name]:
            dest[name] = schemas[name]
            changes.append(f"schema {name}")
    body = yaml.safe_dump(contract, sort_keys=False, allow_unicode=True, width=110)
    file.write_text(header + body, encoding="utf-8")
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("module", help="contract file name without .yaml, e.g. workouts")
    parser.add_argument(
        "targets", nargs="+", help="paths (/prs) or schema names (WorkoutSummary) to copy"
    )
    args = parser.parse_args()
    for line in sync(args.module, args.targets):
        print(f"synced {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
