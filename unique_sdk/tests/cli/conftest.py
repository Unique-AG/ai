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
