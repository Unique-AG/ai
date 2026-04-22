"""Unit tests for `.github/scripts/resolve-dev-versions.py`.

These tests cover the three version-resolution branches the workflow
relies on:

  * packages with *no* versions yet (fresh PyPI name)
  * packages with stable versions but *no* dev in the current cycle
  * packages with a dev sequence already live in the current cycle

and verify cross-dep pin selection (sibling ``==``, latest-dev ``>=``,
last-stable ``>=`` fallback).

We invoke the resolver via its public functions so PyPI is never
actually contacted — a fake ``fetcher`` is injected instead.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".github" / "scripts" / "resolve-dev-versions.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("resolve_dev_versions", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["resolve_dev_versions"] = mod
    spec.loader.exec_module(mod)
    return mod


rdv = _load_module()


def _fake_pypi(versions_by_name: dict[str, list[str]]):
    def fetcher(name: str, _base_url: str) -> list[str]:
        return list(versions_by_name.get(name, []))

    return fetcher


def _pub(id_: str, pypi_name: str) -> "rdv.Publishable":
    return rdv.Publishable(id=id_, pypi_name=pypi_name)


class ClassifyVersionsTests(unittest.TestCase):
    def test_empty(self) -> None:
        state = rdv.classify_versions([], "2026.18")
        self.assertIsNone(state.max_dev_in_cycle)
        self.assertIsNone(state.last_stable)

    def test_only_stable(self) -> None:
        state = rdv.classify_versions(
            ["2026.10.0", "2026.14.0", "2026.14.1"], "2026.18"
        )
        self.assertIsNone(state.max_dev_in_cycle)
        self.assertEqual(state.last_stable, "2026.14.1")

    def test_ignores_devs_from_other_cycles(self) -> None:
        state = rdv.classify_versions(
            ["2026.16.0.dev4", "2026.16.0.dev5", "2026.14.0"], "2026.18"
        )
        self.assertIsNone(state.max_dev_in_cycle)
        self.assertEqual(state.last_stable, "2026.14.0")

    def test_picks_highest_dev_in_cycle(self) -> None:
        state = rdv.classify_versions(
            ["2026.18.0.dev0", "2026.18.0.dev12", "2026.18.0.dev5", "2026.14.0"],
            "2026.18",
        )
        self.assertEqual(state.max_dev_in_cycle, 12)
        self.assertEqual(state.last_stable, "2026.14.0")

    def test_ignores_non_devN_prereleases(self) -> None:
        state = rdv.classify_versions(
            ["2026.18.0rc1", "2026.18.0a2", "2026.14.0"], "2026.18"
        )
        self.assertIsNone(state.max_dev_in_cycle)
        self.assertEqual(state.last_stable, "2026.14.0")

    def test_ignores_hotfix_patches(self) -> None:
        # 2026.18.1 is a hotfix, not a fresh cycle. The resolver only
        # treats `YYYY.WW.0.devN` as a cycle-dev pre-release — which is
        # what release-please will actually ship.
        state = rdv.classify_versions(
            ["2026.18.0", "2026.18.1", "2026.18.2"], "2026.18"
        )
        self.assertIsNone(state.max_dev_in_cycle)
        self.assertEqual(state.last_stable, "2026.18.2")


class ResolveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cycle = "2026.18"
        self.publishable = [
            _pub("toolkit", "unique_toolkit"),
            _pub("sdk", "unique_sdk"),
            _pub("orchestrator", "unique_orchestrator"),
            _pub("mcp", "unique-mcp"),
        ]

    def _resolve(self, selected_ids: list[str], pypi: dict[str, list[str]]):
        return rdv.resolve(
            cycle=self.cycle,
            selected_ids=selected_ids,
            publishable=self.publishable,
            pypi_base_url="https://pypi.example",
            fetcher=_fake_pypi(pypi),
        )

    def test_fresh_cycle_first_push_single_package(self) -> None:
        new_versions, dep_pins = self._resolve(
            ["toolkit"],
            {
                "unique_toolkit": ["1.69.0", "2026.14.0"],
                "unique_sdk": ["0.10.85", "2026.14.0"],
                "unique_orchestrator": ["2026.14.0"],
                "unique-mcp": ["0.3.0"],
            },
        )
        self.assertEqual(new_versions, {"toolkit": "2026.18.0.dev0"})
        # Selected package pins to ==dev0.
        self.assertEqual(dep_pins["unique-toolkit"], "==2026.18.0.dev0")
        # Non-selected deps fall back to last stable.
        self.assertEqual(dep_pins["unique-sdk"], ">=2026.14.0")
        self.assertEqual(dep_pins["unique-orchestrator"], ">=2026.14.0")
        self.assertEqual(dep_pins["unique-mcp"], ">=0.3.0")

    def test_cycle_with_existing_devs_for_unchanged_deps(self) -> None:
        new_versions, dep_pins = self._resolve(
            ["toolkit"],
            {
                "unique_toolkit": ["2026.14.0", "2026.18.0.dev3"],
                # sdk already has dev2 live in this cycle.
                "unique_sdk": ["0.10.85", "2026.18.0.dev2"],
                # orchestrator only has a stable — last stable wins.
                "unique_orchestrator": ["2026.14.0"],
                "unique-mcp": [],
            },
        )
        self.assertEqual(new_versions, {"toolkit": "2026.18.0.dev4"})
        self.assertEqual(dep_pins["unique-toolkit"], "==2026.18.0.dev4")
        self.assertEqual(dep_pins["unique-sdk"], ">=2026.18.0.dev2")
        self.assertEqual(dep_pins["unique-orchestrator"], ">=2026.14.0")
        # Brand-new package with no stable and no dev: ">=0".
        self.assertEqual(dep_pins["unique-mcp"], ">=0")

    def test_siblings_in_same_push_lockstep(self) -> None:
        new_versions, dep_pins = self._resolve(
            ["toolkit", "sdk"],
            {
                "unique_toolkit": ["2026.18.0.dev5", "2026.14.0"],
                "unique_sdk": ["2026.18.0.dev9", "2026.14.0"],
                "unique_orchestrator": ["2026.14.0"],
                "unique-mcp": ["0.3.0"],
            },
        )
        self.assertEqual(
            new_versions,
            {"toolkit": "2026.18.0.dev6", "sdk": "2026.18.0.dev10"},
        )
        # Both siblings pin each other with ==<sibling's new version>.
        self.assertEqual(dep_pins["unique-toolkit"], "==2026.18.0.dev6")
        self.assertEqual(dep_pins["unique-sdk"], "==2026.18.0.dev10")
        self.assertEqual(dep_pins["unique-orchestrator"], ">=2026.14.0")
        self.assertEqual(dep_pins["unique-mcp"], ">=0.3.0")

    def test_pep503_normalization(self) -> None:
        _, dep_pins = self._resolve(
            ["toolkit"],
            {
                n: ["2026.14.0"]
                for n in (
                    "unique_toolkit",
                    "unique_sdk",
                    "unique_orchestrator",
                    "unique-mcp",
                )
            },
        )
        # All keys are PEP 503 normalized — underscores -> hyphens.
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
                fetcher=_fake_pypi({}),
            )

    def test_unknown_selected_id(self) -> None:
        with self.assertRaises(SystemExit):
            rdv.resolve(
                cycle=self.cycle,
                selected_ids=["toolkit", "mystery"],
                publishable=self.publishable,
                pypi_base_url="",
                fetcher=_fake_pypi({}),
            )


class PackageConfigLoadTests(unittest.TestCase):
    def test_skips_publish_skip_and_missing_pypi_name(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "pkgs.json"
            path.write_text(
                json.dumps(
                    [
                        {"id": "toolkit", "pypi_name": "unique_toolkit"},
                        {
                            "id": "proxy",
                            "pypi_name": "unique_search_proxy",
                            "publish_skip": True,
                        },
                        {"id": "no_name"},  # omitted silently
                        {"id": "sdk", "pypi_name": "unique_sdk"},
                    ]
                )
            )
            pubs = rdv.load_publishable(path)
            self.assertEqual([p.id for p in pubs], ["toolkit", "sdk"])


if __name__ == "__main__":
    unittest.main()
