"""Pytest configuration for mcp-sqlite-excel."""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "ai: tests authored by AI agents")
