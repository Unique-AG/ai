"""Unit tests for `.github/scripts/changelog_new.py`.

Covers fragment validation against ``.changie.yaml`` (kind, component,
Audience, Ticket), the changie-compatible filename, and the on-disk YAML
layout the monorepo's ``scripts/changelog-check.sh`` validates after the
fragment is copied across. The real repo ``.changie.yaml`` is used so the
tests fail if the schema drifts in a way the script can't handle.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

SCRIPT = (
    Path(__file__).resolve().parents[3] / ".github" / "scripts" / "changelog_new.py"
)
CHANGIE_CONFIG = Path(__file__).resolve().parents[3] / ".changie.yaml"


def _load_module():
    spec = importlib.util.spec_from_file_location("changelog_new", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["changelog_new"] = mod
    spec.loader.exec_module(mod)
    return mod


cn = _load_module()

NOW = dt.datetime(
    2026, 9, 8, 21, 6, 7, 123456, tzinfo=dt.timezone(dt.timedelta(hours=2))
)


class BuildFragmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = cn.load_config(CHANGIE_CONFIG)

    def _build(self, **overrides):
        kwargs = dict(
            config=self.config,
            kind="Fixed",
            component="API / SDK",
            body="The problem with X now works as intended.",
            custom={"Audience": "user"},
            now=NOW,
        )
        kwargs.update(overrides)
        return cn.build_fragment(**kwargs)

    def test_minimal_fragment(self) -> None:
        fragment = self._build()
        self.assertEqual(
            fragment,
            {
                "component": "API / SDK",
                "kind": "Fixed",
                "body": "The problem with X now works as intended.",
                "time": "2026-09-08T21:06:07.123456+02:00",
                "custom": {"Audience": "user"},
            },
        )

    def test_ticket_is_normalised(self) -> None:
        fragment = self._build(custom={"Audience": "admin", "Ticket": "UN-1 ,UN-22"})
        self.assertEqual(
            fragment["custom"], {"Audience": "admin", "Ticket": "UN-1, UN-22"}
        )

    def test_rejects_unknown_kind(self) -> None:
        with self.assertRaisesRegex(cn.FragmentError, "--kind 'Feature'"):
            self._build(kind="Feature")

    def test_rejects_unknown_component(self) -> None:
        with self.assertRaisesRegex(cn.FragmentError, "--component 'Toolkit'"):
            self._build(component="Toolkit")

    def test_requires_audience(self) -> None:
        with self.assertRaisesRegex(cn.FragmentError, "Audience is required"):
            self._build(custom={})
        with self.assertRaisesRegex(cn.FragmentError, "Audience is required"):
            self._build(custom={"Audience": "everyone"})

    def test_rejects_unknown_custom_key(self) -> None:
        with self.assertRaisesRegex(cn.FragmentError, "Unknown --custom key"):
            self._build(custom={"Audience": "user", "Scope": "x"})

    def test_rejects_malformed_ticket(self) -> None:
        with self.assertRaisesRegex(cn.FragmentError, "UN-<number>"):
            self._build(custom={"Audience": "user", "Ticket": "ABC-1"})

    def test_rejects_ticket_key_in_body(self) -> None:
        with self.assertRaisesRegex(
            cn.FragmentError, "must not contain Jira ticket keys"
        ):
            self._build(body="Fixes UN-123 crash")

    def test_rejects_empty_body(self) -> None:
        with self.assertRaisesRegex(cn.FragmentError, "--body must not be empty"):
            self._build(body="   ")


class ParseCustomTests(unittest.TestCase):
    def test_splits_on_first_equals_only(self) -> None:
        self.assertEqual(
            cn.parse_custom(["Audience=user", "Ticket=UN-1, UN-2"]),
            {"Audience": "user", "Ticket": "UN-1, UN-2"},
        )

    def test_rejects_missing_equals(self) -> None:
        with self.assertRaisesRegex(cn.FragmentError, "Key=Value"):
            cn.parse_custom(["Audience"])

    def test_rejects_duplicate_key(self) -> None:
        with self.assertRaisesRegex(cn.FragmentError, "more than once"):
            cn.parse_custom(["Audience=user", "Audience=admin"])


class FilenameTests(unittest.TestCase):
    def test_matches_changie_fragment_file_format(self) -> None:
        self.assertEqual(
            cn.fragment_filename("Fixed", "Conduct", NOW),
            "fixed-conduct-20260908-210607.yaml",
        )
        self.assertEqual(
            cn.fragment_filename("Added", "API / SDK", NOW),
            "added-api---sdk-20260908-210607.yaml",
        )


class WriteFragmentTests(unittest.TestCase):
    def test_writes_yaml_that_round_trips(self) -> None:
        config = cn.load_config(CHANGIE_CONFIG)
        fragment = cn.build_fragment(
            config=config,
            kind="Added",
            component="Web Search",
            body="Search results now include the publication date. Disabled by default; enable via `FEATURE_FLAG_X`.",
            custom={"Audience": "operator", "Ticket": "UN-42"},
            now=NOW,
        )
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(cn, "REPO_ROOT", Path(tmp)):
                target = cn.write_fragment(fragment, config=config, now=NOW)
            self.assertEqual(
                target.relative_to(tmp).as_posix(),
                ".changelog/unreleased/added-web-search-20260908-210607.yaml",
            )
            loaded = yaml.safe_load(target.read_text(encoding="utf-8"))
        self.assertEqual(loaded, fragment)
        # Keys stay in changie's order so diffs against monorepo fragments are readable.
        self.assertEqual(list(loaded), ["component", "kind", "body", "time", "custom"])

    def test_refuses_to_overwrite(self) -> None:
        config = cn.load_config(CHANGIE_CONFIG)
        fragment = cn.build_fragment(
            config=config,
            kind="Removed",
            component="MCP",
            body="Legacy endpoint removed.",
            custom={"Audience": "admin"},
            now=NOW,
        )
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(cn, "REPO_ROOT", Path(tmp)):
                cn.write_fragment(fragment, config=config, now=NOW)
                with self.assertRaisesRegex(cn.FragmentError, "already exists"):
                    cn.write_fragment(fragment, config=config, now=NOW)


class MainTests(unittest.TestCase):
    def test_dry_run_prints_fragment_and_writes_nothing(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(cn, "REPO_ROOT", Path(tmp)),
        ):
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cn.main(
                    [
                        "--kind",
                        "Changed",
                        "--component",
                        "RAG",
                        "--body",
                        "Chunking now respects headings.",
                        "--custom",
                        "Audience=user",
                        "--config",
                        str(CHANGIE_CONFIG),
                        "--dry-run",
                    ]
                )
            self.assertEqual(rc, 0)
            self.assertEqual(yaml.safe_load(buf.getvalue())["component"], "RAG")
            self.assertFalse((Path(tmp) / ".changelog").exists())

    def test_validation_error_returns_nonzero(self) -> None:
        import io
        from contextlib import redirect_stderr

        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = cn.main(
                [
                    "--kind",
                    "Fixed",
                    "--component",
                    "RAG",
                    "--body",
                    "x",
                    "--config",
                    str(CHANGIE_CONFIG),
                    "--dry-run",
                ]
            )
        self.assertEqual(rc, 1)
        self.assertIn("Audience is required", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
