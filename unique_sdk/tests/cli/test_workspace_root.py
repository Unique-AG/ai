"""UN-25672: manifests anchor on the workspace root, not the shell's cwd."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from unique_sdk.cli.commands.web_search import _annotate_web_results_for_citations
from unique_sdk.cli.workspace import manifest_path, unique_dir, workspace_root

WEB_REFS = Path(".unique") / "web-refs.jsonl"


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A workspace root with a `.unique` dir and an empty subdirectory."""
    root = tmp_path / "workspace"
    (root / ".unique").mkdir(parents=True)
    (root / "work").mkdir()
    for var in ("UNIQUE_WORKSPACE_DIR", "UNIQUE_TURN_IDENTITY_FILE", "HOME"):
        monkeypatch.delenv(var, raising=False)
    return root


def _chdir(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.chdir(path)


class TestWorkspaceRoot:
    def test_env_var_wins(
        self, workspace: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("UNIQUE_WORKSPACE_DIR", str(workspace))
        _chdir(monkeypatch, workspace / "work")
        assert workspace_root() == workspace

    def test_turn_identity_file_is_used_when_env_is_absent(
        self, workspace: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        identity = workspace / ".unique" / "turn-identity.json"
        identity.write_text("{}", encoding="utf-8")
        monkeypatch.setenv("UNIQUE_TURN_IDENTITY_FILE", str(identity))
        _chdir(monkeypatch, workspace / "work")
        assert workspace_root() == workspace

    def test_home_is_used_when_it_holds_the_unique_dir(
        self, workspace: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HOME", str(workspace))
        _chdir(monkeypatch, workspace / "work")
        assert workspace_root() == workspace

    def test_a_stray_nested_unique_dir_never_wins(
        self, workspace: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A pre-fix turn leaves `work/.unique`; it must not capture later calls."""
        (workspace / "work" / ".unique").mkdir()
        monkeypatch.setenv("HOME", str(workspace))
        _chdir(monkeypatch, workspace / "work")
        assert workspace_root() == workspace

    def test_no_ancestor_walk_without_an_env_signal(
        self, workspace: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No env signal means the cwd, never a guess up the tree."""
        _chdir(monkeypatch, workspace / "work")
        assert workspace_root() == Path.cwd()


class TestTestIsolation:
    """The autouse fixture MUST keep a real developer HOME out of reach."""

    def test_home_points_at_the_scratch_dir(self, _isolated_cwd: Path) -> None:
        assert Path(os.environ["HOME"]).resolve() == _isolated_cwd.resolve()

    def test_a_home_unique_dir_captures_writes_without_the_redirect(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Why the fixture redirects HOME rather than only clearing env vars."""
        fake_home = tmp_path / "home"
        (fake_home / ".unique").mkdir(parents=True)
        cwd = tmp_path / "elsewhere"
        cwd.mkdir()
        _chdir(monkeypatch, cwd)

        monkeypatch.setenv("HOME", str(fake_home))
        assert workspace_root() == fake_home

        monkeypatch.setenv("HOME", str(cwd))
        assert workspace_root() == cwd

    def test_falls_back_to_cwd_with_no_signal(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        bare = tmp_path / "bare"
        bare.mkdir()
        for var in ("UNIQUE_WORKSPACE_DIR", "UNIQUE_TURN_IDENTITY_FILE", "HOME"):
            monkeypatch.delenv(var, raising=False)
        _chdir(monkeypatch, bare)
        assert workspace_root() == Path.cwd()

    def test_unusable_env_value_does_not_win(
        self, workspace: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("UNIQUE_WORKSPACE_DIR", str(workspace / "missing"))
        monkeypatch.setenv("HOME", str(workspace))
        _chdir(monkeypatch, workspace / "work")
        assert workspace_root() == workspace

    def test_identity_outside_a_unique_dir_is_ignored(
        self, workspace: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stray_identity = workspace / "work" / "turn-identity.json"
        stray_identity.write_text("{}", encoding="utf-8")
        monkeypatch.setenv("UNIQUE_TURN_IDENTITY_FILE", str(stray_identity))
        monkeypatch.setenv("HOME", str(workspace))
        _chdir(monkeypatch, workspace / "work")
        # The identity path is not `<root>/.unique/...`, so it is skipped and
        # the next signal (HOME) decides.
        assert workspace_root() == workspace

    def test_helpers_compose(
        self, workspace: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("UNIQUE_WORKSPACE_DIR", str(workspace))
        _chdir(monkeypatch, workspace / "work")
        assert unique_dir() == workspace / ".unique"
        assert manifest_path(WEB_REFS) == workspace / WEB_REFS


class TestManifestsFromASubdirectory:
    """The UN-25672 repro: `cd work` then register a citable source."""

    def test_web_refs_land_at_the_workspace_root(
        self, workspace: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("UNIQUE_WORKSPACE_DIR", str(workspace))
        _chdir(monkeypatch, workspace / "work")

        out = _annotate_web_results_for_citations(
            {"results": [{"url": "https://example.com/a", "title": "A"}]}
        )

        assert [r["sourceNumber"] for r in out["results"]] == [1]
        assert (workspace / WEB_REFS).is_file()
        assert not (workspace / "work" / ".unique").exists()

    def test_explicit_refs_log_path_still_wins(
        self, workspace: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("UNIQUE_WORKSPACE_DIR", str(workspace))
        _chdir(monkeypatch, workspace / "work")
        explicit = workspace / "elsewhere" / "web-refs.jsonl"

        _ = _annotate_web_results_for_citations(
            {"results": [{"url": "https://example.com/a", "title": "A"}]},
            refs_log_path=explicit,
        )

        assert explicit.is_file()
        assert not (workspace / WEB_REFS).exists()


class TestDownloadDestinationStaysCwdRelative:
    """Guard against over-correcting: output paths are not manifests."""

    def test_files_module_still_resolves_against_cwd(self) -> None:
        source = (
            Path(__file__).resolve().parents[2]
            / "unique_sdk"
            / "cli"
            / "commands"
            / "files.py"
        ).read_text(encoding="utf-8")
        assert "final_dest = Path.cwd() / filename" in source
        assert "workspace_manifest_path" not in source


def test_no_manifest_path_is_resolved_from_the_cwd() -> None:
    """Structural: every `.unique` manifest reader/writer uses the resolver."""
    cli_dir = Path(__file__).resolve().parents[2] / "unique_sdk" / "cli"
    offenders: list[str] = []
    for path in cli_dir.rglob("*.py"):
        if path.name == "workspace.py":
            continue
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if "Path.cwd()" in line and '".unique"' in line:
                offenders.append(f"{path.name}:{lineno}")
            if "Path.cwd()" in line and "_REFS_LOG" in line:
                offenders.append(f"{path.name}:{lineno}")
    assert offenders == [], f"cwd-resolved manifest paths: {offenders}"
