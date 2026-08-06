"""Pytest configuration and shared fixtures for mcp-sqlite-excel."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_sqlite_excel.db.excel_loader import bootstrap_from_excel
from mcp_sqlite_excel.db.repository import SqliteCrudRepository
from mcp_sqlite_excel.scripts.generate_sample_excel import generate
from mcp_sqlite_excel.settings import AppSettings


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "ai: tests authored by AI agents")


@pytest.fixture
def sample_excel(tmp_path: Path) -> Path:
    """Write the bundled sample workbook into a temp directory."""
    return generate(tmp_path / "sample_portfolio.xlsx")


@pytest.fixture
def app_settings(sample_excel: Path, tmp_path: Path) -> AppSettings:
    """Settings pointing at temp Excel/SQLite paths."""
    return AppSettings(
        excel_path=sample_excel,
        sqlite_path=tmp_path / "portfolio.db",
        auth_disabled=True,
    )


@pytest.fixture
def repo(app_settings: AppSettings) -> SqliteCrudRepository:
    """Repository backed by a fresh SQLite DB seeded from the sample Excel."""
    bootstrap_from_excel(settings=app_settings, replace=True)
    return SqliteCrudRepository(settings=app_settings)
