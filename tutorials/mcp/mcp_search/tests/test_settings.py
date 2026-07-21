"""Tests for mcp_search-specific server settings."""

import pytest
from mcp_search.settings import McpSearchServerSettings

pytestmark = pytest.mark.ai


def test_frontend_base_url_str_none_when_unset(monkeypatch):
    monkeypatch.delenv("UNIQUE_MCP_FRONTEND_BASE_URL", raising=False)
    assert McpSearchServerSettings().frontend_base_url_str() is None


def test_frontend_base_url_str_strips_trailing_slash(monkeypatch):
    monkeypatch.setenv("UNIQUE_MCP_FRONTEND_BASE_URL", "https://next.qa.unique.app/")
    assert (
        McpSearchServerSettings().frontend_base_url_str()
        == "https://next.qa.unique.app"
    )
