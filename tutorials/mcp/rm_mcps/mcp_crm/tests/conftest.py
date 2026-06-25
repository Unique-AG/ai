"""Shared pytest helpers for the CRM MCP tests.

`FakeMCP` captures `@mcp.tool(...)` registrations so unit tests can call the real
tool callables without a running FastMCP server. Unit tests monkeypatch the DB
layer (no Postgres needed); integration tests skip when the DB / server is down.
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
