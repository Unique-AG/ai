from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


@pytest.mark.ai
def test_AI_account_review_server__uses_dataset_local_paths__for_excel_and_sqlite() -> (
    None
):
    """
    Purpose: Verify the generated account-review FastMCP app owns its Excel and SQLite paths.
    Why this matters: Dataset apps must be isolated from shared helper state and from other datasets.
    Setup summary: Import the server module by file path and assert its configured paths live under fastmcp/data.
    """
    # Arrange
    server_path = (
        Path(__file__).resolve().parents[3]
        / "datasets"
        / "account_review"
        / "fastmcp"
        / "server.py"
    )
    spec = importlib.util.spec_from_file_location(
        "account_review_server_for_test", server_path
    )
    assert spec is not None
    assert spec.loader is not None

    # Act
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Assert
    assert (
        module.settings.excel_path
        == server_path.parent / "data" / "account_review_dataset.xlsx"
    )
    assert (
        module.settings.sqlite_path
        == server_path.parent / "data" / "account_review.sqlite"
    )


@pytest.mark.ai
def test_AI_normalize_due_date__coerces_workbook_values_to_iso_dates() -> None:
    """
    Purpose: Verify remediation due dates are normalized to ISO 8601 full-date text at import time.
    Why this matters: Mixed workbook strings break typed contracts, filters, and dashboard display.
    Setup summary: Import the dataset import plan and call `_normalize_due_date` on legacy and ISO inputs.
    """
    import_plan_path = (
        Path(__file__).resolve().parents[3]
        / "datasets"
        / "account_review"
        / "fastmcp"
        / "import_plan.py"
    )
    spec = importlib.util.spec_from_file_location(
        "account_review_import_plan_for_test", import_plan_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module._normalize_due_date("2026-08-03") == "2026-08-03"
    assert module._normalize_due_date(None) is None
    assert module._normalize_due_date("—") is None

    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        module._normalize_due_date("Escalated 2026-07-14")
