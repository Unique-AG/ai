"""Tests for `.github/scripts/bump-constraints.py`."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".github" / "scripts" / "bump-constraints.py"


def _load():
    spec = importlib.util.spec_from_file_location("bump_constraints", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["bump_constraints"] = module
    spec.loader.exec_module(module)
    return module


bc = _load()

PYPROJECT = """\
[tool.uv]
constraint-dependencies = [
    "aiohttp>=3.14.4",
    # keep with dnspython
    "dnspython>=2.9.0",
    "urllib3>=2.8.0"
]
override-dependencies = [
    "dnspython>=1.0.0",
]
"""

AUDIT = """\
opentelemetry-api 1.45.1 has 2 known vulnerabilities:

- GHSA-aaa: one

  Fixed in: 1.9.0

- GHSA-bbb: two

  Fixed in: 1.10.0

dnspython 2.9.0 has 1 known vulnerability:

- GHSA-ccc: memory

  Fixed in: 2.9.2
"""


class ParseTests(unittest.TestCase):
    def test_explicit_and_bare(self) -> None:
        self.assertEqual(
            bc.parse_packages("dnspython>=2.9.2\n\n# comment\nopentelemetry-api\n"),
            [("dnspython", "2.9.2"), ("opentelemetry-api", None)],
        )

    def test_rejects_other_operators_and_duplicates(self) -> None:
        with self.assertRaises(bc.BumpError):
            bc.parse_packages("dnspython==2.9.2")
        with self.assertRaises(bc.BumpError):
            bc.parse_packages("dnspython>=2.9.2\ndnspython>=2.9.3")


class AuditTests(unittest.TestCase):
    def test_highest_fixed_version_wins(self) -> None:
        floor, note = bc.resolve_floor("opentelemetry-api", None, AUDIT, None)
        self.assertEqual(floor, "1.10.0")
        self.assertIn("1.10.0", note)

    def test_explicit_floor_when_audit_is_silent(self) -> None:
        floor, note = bc.resolve_floor("requests", "2.33.0", "", None)
        self.assertEqual(floor, "2.33.0")
        self.assertIn("does not list", note)

    def test_missing_audit_and_floor_errors(self) -> None:
        with self.assertRaises(bc.BumpError):
            bc.resolve_floor("requests", None, AUDIT, None)

    def test_does_not_lower_an_existing_floor(self) -> None:
        floor, note = bc.resolve_floor("dnspython", "2.0.0", AUDIT, "dnspython>=2.9.2")
        self.assertEqual(floor, "2.9.2")
        self.assertIn("kept existing floor", note)


class PatchTests(unittest.TestCase):
    def test_replaces_inserts_and_leaves_overrides(self) -> None:
        rewritten, bumps = bc.plan(PYPROJECT, "dnspython>=2.9.2\nanyio>=4.1", "")
        self.assertIn('"dnspython>=2.9.2"', rewritten)
        self.assertLess(
            rewritten.index("anyio"), rewritten.index("# keep with dnspython")
        )
        self.assertIn('"dnspython>=1.0.0"', rewritten)
        self.assertIn('"urllib3>=2.8.0"', rewritten)
        changed = {b["name"]: b["changed"] for b in bumps}
        self.assertEqual(changed, {"dnspython": True, "anyio": True})

    def test_unchanged_floor_does_not_count(self) -> None:
        _, bumps = bc.plan(PYPROJECT, "urllib3>=2.8.0", "")
        self.assertFalse(bumps[0]["changed"])

    def test_fragment_counts_changed_packages(self) -> None:
        self.assertEqual(
            bc.security_body(1), "Dependencies patch a published vulnerability."
        )
        self.assertEqual(
            bc.security_body(2), "Dependencies patch 2 published vulnerabilities."
        )


class LockTests(unittest.TestCase):
    def test_accepts_a_locked_floor_and_records_it(self) -> None:
        bumps = [{"name": "dnspython", "floor": "2.9.2", "changed": True}]
        bc.check_locked('[[package]]\nname = "dnspython"\nversion = "2.9.2"\n', bumps)
        self.assertEqual(bumps[0]["locked"], "2.9.2")

    def test_rejects_a_lock_below_the_floor(self) -> None:
        bumps = [{"name": "dnspython", "floor": "2.9.2", "changed": True}]
        with self.assertRaises(bc.BumpError):
            bc.check_locked(
                '[[package]]\nname = "dnspython"\nversion = "2.9.0"\n', bumps
            )


class FragmentTests(unittest.TestCase):
    def test_writes_a_security_fragment(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = bc.write_fragment(
                Path(directory),
                "Deep Research",
                "operator",
                2,
                datetime(2026, 11, 16, 15, 0, tzinfo=timezone.utc),
            )
            text = path.read_text()
            self.assertTrue(path.name.startswith("security-deep-research-"))
            self.assertIn("kind: Security", text)
            self.assertIn("Dependencies patch 2 published vulnerabilities.", text)
            self.assertIn("operator", text)


if __name__ == "__main__":
    unittest.main()
