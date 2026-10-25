"""Repo rules a script can check (docs/RULES_AND_BASELINE.md, rules T8 to T10).

    python3 scripts/check_rules.py

Fails (exit 1) with one line per problem:
  * a phone number in a tracked text file (T8: no phone numbers in the repo);
  * something that looks like a secret: a private key block or a provider token (T8);
  * a commit-credit or co-author line naming an AI assistant, or a link to an assistant's
    site, in tracked files (T9: the team is the author);
  * the README line "Parts of this codebase were written with AI assistance." missing (T9).
Standard library only, so it runs before any install.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT = {".py", ".ts", ".tsx", ".js", ".mjs", ".md", ".yml", ".yaml", ".toml", ".json", ".css",
        ".html", ".txt", ".ini", ".cfg", ".spec"}  # fmt: skip
SKIP = ("package-lock.json", "uv.lock", "/data/", "free_exercise_db", "command-vectors.json",
        "eval/results/", "trainer_chat_messages.json")  # fmt: skip
# Indian and international mobile numbers written for people (not ids or hashes).
PHONE = re.compile(r"(?<![\w.:/#-])(?:\+\d{1,3}[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?![\w.])")
SECRET = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|\bghp_[A-Za-z0-9]{30,}|\bsk-[A-Za-z0-9]{20,}"
    r"|\bhf_[A-Za-z0-9]{30,}|\bAKIA[0-9A-Z]{16}\b|\bxox[bp]-[A-Za-z0-9-]{20,}"
)
CREDIT = re.compile(
    r"co-authored-by:.*\b(claude|chatgpt|copilot|gemini|anthropic|openai)\b"
    r"|\b(generated|written) (by|with) (claude|chatgpt|gemini)\b|\btab\.bot\b",
    re.IGNORECASE,
)
README_LINE = "Parts of this codebase were written with AI assistance."


def tracked() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    return [ROOT / p for p in out.splitlines() if Path(p).suffix in TEXT and not any(s in p for s in SKIP)]


def main() -> int:
    problems: list[str] = []
    for path in tracked():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        rel = path.relative_to(ROOT).as_posix()
        for n, line in enumerate(text.splitlines(), 1):
            if PHONE.search(line):
                problems.append(f"{rel}:{n}: looks like a phone number")
            if SECRET.search(line):
                problems.append(f"{rel}:{n}: looks like a secret")
            if CREDIT.search(line) and rel != "scripts/check_rules.py":
                problems.append(f"{rel}:{n}: names an AI assistant as author or links its site")
    if README_LINE not in (ROOT / "README.md").read_text(encoding="utf-8"):
        problems.append(f"README.md: the line {README_LINE!r} is missing")
    for p in problems:
        print(p)
    print(f"check_rules: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
