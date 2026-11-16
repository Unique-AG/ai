"""Tests for `.github/scripts/bump-constraints.py`."""

from __future__ import annotations

import importlib.util
import json
import sys
import tomllib
import unittest
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

AUDIT = json.dumps(
    {
        "vulnerabilities": [
            {
                "dependency": {"name": "opentelemetry-api", "version": "1.45.1"},
                "id": "GHSA-aaa",
                "fix_versions": ["1.9.0"],
            },
            {
                "dependency": {"name": "opentelemetry-api", "version": "1.45.1"},
                "id": "GHSA-bbb",
                "fix_versions": ["1.10.0"],
            },
            {
                "dependency": {"name": "dnspython", "version": "2.9.0"},
                "id": "GHSA-ccc",
                "fix_versions": ["2.9.2"],
            },
        ]
    }
)


class ParseTests(unittest.TestCase):
    def test_explicit_and_bare(self) -> None:
        self.assertEqual(
            bc.parse_packages("dnspython>=2.9.2\n\n# comment\nopentelemetry-api\n"),
            [("dnspython", "2.9.2"), ("opentelemetry-api", None)],
        )

    def test_underscore_request_matches_hyphenated_audit_entry(self) -> None:
        _, bumps = bc.plan(PYPROJECT, "opentelemetry_api", AUDIT)
        self.assertEqual(bumps[0]["floor"], "1.10.0")

    def test_empty_input_applies_every_audit_fix(self) -> None:
        rewritten, bumps = bc.plan(PYPROJECT, "", AUDIT)
        self.assertEqual(
            [(b["name"], b["floor"]) for b in bumps],
            [("opentelemetry-api", "1.10.0"), ("dnspython", "2.9.2")],
        )
        self.assertIn('"opentelemetry-api>=1.10.0"', rewritten)
        self.assertIn('"dnspython>=2.9.2"', rewritten)

    def test_empty_input_skips_findings_with_no_fix(self) -> None:
        data = json.loads(AUDIT)
        data["vulnerabilities"].append(
            {
                "dependency": {"name": "requests", "version": "2.32.0"},
                "id": "GHSA-x",
                "fix_versions": [],
            }
        )
        _, bumps = bc.plan(PYPROJECT, "\n", json.dumps(data))
        self.assertNotIn("requests", [b["name"] for b in bumps])

    def test_clean_audit_changes_nothing(self) -> None:
        text, bumps = bc.plan(PYPROJECT, "", '{"vulnerabilities": []}')
        self.assertEqual(bumps, [])
        self.assertEqual(text, PYPROJECT)

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

    def test_equivalent_spelling_same_floor_preserves_original_text(self) -> None:
        pyproject = '[tool.uv]\nconstraint-dependencies = [\n    "opentelemetry_api >= 1.10.0",\n]\n'
        rewritten, bumps = bc.plan(pyproject, "opentelemetry-api>=1.10", "")
        self.assertFalse(bumps[0]["changed"])
        self.assertEqual(rewritten, pyproject)

    def test_preserves_inline_comments_upper_bounds_and_markers(self) -> None:
        pyproject = (
            "[tool.uv]\nconstraint-dependencies = [\n"
            "    \"dnspython>=2.9.0,<3 ; sys_platform == 'linux'\",  # note\n]\n"
        )
        rewritten, bumps = bc.plan(pyproject, "dnspython>=2.9.2", "")
        self.assertTrue(bumps[0]["changed"])
        self.assertIn(
            "\"dnspython>=2.9.2,<3; sys_platform == 'linux'\",  # note",
            rewritten,
        )

    def test_handles_escaped_quotes_and_missing_trailing_comma(self) -> None:
        pyproject = (
            "[tool.uv]\nconstraint-dependencies = [\n"
            '    "dnspython>=2.9.0; sys_platform == \\"linux\\""\n]\n'
        )
        rewritten, bumps = bc.plan(pyproject, "dnspython>=2.9.2\nzlib>=1.0", "")
        self.assertTrue(all(b["changed"] for b in bumps))
        parsed = tomllib.loads(rewritten)["tool"]["uv"]["constraint-dependencies"]
        self.assertEqual(
            parsed,
            ['dnspython>=2.9.2; sys_platform == "linux"', "zlib>=1.0"],
        )

    def test_conditional_entries_keep_independent_floors(self) -> None:
        for entries in (
            (
                "dnspython>=3.0; sys_platform == 'linux'",
                "dnspython>=2.0; sys_platform == 'win32'",
            ),
            (
                "dnspython>=2.0; sys_platform == 'win32'",
                "dnspython>=3.0; sys_platform == 'linux'",
            ),
        ):
            pyproject = (
                "[tool.uv]\nconstraint-dependencies = [\n"
                + "".join(f'    "{e}",\n' for e in entries)
                + "]\n"
            )
            rewritten, bumps = bc.plan(pyproject, "dnspython>=2.5", "")
            self.assertTrue(bumps[0]["changed"])
            self.assertEqual(bumps[0]["floor"], "2.5")
            parsed = set(
                tomllib.loads(rewritten)["tool"]["uv"]["constraint-dependencies"]
            )
            self.assertEqual(
                parsed,
                {
                    "dnspython>=3.0; sys_platform == 'linux'",
                    "dnspython>=2.5; sys_platform == 'win32'",
                },
            )


class LockTests(unittest.TestCase):
    def test_accepts_a_locked_floor_and_records_it(self) -> None:
        bumps = [{"name": "dnspython", "floor": "2.9.2", "changed": True}]
        bc.check_locked('[[package]]\nversion = "2.9.2"\nname = "dnspython"\n', bumps)
        self.assertEqual(bumps[0]["locked"], "2.9.2")

    def test_rejects_a_lock_below_the_floor(self) -> None:
        bumps = [{"name": "dnspython", "floor": "2.9.2", "changed": True}]
        with self.assertRaises(bc.BumpError):
            bc.check_locked(
                '[[package]]\nname = "dnspython"\nversion = "2.9.0"\n', bumps
            )


if __name__ == "__main__":
    unittest.main()
