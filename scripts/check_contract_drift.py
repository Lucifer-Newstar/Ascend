"""Contract drift check: the sidecar's real OpenAPI vs docs/contracts/*.yaml.

Run from the sidecar environment (it imports the app):

    cd services/sidecar && uv run --with pyyaml python ../../scripts/check_contract_drift.py
    ... --update-counts     # also rewrite the operation counts in manifest.json

For every module row in docs/contracts/manifest.json (see docs/contracts/README.md §4):
  * each operation the code serves under the module's path prefixes must exist in the
    contract, marked implemented, with the same parameters, request body schema and
    success responses (2xx). Error responses the contract documents (404, 409...) may be
    absent from the code's OpenAPI, because FastAPI only lists declared responses, but
    any error response the code declares must be in the contract;
  * each contract operation marked implemented must exist in the code;
  * a planned operation that the code already serves fails until it is flipped;
  * every schema an implemented operation references must have the same properties and
    required fields on both sides.
Exit status 1 on any drift, with one line per problem.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "docs" / "contracts"
METHODS = ("get", "put", "post", "patch", "delete")


def load_app_openapi() -> dict[str, Any]:
    import os

    sys.path.insert(0, str(ROOT / "services" / "sidecar"))
    from app.core.config import load_settings
    from app.main import create_app

    with tempfile.TemporaryDirectory() as tmp:
        os.environ.update({"ASCEND_DATA_DIR": tmp, "ASCEND_TOKEN": "drift-check"})
        return create_app(load_settings(), migrate=False).openapi()


def ref_name(schema: dict[str, Any] | None) -> str | None:
    """Name of the component a schema points at (unwrapping arrays and nullables)."""
    if not schema:
        return None
    if "$ref" in schema:
        return str(schema["$ref"]).rsplit("/", 1)[-1]
    if schema.get("type") == "array":
        inner = ref_name(schema.get("items"))
        return f"[{inner}]" if inner else "array"
    for key in ("anyOf", "oneOf"):
        if key in schema:
            names = sorted(filter(None, (ref_name(s) for s in schema[key])))
            nullable = any(s.get("type") == "null" for s in schema[key])
            return "|".join(names) + ("|null" if nullable else "") if names else schema.get("type")
    return schema.get("type")


def signature(op: dict[str, Any]) -> dict[str, Any]:
    params = sorted(
        (p["name"], p["in"], bool(p.get("required", False)))
        for p in op.get("parameters", [])
        if p.get("in") != "header"
    )
    body = op.get("requestBody", {}).get("content", {})
    body_ref = ref_name(next(iter(body.values()), {}).get("schema")) if body else None
    responses = {}
    for code, resp in op.get("responses", {}).items():
        if code == "422":  # FastAPI adds validation errors to every operation with input
            continue
        content = resp.get("content", {})
        responses[code] = (
            ref_name(next(iter(content.values()), {}).get("schema")) if content else None
        )
    return {"params": params, "body": body_ref, "responses": responses}


def refs_used(op: dict[str, Any]) -> set[str]:
    text = json.dumps(op)
    out = set()
    for part in text.split('"#/components/schemas/')[1:]:
        out.add(part.split('"', 1)[0])
    return out


def schema_shape(spec: dict[str, Any], name: str) -> tuple[set[str], set[str]] | None:
    s = spec.get("components", {}).get("schemas", {}).get(name)
    if s is None:
        return None
    return set(s.get("properties", {})), set(s.get("required", []))


def check_module(row: dict[str, Any], code: dict[str, Any], problems: list[str]) -> dict[str, int]:
    contract = yaml.safe_load((CONTRACTS / row["contract"]).read_text(encoding="utf-8"))
    prefixes = tuple(row["path_prefixes"])
    mod = row["id"]

    def ops(spec: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
        return {
            (m.upper(), path): op
            for path, item in spec.get("paths", {}).items()
            if path.startswith(prefixes)
            for m, op in item.items()
            if m in METHODS
        }

    in_code = ops(code)
    in_contract = ops(contract)
    implemented = {k for k, op in in_contract.items() if op.get("x-status") == "implemented"}
    planned = set(in_contract) - implemented

    for key, op in sorted(in_code.items()):
        label = f"{mod}: {key[0]} {key[1]}"
        if key not in in_contract:
            problems.append(f"{label} is served by the code but missing from {row['contract']}")
            continue
        if key in planned:
            problems.append(f"{label} is implemented but still x-status: planned in the contract")
            continue
        want, got = signature(in_contract[key]), signature(op)
        for part in ("params", "body"):
            if want[part] != got[part]:
                problems.append(f"{label} {part} differ: contract {want[part]} vs code {got[part]}")
        ok_want = {c: s for c, s in want["responses"].items() if c.startswith("2")}
        ok_got = {c: s for c, s in got["responses"].items() if c.startswith("2")}
        if ok_want != ok_got:
            problems.append(
                f"{label} success responses differ: contract {ok_want} vs code {ok_got}"
            )
        for c in sorted(set(got["responses"]) - set(want["responses"]) - set(ok_got)):
            problems.append(
                f"{label} declares error response {c} that the contract does not document"
            )
        for name in sorted(refs_used(op)):
            a, b = schema_shape(contract, name), schema_shape(code, name)
            if a is None:
                problems.append(f"{label} uses schema {name}, missing from {row['contract']}")
            elif b is not None and a != b:
                extra, missing = sorted(b[0] - a[0]), sorted(a[0] - b[0])
                req = "" if a[1] == b[1] else f"; required {sorted(a[1])} vs {sorted(b[1])}"
                problems.append(
                    f"{mod}: schema {name} differs: code adds {extra}, code lacks {missing}{req}"
                )
    for key in sorted(implemented - set(in_code)):
        problems.append(
            f"{mod}: {key[0]} {key[1]} is marked implemented but the code does not serve it"
        )
    return {"implemented": len(implemented & set(in_code)), "planned": len(planned)}


def main() -> int:
    ap = argparse.ArgumentParser(description="compare the sidecar OpenAPI with docs/contracts")
    ap.add_argument(
        "--update-counts", action="store_true", help="rewrite operation counts in manifest.json"
    )
    args = ap.parse_args()

    manifest_path = CONTRACTS / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    code = load_app_openapi()
    problems: list[str] = []
    for row in manifest["modules"]:
        counts = check_module(row, code, problems)
        if counts != row.get("operations"):
            msg = f"{row['id']}: manifest counts {row.get('operations')} vs actual {counts}"
            if args.update_counts:
                row["operations"] = counts
                print(f"updated {msg}")
            else:
                problems.append(msg + " (run with --update-counts)")

    served = {p for p in code.get("paths", {})}
    covered = tuple(pre for row in manifest["modules"] for pre in row["path_prefixes"])
    for path in sorted(served):
        if not path.startswith(covered):
            problems.append(f"{path} is served by the code but no manifest module covers it")

    if args.update_counts:
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    problems = list(dict.fromkeys(problems))  # a shared schema is reported once
    for p in problems:
        print(f"DRIFT {p}")
    if not problems:
        n = sum(r["operations"]["implemented"] for r in manifest["modules"])
        print(f"ok: {n} implemented operations match {len(manifest['modules'])} contracts")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
