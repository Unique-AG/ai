"""Unit tests for `.github/scripts/resolve-dev-versions.py`.

Covers the three dep-pin branches the workflow relies on — sibling
``>=``, in-cycle ``>=`` latest dev, pyproject-stable fallback ``>=`` —
plus the per-package dev counter behaviour.

PyPI is never contacted; a fake ``fetcher`` is injected into
``highest_dev_in_cycle`` and the on-disk pyproject read is stubbed via
``REPO_ROOT``.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = (
    Path(__file__).resolve().parents[3]
    / ".github"
    / "scripts"
    / "resolve-dev-versions.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("resolve_dev_versions", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["resolve_dev_versions"] = mod
    spec.loader.exec_module(mod)
    return mod


rdv = _load_module()


def _fake_fetcher(versions_by_name: dict[str, list[str]]):
    def fetcher(name: str, _base: str) -> list[str]:
        return list(versions_by_name.get(name, []))

    return fetcher


class HighestDevInCycleTests(unittest.TestCase):
    def test_returns_none_when_empty(self) -> None:
        self.assertIsNone(
            rdv.highest_dev_in_cycle(
                "foo", "2026.18", "", fetcher=_fake_fetcher({"foo": []})
            )
        )

    def test_returns_none_when_only_other_cycles_or_stables(self) -> None:
        self.assertIsNone(
            rdv.highest_dev_in_cycle(
                "foo",
                "2026.18",
                "",
                fetcher=_fake_fetcher(
                    {"foo": ["2026.16.0.dev4", "2026.14.0", "0.3.0", "2026.18.0rc1"]}
                ),
            )
        )

    def test_picks_highest_matching_devN(self) -> None:
        self.assertEqual(
            12,
            rdv.highest_dev_in_cycle(
                "foo",
                "2026.18",
                "",
                fetcher=_fake_fetcher(
                    {
                        "foo": [
                            "2026.18.0.dev0",
                            "2026.18.0.dev5",
                            "2026.18.0.dev12",
                            "2026.18.1",  # hotfix patch, not a cycle dev
                            "2026.14.0",
                        ]
                    }
                ),
            ),
        )


class ResolveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cycle = "2026.18"
        self.publishable = [
            {"id": "toolkit", "pypi_name": "unique_toolkit", "dir": "unique_toolkit"},
            {"id": "sdk", "pypi_name": "unique_sdk", "dir": "unique_sdk"},
            {"id": "mcp", "pypi_name": "unique-mcp", "dir": "unique_mcp"},
        ]

    def _resolve(self, selected_ids, pypi, on_disk):
        # on_disk maps "<pkg dir>" -> "version" to stub the pyproject
        # fallback read without touching the filesystem.
        def fake_read(pkg_dir: Path) -> str:
            return on_disk[str(pkg_dir)]

        with patch.object(rdv, "read_pyproject_version", side_effect=fake_read):
            return rdv.resolve(
                cycle=self.cycle,
                selected_ids=selected_ids,
                publishable=self.publishable,
                pypi_base_url="",
                fetcher=_fake_fetcher(pypi),
            )

    def test_fresh_cycle_first_push_uses_pyproject_for_unchanged(self) -> None:
        new_versions, dep_pins = self._resolve(
            ["toolkit"],
            pypi={"unique_toolkit": [], "unique_sdk": [], "unique-mcp": []},
            on_disk={"unique_sdk": "0.11.6", "unique_mcp": "0.3.3"},
        )
        self.assertEqual(new_versions, {"toolkit": "2026.18.0.dev0"})
        self.assertEqual(dep_pins["unique-toolkit"], ">=2026.18.0.dev0")
        self.assertEqual(dep_pins["unique-sdk"], ">=0.11.6")
        self.assertEqual(dep_pins["unique-mcp"], ">=0.3.3")

    def test_cycle_with_existing_devs_for_unchanged(self) -> None:
        new_versions, dep_pins = self._resolve(
            ["toolkit"],
            pypi={
                "unique_toolkit": ["2026.18.0.dev3"],
                "unique_sdk": ["2026.18.0.dev2", "0.11.6"],
                "unique-mcp": [],
            },
            on_disk={"unique_mcp": "0.3.3"},
        )
        self.assertEqual(new_versions, {"toolkit": "2026.18.0.dev4"})
        self.assertEqual(dep_pins["unique-toolkit"], ">=2026.18.0.dev4")
        self.assertEqual(dep_pins["unique-sdk"], ">=2026.18.0.dev2")
        self.assertEqual(dep_pins["unique-mcp"], ">=0.3.3")

    def test_siblings_in_same_push_lockstep(self) -> None:
        new_versions, dep_pins = self._resolve(
            ["toolkit", "sdk"],
            pypi={
                "unique_toolkit": ["2026.18.0.dev5"],
                "unique_sdk": ["2026.18.0.dev9"],
                "unique-mcp": [],
            },
            on_disk={"unique_mcp": "0.3.3"},
        )
        self.assertEqual(
            new_versions, {"toolkit": "2026.18.0.dev6", "sdk": "2026.18.0.dev10"}
        )
        self.assertEqual(dep_pins["unique-toolkit"], ">=2026.18.0.dev6")
        self.assertEqual(dep_pins["unique-sdk"], ">=2026.18.0.dev10")
        self.assertEqual(dep_pins["unique-mcp"], ">=0.3.3")

    def test_pep503_normalization(self) -> None:
        _, dep_pins = self._resolve(
            ["toolkit"],
            pypi={"unique_toolkit": [], "unique_sdk": [], "unique-mcp": []},
            on_disk={"unique_sdk": "0.11.6", "unique_mcp": "0.3.3"},
        )
        self.assertIn("unique-toolkit", dep_pins)
        self.assertIn("unique-sdk", dep_pins)
        self.assertIn("unique-mcp", dep_pins)
        self.assertNotIn("unique_toolkit", dep_pins)

    def test_invalid_cycle(self) -> None:
        with self.assertRaises(SystemExit):
            rdv.resolve(
                cycle="not-a-cycle",
                selected_ids=[],
                publishable=self.publishable,
                pypi_base_url="",
                fetcher=_fake_fetcher({}),
            )

    def test_unknown_selected_id(self) -> None:
        with self.assertRaises(SystemExit):
            rdv.resolve(
                cycle=self.cycle,
                selected_ids=["mystery"],
                publishable=self.publishable,
                pypi_base_url="",
                fetcher=_fake_fetcher({}),
            )


class MainOutputFilesTests(unittest.TestCase):
    """Guards that the JSON files consumed by publish-dev.yaml end with
    a trailing newline. The workflow streams them into GITHUB_OUTPUT with
    a delimiter on its own line; without the final `\\n`, GitHub reports
    "Matching delimiter not found"."""

    def test_files_end_with_newline(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "pkgs.json"
            cfg.write_text(
                json.dumps(
                    [{"id": "toolkit", "pypi_name": "unique_toolkit", "dir": "u"}]
                )
            )
            out = Path(td) / "out"

            def fake_resolve(**_):
                return (
                    {"toolkit": "2026.18.0.dev0"},
                    {"unique-toolkit": ">=2026.18.0.dev0"},
                )

            with patch.object(rdv, "resolve", side_effect=fake_resolve):
                rc = rdv.main(
                    [
                        "--cycle",
                        "2026.18",
                        "--selected-ids",
                        json.dumps(["toolkit"]),
                        "--output-dir",
                        str(out),
                        "--package-config",
                        str(cfg),
                        "--pypi-base-url",
                        "",
                    ]
                )
            self.assertEqual(rc, 0)
            self.assertTrue((out / "new_versions.json").read_text().endswith("\n"))
            self.assertTrue((out / "dep_pins.json").read_text().endswith("\n"))


class LoadPublishableTests(unittest.TestCase):
    def test_skips_publish_skip_and_missing_pypi_name(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "pkgs.json"
            path.write_text(
                json.dumps(
                    [
                        {"id": "toolkit", "pypi_name": "unique_toolkit"},
                        {"id": "proxy", "pypi_name": "x", "publish_skip": True},
                        {"id": "no_name"},
                        {"id": "sdk", "pypi_name": "unique_sdk"},
                    ]
                )
            )
            pubs = rdv._load_publishable(path)
            self.assertEqual([p["id"] for p in pubs], ["toolkit", "sdk"])


if __name__ == "__main__":
    unittest.main()
