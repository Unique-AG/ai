from __future__ import annotations

from pathlib import Path

import pytest
from mcp_dashboards.db.repository import SqliteCrudRepository
from mcp_dashboards.settings import AppSettings
from openpyxl import Workbook


def _write_workbook(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "clients"
    sheet.append(["client_name", "client_ref", "status", "portfolio_value"])
    sheet.append(["Alice", "A-1", "Open", 125.50])
    sheet.append(["Bob", "B-2", "Closed", 250.00])
    workbook.save(path)


@pytest.mark.ai
def test_AI_repository__bootstraps_and_lists_rows__with_dataset_local_sqlite(
    tmp_path: Path,
) -> None:
    """
    Purpose: Verify a repository creates and reads a dataset-local SQLite file from Excel.
    Why this matters: Each generated dataset must own its database instead of sharing framework state.
    Setup summary: Create a tiny workbook in tmp_path, ensure the repository bootstraps it, and assert rows are listed.
    """
    # Arrange
    excel_path = tmp_path / "dataset.xlsx"
    sqlite_path = tmp_path / "dataset.sqlite"
    _write_workbook(excel_path)
    repo = SqliteCrudRepository(
        settings=AppSettings(excel_path=excel_path, sqlite_path=sqlite_path)
    )

    # Act
    repo.ensure_ready()
    result = repo.list_rows("clients", limit=10)

    # Assert
    assert sqlite_path.is_file()
    assert result.total_matching == 2
    assert result.rows[0]["client_name"] == "Alice"


@pytest.mark.ai
def test_AI_repository__updates_one_row__with_valid_partial_fields(
    tmp_path: Path,
) -> None:
    """
    Purpose: Verify partial updates go through SQLite column validation and return the updated row.
    Why this matters: Typed FastMCP update tools delegate writes to the repository.
    Setup summary: Bootstrap a workbook, update one status field, and assert the returned row changed.
    """
    # Arrange
    excel_path = tmp_path / "dataset.xlsx"
    sqlite_path = tmp_path / "dataset.sqlite"
    _write_workbook(excel_path)
    repo = SqliteCrudRepository(
        settings=AppSettings(excel_path=excel_path, sqlite_path=sqlite_path)
    )
    repo.ensure_ready()

    # Act
    updated = repo.update_row("clients", 1, {"status": "Escalated"})

    # Assert
    assert updated.row["row_id"] == 1
    assert updated.row["status"] == "Escalated"
