"""Offline release checks: exercise the workflow shell with a fake gh, never GitHub."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from check_release import ROOT, check, python_version


class ReleaseTests(unittest.TestCase):
    def test_versions_agree(self):
        self.assertEqual(check(), [])

    def test_python_beta_spelling(self):
        self.assertEqual(python_version("1.4.0-beta.1"), "1.4.0b1")
        self.assertEqual(python_version("1.4.0"), "1.4.0")

    def test_workflow_publication_flags(self):
        workflow = (ROOT / ".github/workflows/release.yml").read_text()
        script = workflow.split('          notes="docs/releases/${TAG}.md"', 1)[1]
        script = 'notes="docs/releases/${TAG}.md"' + "\n".join(line[10:] if line.startswith("          ") else line for line in script.splitlines())
        for tag in ("v1.4.0-beta.1", "v1.4.0-rc.1", "v1.4.0-alpha.1", "v1.4.0"):
            for existing in (False, True):
                for notes in (False, True):
                    with self.subTest(tag=tag, existing=existing, notes=notes), tempfile.TemporaryDirectory() as tmp:
                        root = Path(tmp)
                        (root / "installer").mkdir()
                        (root / "installer/setup.exe").write_bytes(b"fixture")
                        (root / "installer/SHA256SUMS.txt").write_text("fixture")
                        (root / "docs/releases").mkdir(parents=True)
                        if notes:
                            (root / f"docs/releases/{tag}.md").write_text("Notes")
                        gh = root / "gh"
                        gh.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$LOG"\nif [[ "$2" == view ]]; then exit "$EXISTS"; fi\n')
                        gh.chmod(0o700)
                        log = root / "calls.txt"
                        env = {**os.environ, "PATH": str(root) + os.pathsep + os.environ["PATH"], "TAG": tag, "REPO": "test/fixture", "LOG": str(log), "EXISTS": "0" if existing else "1"}
                        subprocess.run(["bash", "-e", "-c", script], cwd=root, env=env, check=True, capture_output=True)
                        calls = log.read_text()
                        if "-" in tag:
                            self.assertIn("--prerelease --latest=false", calls)
                        else:
                            self.assertNotIn("--prerelease", calls)
                            self.assertNotIn("--latest=false", calls)
                        self.assertIn("release upload" if existing else "release create", calls)


if __name__ == "__main__":
    unittest.main()
