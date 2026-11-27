"""Tests for FastMCP process defaults applied on unique_mcp import."""

from __future__ import annotations

import importlib
import os
import sys

import pytest


@pytest.mark.ai
@pytest.mark.unit
def test_bootstrap__sets_check_for_updates_env__when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify FASTMCP_CHECK_FOR_UPDATES defaults to off.
    Why this matters: Update checks add noisy startup network calls in containers.
    Setup summary: Clear env, reload bootstrap, assert env + live settings.
    """
    monkeypatch.delenv("FASTMCP_CHECK_FOR_UPDATES", raising=False)
    sys.modules.pop("unique_mcp._bootstrap", None)

    import unique_mcp._bootstrap as bootstrap

    importlib.reload(bootstrap)

    assert os.environ["FASTMCP_CHECK_FOR_UPDATES"] == "off"

    import fastmcp

    assert fastmcp.settings.check_for_updates == "off"


@pytest.mark.ai
@pytest.mark.unit
def test_bootstrap__does_not_override_explicit_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify setdefault leaves an explicit FASTMCP_CHECK_FOR_UPDATES alone.
    Why this matters: Operators must be able to opt back into update checks.
    Setup summary: Set env to stable, reload bootstrap, assert value unchanged.
    """
    monkeypatch.setenv("FASTMCP_CHECK_FOR_UPDATES", "stable")
    sys.modules.pop("unique_mcp._bootstrap", None)

    import unique_mcp._bootstrap as bootstrap

    importlib.reload(bootstrap)

    assert os.environ["FASTMCP_CHECK_FOR_UPDATES"] == "stable"
