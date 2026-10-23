#!/usr/bin/env python3
"""Check that relative links in the repository's Markdown files resolve.

Every tracked *.md file is read; for each relative link `[text](path#anchor)` the target
file must exist, and an anchor into another Markdown file must match one of its headings
(GitHub's slug rules: lower case, punctuation dropped, spaces to hyphens). Links inside code
blocks and inline code are ignored, and so are http(s) and mailto links: this check is
offline and only guards the repo's own structure.

    python scripts/check_md_links.py        # exit code 1 and a list if anything is broken

Runs in CI (.github/workflows/ci.yml, job "docs"). Standard library only.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
FENCE = re.compile(r"^(```|~~~).*?^\1", re.S | re.M)
INLINE_CODE = re.compile(r"`[^`\n]*`")
LINK = re.compile(r"\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$", re.M)
HTML_ANCHOR = re.compile(r"<a\s+(?:name|id)=\"([^\"]+)\"")
EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.I)


def strip_code(text: str) -> str:
    return INLINE_CODE.sub("", FENCE.sub("", text))


def slug(heading: str) -> str:
    text = re.sub(r"<[^>]+>", "", heading).strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def anchors(path: Path, cache: dict[Path, set[str]]) -> set[str]:
    if path not in cache:
        text = FENCE.sub("", path.read_text(encoding="utf-8"))
        found: set[str] = set()
        seen: dict[str, int] = {}
        for heading in HEADING.findall(text):
            base = slug(heading)
            n = seen.get(base, 0)
            seen[base] = n + 1
            found.add(base if n == 0 else f"{base}-{n}")
        found.update(HTML_ANCHOR.findall(text))
        cache[path] = found
    return cache[path]


def main() -> int:
    tracked = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    cache: dict[Path, set[str]] = {}
    broken: list[str] = []
    checked = 0
    for name in tracked:
        source = ROOT / name
        for match in LINK.finditer(strip_code(source.read_text(encoding="utf-8"))):
            url = match.group(1)
            if EXTERNAL.match(url) or url == "#":
                continue
            checked += 1
            path_part, _, fragment = url.partition("#")
            target = (source.parent / unquote(path_part)).resolve() if path_part else source
            if not target.exists():
                broken.append(f"{name}: {url} (no such file)")
            elif fragment and target.suffix == ".md":
                if fragment.lower() not in anchors(target, cache):
                    broken.append(f"{name}: {url} (no such heading)")
    for line in broken:
        print(line)
    print(f"{checked} relative links in {len(tracked)} Markdown files, {len(broken)} broken")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
