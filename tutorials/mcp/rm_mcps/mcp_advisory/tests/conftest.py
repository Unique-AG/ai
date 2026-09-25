"""Shared pytest helpers for the Advisory MCP tests.

`FakeMCP` captures `@mcp.tool(...)` registrations so unit tests can call the real
tool callables (including the closures defined inside `register()`) without a
running FastMCP server. Unit tests monkeypatch the DB layer, so they need no
Postgres; integration tests skip themselves when the DB / server is unavailable.

Imports (`import common`, `import portfolios`, …) resolve via the package's
`[tool.pytest.ini_options] pythonpath = ["src/mcp_advisory"]` in pyproject.toml —
so run tests with pytest (e.g. `uv run pytest`).
"""

import pytest


class FakeMCP:
    """Minimal stand-in for FastMCP that records registered tools by name."""

    def __init__(self):
        self.tools = {}

    def tool(self, name=None, **kwargs):
        def decorator(fn):
            self.tools[name or getattr(fn, "__name__", repr(fn))] = fn
            return fn

        return decorator


@pytest.fixture
def fake_mcp():
    return FakeMCP()
