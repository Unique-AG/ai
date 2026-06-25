"""Shared pytest helpers for the Advisory MCP tests.

`FakeMCP` captures `@mcp.tool(...)` registrations so unit tests can call the real
tool callables (including the closures defined inside `register()`) without a
running FastMCP server. Unit tests monkeypatch the DB layer, so they need no
Postgres; integration tests skip themselves when the DB / server is unavailable.
"""

import os
import sys

# Put the package's source dir on sys.path so `import common`, `import portfolios`,
# etc. resolve regardless of which pyproject pytest picks as its rootdir. Mirrors
# `[tool.pytest.ini_options] pythonpath`, but also works when a higher-level config
# wins (e.g. the ai repo root pyproject — i.e. running from PyCharm / the repo root).
_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "mcp_advisory"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

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
