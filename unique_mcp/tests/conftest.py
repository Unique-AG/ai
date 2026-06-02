"""Shared pytest fixtures and configuration."""

# avoid a Python importlib bug: unique_toolkit.chat.deprecated is a namespace
# package; if unique_toolkit.chat isn't in sys.modules when its _NamespacePath
# recalculates after a sys.path insertion, Python raises KeyError.
import pytest
import unique_toolkit.chat  # noqa: F401 - must be imported before unique_mcp to


@pytest.fixture
def sample_base_url() -> str:
    """Sample base URL for testing."""
    return "http://localhost:10116"


@pytest.fixture
def sample_mcp_server_url() -> str:
    """Sample MCP server base URL for testing."""
    return "http://localhost:8003"
