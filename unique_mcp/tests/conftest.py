"""Shared pytest fixtures and configuration."""

import pytest


@pytest.fixture
def sample_base_url() -> str:
    """Sample base URL for testing."""
    return "http://localhost:10116"


@pytest.fixture
def sample_mcp_server_url() -> str:
    """Sample MCP server base URL for testing."""
    return "http://localhost:8003"
