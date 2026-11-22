"""Check active release versions. Python lock metadata uses normalized PEP 440 spelling."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def python_version(version: str) -> str:
    return re.sub(r"-(alpha|beta|rc)\.(\d+)$", lambda m: {"alpha": "a", "beta": "b", "rc": "rc"}[m[1]] + m[2], version)


def check(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    desktop = json.loads((root / "apps/desktop/package.json").read_text())
    version = desktop["version"]
    if os.environ.get("GITHUB_REF_TYPE") == "tag":
        tag = os.environ.get("GITHUB_REF_NAME")
        if tag != f"v{version}":
            errors.append(f"tag {tag!r} does not match app version v{version}")
    def same(label: str, actual: str, expected: str = version) -> None:
        if actual != expected:
            errors.append(f"{label}: {actual!r}, expected {expected!r}")
    for name in ("package.json", "packages/shared/package.json"):
        same(name, json.loads((root / name).read_text())["version"])
    same("desktop shared dependency", desktop["devDependencies"]["@ascend/shared"])
    lock = json.loads((root / "package-lock.json").read_text())
    same("npm lock root", lock["version"])
    for name in ("", "apps/desktop", "packages/shared"):
        same(f"npm lock {name}", lock["packages"][name]["version"])
    same("npm lock shared dependency", lock["packages"]["apps/desktop"]["devDependencies"]["@ascend/shared"])
    py = (root / "services/sidecar/pyproject.toml").read_text()
    py_match = re.search(r'^version = "([^"]+)"', py, re.MULTILINE)
    same("pyproject", py_match[1] if py_match else "missing")
    text = (root / "services/sidecar/app/__init__.py").read_text()
    match = re.search(r'__version__ = "([^"]+)"', text)
    same("sidecar runtime", match[1] if match else "missing")
    uv = (root / "services/sidecar/uv.lock").read_text()
    uv_match = re.search(r'name = "ascend-sidecar"\nversion = "([^"]+)"', uv)
    same("uv normalized version", uv_match[1] if uv_match else "missing", python_version(version))
    template = (root / ".github/ISSUE_TEMPLATE/bug_report.yml").read_text()
    if f"placeholder: {version}" not in template:
        errors.append("bug template version placeholder is stale")
    if not (root / f"docs/releases/v{version}.md").is_file():
        errors.append("release notes missing")
    if f"## [{version}] - " not in (root / "CHANGELOG.md").read_text():
        errors.append("changelog release section missing")
    return errors


if __name__ == "__main__":
    problems = check()
    print("\n".join(problems) if problems else "Release versions and notes agree.")
    raise SystemExit(bool(problems))
