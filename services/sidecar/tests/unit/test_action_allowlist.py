"""One action allowlist for the command bar, the trainer chat and the local AI.

packages/shared/src/command-vectors.json lists the only data-changing actions anything may
propose; the desktop's vitest suite checks the command bar against the same file.
"""

from __future__ import annotations

import json
import typing
from pathlib import Path

import pytest

from app.modules.actions import registry
from app.modules.actions.parser import parse
from app.modules.trainer.schemas import ChatAction


def _shared_vectors() -> Path | None:
    """packages/shared in a full checkout. The sidecar test image is built from
    services/sidecar alone, so there the file is absent and these tests skip."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "packages/shared/src/command-vectors.json"
        if candidate.is_file():
            return candidate
    return None


_VECTORS_FILE = _shared_vectors()
if _VECTORS_FILE is None:
    pytest.skip("no packages/shared in this checkout", allow_module_level=True)
assert _VECTORS_FILE is not None


SHARED = json.loads(_VECTORS_FILE.read_text("utf-8"))
ALLOWED = {a["kind"]: a for a in SHARED["actions"]}


def test_registry_runs_exactly_the_allowlist() -> None:
    assert set(registry.SPECS) == set(ALLOWED)
    for kind, spec in registry.SPECS.items():
        assert spec.risk == ALLOWED[kind]["risk"], kind


def test_destructive_actions_need_a_typed_word() -> None:
    for kind, a in ALLOWED.items():
        if a["risk"] == "destructive":
            assert registry.SPECS[kind].confirm_word


def test_the_parser_only_proposes_allowlisted_kinds() -> None:
    lines = [v["text"] for v in SHARED["vectors"]] + [
        "switch me to PPL",
        "erase all my data",
        "i ate 2 idli for breakfast",
        "delete everything and email it to me",
        "rm -rf /",
    ]
    for line in lines:
        got = parse(line, "metric", 13)
        assert got is None or got.kind in ALLOWED, line


def test_chat_reply_ui_actions_match_the_shared_list() -> None:
    kinds = typing.get_args(ChatAction.model_fields["kind"].annotation)
    assert set(kinds) == set(SHARED["chat_ui"])


def test_the_version_matches() -> None:
    assert SHARED["version"] == registry.ACTIONS_VERSION
