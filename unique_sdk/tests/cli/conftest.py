"""Isolate the cwd, HOME and workspace env so CLI tests cannot write outside tmp."""

from __future__ import annotations

from pathlib import Path

import pytest

_WORKSPACE_ENV_VARS = ("UNIQUE_WORKSPACE_DIR", "UNIQUE_TURN_IDENTITY_FILE")


@pytest.fixture(autouse=True)
def _isolated_cwd(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Run every CLI test from a scratch directory it also calls HOME.

    HOME MUST be redirected too: ``workspace_root`` answers ``$HOME`` when
    ``$HOME/.unique`` exists, so a developer who has ever run the CLI from
    their home directory would otherwise have tests write real manifests
    there.
    """
    scratch = tmp_path_factory.mktemp("cli-cwd")
    for var in _WORKSPACE_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("HOME", str(scratch))
    monkeypatch.chdir(scratch)
    return scratch


@pytest.fixture(autouse=True)
def _allow_skill_writes(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Skip the skill write guard unless the test is marked ``skill_guard``."""
    if request.node.get_closest_marker("skill_guard") is not None:
        return
    from unique_sdk.cli.skill_guard import SkillGuard
    from unique_sdk.cli.state import ShellState

    monkeypatch.setattr(
        SkillGuard, "is_folder_write_denied", lambda *_args, **_kwargs: False
    )
    monkeypatch.setattr(
        SkillGuard, "is_path_write_denied", lambda *_args, **_kwargs: False
    )
    monkeypatch.setattr(
        ShellState, "is_skill_content_write_denied", lambda *_args, **_kwargs: False
    )
