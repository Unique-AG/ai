"""Unit tests for `.github/scripts/resolve-rc-versions.py`.

Covers the shared rc counter logic, exact dep pinning across the full
publishable set, PEP 503 normalization, and the trailing-newline guard
on output files (the workflow streams them into GITHUB_OUTPUT under a
multiline delimiter and a missing newline silently breaks parsing).

PyPI is never contacted; a fake ``fetcher`` is injected into the
resolver via the documented keyword argument.
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
    / "resolve-rc-versions.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("resolve_rc_versions", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["resolve_rc_versions"] = mod
    spec.loader.exec_module(mod)
    return mod


rrv = _load_module()


def _fake_fetcher(versions_by_name: dict[str, list[str]]):
    def fetcher(name: str, _base: str) -> list[str]:
        return list(versions_by_name.get(name, []))

    return fetcher


class HighestRcInCycleTests(unittest.TestCase):
    def test_returns_none_when_empty(self) -> None:
        self.assertIsNone(
            rrv.highest_rc_in_cycle(
                "foo", "2026.20", "", fetcher=_fake_fetcher({"foo": []})
            )
        )

    def test_ignores_other_cycles_devs_and_stables(self) -> None:
        # Only ``{cycle}.0rcN`` counts; everything else (other cycles,
        # devN, stable, hotfix patch) must be filtered out so the rc
        # counter never picks up a stale match.
        self.assertIsNone(
            rrv.highest_rc_in_cycle(
                "foo",
                "2026.20",
                "",
                fetcher=_fake_fetcher(
                    {
                        "foo": [
                            "2026.18.0rc1",
                            "2026.20.0",
                            "2026.20.1",
                            "2026.20.0.dev3",
                            "0.3.0",
                        ]
                    }
                ),
            )
        )

    def test_picks_highest_matching_rcN(self) -> None:
        self.assertEqual(
            7,
            rrv.highest_rc_in_cycle(
                "foo",
                "2026.20",
                "",
                fetcher=_fake_fetcher(
                    {
                        "foo": [
                            "2026.20.0rc1",
                            "2026.20.0rc7",
                            "2026.20.0rc3",
                            "2026.20.0",  # eventual stable, not an rc
                        ]
                    }
                ),
            ),
        )


class ResolveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cycle = "2026.20"
        self.publishable = [
            {"id": "toolkit", "pypi_name": "unique_toolkit", "dir": "unique_toolkit"},
            {"id": "sdk", "pypi_name": "unique_sdk", "dir": "unique_sdk"},
            {"id": "mcp", "pypi_name": "unique-mcp", "dir": "unique_mcp"},
        ]

    def _resolve(self, pypi):
        return rrv.resolve(
            cycle=self.cycle,
            publishable=self.publishable,
            pypi_base_url="",
            fetcher=_fake_fetcher(pypi),
        )

    def test_fresh_cycle_starts_at_rc1(self) -> None:
        new_versions, dep_pins, rc_n = self._resolve(
            pypi={"unique_toolkit": [], "unique_sdk": [], "unique-mcp": []},
        )
        self.assertEqual(rc_n, 1)
        # Every publishable package gets the same shared rc version.
        self.assertEqual(new_versions["toolkit"], "2026.20.0rc1")
        self.assertEqual(new_versions["sdk"], "2026.20.0rc1")
        self.assertEqual(new_versions["mcp"], "2026.20.0rc1")
        # And every sibling dep is floored at that rc version.
        self.assertEqual(dep_pins["unique-toolkit"], ">=2026.20.0rc1")
        self.assertEqual(dep_pins["unique-sdk"], ">=2026.20.0rc1")
        self.assertEqual(dep_pins["unique-mcp"], ">=2026.20.0rc1")

    def test_global_max_drives_shared_counter(self) -> None:
        # Different packages are at different rc counters on PyPI; the
        # next cut must use ``max + 1`` shared across the full set so
        # all siblings are floored at the same rc.
        new_versions, dep_pins, rc_n = self._resolve(
            pypi={
                "unique_toolkit": ["2026.20.0rc1", "2026.20.0rc2"],
                "unique_sdk": ["2026.20.0rc4"],
                "unique-mcp": ["2026.20.0rc1"],
            },
        )
        self.assertEqual(rc_n, 5)
        for pid in ("toolkit", "sdk", "mcp"):
            self.assertEqual(new_versions[pid], "2026.20.0rc5")
        for name in ("unique-toolkit", "unique-sdk", "unique-mcp"):
            self.assertEqual(dep_pins[name], ">=2026.20.0rc5")

    def test_publishable_without_rc_history_still_gets_shared_counter(self) -> None:
        # A brand-new package never published to PyPI must still land at
        # the shared rc counter; the resolver does not fall back to
        # per-package counters.
        new_versions, dep_pins, rc_n = self._resolve(
            pypi={
                "unique_toolkit": ["2026.20.0rc3"],
                "unique_sdk": [],  # never published
                "unique-mcp": [],
            },
        )
        self.assertEqual(rc_n, 4)
        self.assertEqual(new_versions["sdk"], "2026.20.0rc4")
        self.assertEqual(dep_pins["unique-sdk"], ">=2026.20.0rc4")

    def test_pep503_normalization(self) -> None:
        # ``unique_toolkit`` and ``unique-mcp`` must both land under
        # PEP 503 normalized keys so the rewrite step matches them
        # regardless of how the requirement is spelled.
        _, dep_pins, _ = self._resolve(
            pypi={"unique_toolkit": [], "unique_sdk": [], "unique-mcp": []},
        )
        self.assertIn("unique-toolkit", dep_pins)
        self.assertIn("unique-sdk", dep_pins)
        self.assertIn("unique-mcp", dep_pins)
        self.assertNotIn("unique_toolkit", dep_pins)

    def test_invalid_cycle(self) -> None:
        with self.assertRaises(SystemExit):
            rrv.resolve(
                cycle="not-a-cycle",
                publishable=self.publishable,
                pypi_base_url="",
                fetcher=_fake_fetcher({}),
            )


class MainOutputFilesTests(unittest.TestCase):
    """Guards that the JSON / text files consumed by publish-rc.yaml end
    with a trailing newline. The workflow streams them into GITHUB_OUTPUT
    with a delimiter on its own line; without the final `\\n`, GitHub
    reports "Matching delimiter not found"."""

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
                    {"toolkit": "2026.20.0rc1"},
                    {"unique-toolkit": ">=2026.20.0rc1"},
                    1,
                )

            with patch.object(rrv, "resolve", side_effect=fake_resolve):
                rc = rrv.main(
                    [
                        "--cycle",
                        "2026.20",
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
            self.assertTrue((out / "rc_version.txt").read_text().endswith("\n"))
            self.assertTrue((out / "rc_n.txt").read_text().endswith("\n"))
            self.assertEqual(
                (out / "rc_version.txt").read_text().strip(), "2026.20.0rc1"
            )
            self.assertEqual((out / "rc_n.txt").read_text().strip(), "1")


if __name__ == "__main__":
    unittest.main()
