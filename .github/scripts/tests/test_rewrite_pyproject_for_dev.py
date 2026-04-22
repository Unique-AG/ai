"""Unit tests for `.github/scripts/rewrite-pyproject-for-dev.py`.

Verifies the in-place rewrite of ``project.version`` plus PEP 621
dependency arrays (including optional-dependencies groups) against the
dep-pin map produced by ``resolve-dev-versions.py``.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".github" / "scripts" / "rewrite-pyproject-for-dev.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("rewrite_pyproject_for_dev", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["rewrite_pyproject_for_dev"] = mod
    spec.loader.exec_module(mod)
    return mod


rpd = _load_module()


SAMPLE_PYPROJECT = """\
[project]
name = "unique_toolkit"
version = "1.69.6"
dependencies = [
  "unique-sdk>=0.10.85,<0.12",
  "pydantic>=2.0",
  "unique_orchestrator>=0.1.0",
]

[project.optional-dependencies]
monitoring = [
  "unique-mcp[extra]>=0.3",
  "prometheus-client>=0.17",
]
fastapi = []

[tool.some-tool]
keep_me = true
"""


class RewriteTests(unittest.TestCase):
    def _run(self, dep_pins: dict[str, str], own_version: str = "2026.18.0.dev7"):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "pyproject.toml"
            path.write_text(SAMPLE_PYPROJECT)
            rc = rpd.main(
                [
                    str(path),
                    "--own-version",
                    own_version,
                    "--dep-pins",
                    json.dumps(dep_pins),
                ]
            )
            self.assertEqual(rc, 0)
            return path.read_text()

    def test_rewrites_own_version_and_ai_deps(self) -> None:
        out = self._run(
            {
                "unique-sdk": "==2026.18.0.dev3",
                "unique-orchestrator": ">=2026.18.0.dev1",
                "unique-mcp": ">=2026.14.0",
            },
        )
        self.assertIn('version = "2026.18.0.dev7"', out)
        self.assertIn('"unique-sdk==2026.18.0.dev3"', out)
        self.assertIn('"unique_orchestrator>=2026.18.0.dev1"', out)
        self.assertIn('"unique-mcp[extra]>=2026.14.0"', out)

    def test_leaves_non_ai_deps_alone(self) -> None:
        out = self._run({"unique-sdk": "==2026.18.0.dev3"})
        self.assertIn('"pydantic>=2.0"', out)
        self.assertIn('"prometheus-client>=0.17"', out)

    def test_accepts_legacy_stable_fallback_pin(self) -> None:
        # Last-stable fallback for unchanged deps may be pre-CalVer
        # (e.g. unique-mcp 0.3.3). The rewriter must pass it through.
        out = self._run(
            {
                "unique-sdk": "==2026.18.0.dev3",
                "unique-mcp": ">=0.3.3",
                "unique-orchestrator": ">=1.22.2",
            }
        )
        self.assertIn('"unique-mcp[extra]>=0.3.3"', out)
        self.assertIn('"unique_orchestrator>=1.22.2"', out)

    def test_preserves_other_tool_tables(self) -> None:
        out = self._run({"unique-sdk": "==2026.18.0.dev3"})
        self.assertIn("[tool.some-tool]", out)
        self.assertIn("keep_me = true", out)

    def test_pep503_normalization_on_dep_names(self) -> None:
        # Requirement string uses "unique_orchestrator" (underscore), but
        # the dep-pin map keys on the normalized "unique-orchestrator".
        out = self._run(
            {
                "unique-orchestrator": "==2026.18.0.dev2",
                "unique-sdk": "==2026.18.0.dev3",
                "unique-mcp": ">=2026.14.0",
            }
        )
        self.assertIn('"unique_orchestrator==2026.18.0.dev2"', out)

    def test_rejects_unknown_dep_pin_format(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "pyproject.toml"
            path.write_text(SAMPLE_PYPROJECT)
            with self.assertRaises(SystemExit):
                rpd.main(
                    [
                        str(path),
                        "--own-version",
                        "2026.18.0.dev7",
                        "--dep-pins",
                        json.dumps({"unique-sdk": "~=2026.18.0"}),
                    ]
                )

    def test_rejects_invalid_own_version(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "pyproject.toml"
            path.write_text(SAMPLE_PYPROJECT)
            with self.assertRaises(SystemExit):
                rpd.main(
                    [
                        str(path),
                        "--own-version",
                        "banana",
                        "--dep-pins",
                        json.dumps({}),
                    ]
                )

    def test_rejects_non_dev_own_version(self) -> None:
        # The rewriter is only ever invoked for dev publishes — stable
        # CalVers are stamped by release-please, not by this script.
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "pyproject.toml"
            path.write_text(SAMPLE_PYPROJECT)
            with self.assertRaises(SystemExit):
                rpd.main(
                    [
                        str(path),
                        "--own-version",
                        "2026.18.0",  # stable, no .devN — must be rejected
                        "--dep-pins",
                        json.dumps({}),
                    ]
                )


if __name__ == "__main__":
    unittest.main()
