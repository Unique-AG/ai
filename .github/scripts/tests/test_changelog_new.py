"""Unit tests for `.claude/skills/changelog-fragment/scripts/changelog_new.py`."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / ".claude/skills/changelog-fragment/scripts/changelog_new.py"


class ChangelogNewTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        (self.root / ".claude/skills/changelog-fragment/scripts").mkdir(parents=True)
        (self.root / ".changelog" / "unreleased").mkdir(parents=True)
        shutil.copy(SCRIPT, self.root / ".claude/skills/changelog-fragment/scripts")
        for name in (".changie.yaml", "release-please-config.json"):
            shutil.copy(REPO / name, self.root)

    def run_script(self, *overrides: str) -> subprocess.CompletedProcess[str]:
        args = {
            "--kind": "Fixed",
            "--component": "Web Search",
            "--audience": "user",
            "--package": "unique-toolkit, unique-sdk",
            "--ticket": "UN-25380",
            "--body": "Search results keep their source links.",
        }
        args.update(dict(zip(overrides[::2], overrides[1::2])))
        return subprocess.run(
            [
                "uv",
                "run",
                "--quiet",
                str(
                    self.root
                    / ".claude/skills/changelog-fragment/scripts/changelog_new.py"
                ),
            ]
            + [x for kv in args.items() for x in kv],
            capture_output=True,
            text=True,
        )

    def test_writes_fragment(self) -> None:
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        rel = result.stdout.strip()
        self.assertRegex(
            rel, r"^\.changelog/unreleased/fixed-web-search-\d{8}-\d{6}\.yaml$"
        )
        text = (self.root / rel).read_text()
        for line in (
            "component: Web Search",
            "kind: Fixed",
            "body: Search results keep their source links.",
            "  Audience: user",
            "  Package: unique-toolkit, unique-sdk",
            "  Ticket: UN-25380",
        ):
            self.assertIn(line, text)
        self.assertTrue(re.search(r"^time: '?\d{4}-\d{2}-\d{2}T", text, re.M))

    def test_rejects_unknown_package(self) -> None:
        self.assertEqual(self.run_script("--package", "unique-nope").returncode, 1)

    def test_rejects_bad_ticket(self) -> None:
        self.assertEqual(self.run_script("--ticket", "UN-x").returncode, 1)

    def test_rejects_unknown_component(self) -> None:
        self.assertNotEqual(self.run_script("--component", "Foo").returncode, 0)


if __name__ == "__main__":
    unittest.main()
