"""Tests for list_rows search/sort and count_by."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from mcp_sqlite_excel.db.excel_loader import bootstrap_from_excel
from mcp_sqlite_excel.db.repository import SqliteCrudRepository
from mcp_sqlite_excel.mcp_sqlite_excel import list_rows
from mcp_sqlite_excel.models import FieldMap, ListRowsResult, SortSpec, parse_sort_arg
from mcp_sqlite_excel.settings import AppSettings


@pytest.fixture
def account_review_repo(tmp_path: Path) -> SqliteCrudRepository:
    """Repository seeded from the account-review workbook."""
    excel = Path(__file__).resolve().parents[1] / "data" / "account_review_dataset.xlsx"
    if not excel.is_file():
        pytest.skip("account_review_dataset.xlsx not present")
    settings = AppSettings(
        excel_path=excel,
        sqlite_path=tmp_path / "account_review_query.db",
        auth_disabled=True,
    )
    bootstrap_from_excel(settings=settings, replace=True)
    return SqliteCrudRepository(settings=settings)


@pytest.mark.ai
def test_AI_list_rows_search_matches_client_name_or_ref(
    account_review_repo: SqliteCrudRepository,
) -> None:
    """Purpose: search substring matches client_name or client_ref.
    Why this matters: Account Review console filter box cannot run client-side JS.
    Setup summary: search for 'vol' should hit Dmitry Volkov.
    """
    listed = account_review_repo.list_rows("clients", search="vol")
    names = {row["client_name"] for row in listed.rows}
    assert "Dmitry Volkov" in names
    assert listed.search == "vol"
    assert set(listed.search_fields) == {"client_name", "client_ref"}


@pytest.mark.ai
def test_AI_list_rows_search_with_filters_and_sort(
    account_review_repo: SqliteCrudRepository,
) -> None:
    """Purpose: search, exact filters, and sort combine in one query.
    Why this matters: Status dropdown + search + Due date sort map to one MCP call.
    Setup summary: Needs Remediation + risk_level High, sorted by client_name.
    """
    listed = account_review_repo.list_rows(
        "clients",
        filters=FieldMap({"status": "Needs Remediation", "risk_level": "High"}),
        sort=[SortSpec(field="client_name", dir="asc")],
        limit=50,
    )
    assert listed.total_matching >= 1
    assert all(row["status"] == "Needs Remediation" for row in listed.rows)
    assert all(row["risk_level"] == "High" for row in listed.rows)
    names = [row["client_name"] for row in listed.rows]
    assert names == sorted(names)
    assert listed.sort[0].field == "client_name"


@pytest.mark.ai
def test_AI_list_rows_rejects_unknown_sort_field(
    account_review_repo: SqliteCrudRepository,
) -> None:
    """Purpose: sort fields must be known schema columns.
    Why this matters: prevents SQL injection via ORDER BY identifiers.
    Setup summary: unknown field raises ValueError.
    """
    with pytest.raises(ValueError, match="Unknown column"):
        account_review_repo.list_rows(
            "clients",
            sort=[SortSpec(field="not_a_column", dir="asc")],
        )


@pytest.mark.ai
def test_AI_parse_sort_arg_accepts_json_string() -> None:
    """Purpose: sort MCP args may arrive as JSON strings.
    Why this matters: Unique Chat bridges often stringify nested arrays.
    Setup summary: parse a JSON array into SortSpec list.
    """
    specs = parse_sort_arg('[{"field":"due_date","dir":"desc"}]')
    assert len(specs) == 1
    assert specs[0].field == "due_date"
    assert specs[0].dir.lower() == "desc"


@pytest.mark.ai
def test_AI_list_rows_tool_returns_structured_object_for_iframe_path(
    account_review_repo: SqliteCrudRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Purpose: list_rows MCP tool returns a typed ListRowsResult with rows.
    Why this matters: Unique iframe bindings use data-unique-source-path
    ``rows`` and need a concrete output schema (not opaque dict / JSON string).
    Setup summary: call the tool and assert ListRowsResult.rows is populated.
    """
    monkeypatch.setattr("mcp_sqlite_excel.mcp_sqlite_excel.repo", account_review_repo)
    payload = asyncio.run(list_rows(table="clients", limit=3))
    assert isinstance(payload, ListRowsResult)
    assert len(payload.rows) == 3
    assert "row_id" in payload.rows[0]


@pytest.mark.ai
def test_AI_count_by_status_for_kpi_tiles(
    account_review_repo: SqliteCrudRepository,
) -> None:
    """Purpose: count_by groups clients by status for live KPI tiles.
    Why this matters: dashboard KPIs should refresh without regenerating HTML.
    Setup summary: totals match the seed workbook (12 clients).
    """
    result = account_review_repo.count_by("clients", column="status")
    assert result.total == 12
    assert result.column == "status"
    assert result.counts.get("Escalated") == 2
    assert result.counts.get("Needs Remediation") == 6
    assert result.counts.get("Compliant") == 4
    # Canvas KPI tiles bind data-unique-source-path="rows"
    assert result.rows[0] == {
        "bucket": "__total__",
        "label": "Total clients",
        "count": 12,
    }
    by_bucket = {row["bucket"]: row["count"] for row in result.rows[1:]}
    assert by_bucket == result.counts


@pytest.mark.ai
def test_AI_account_review_identity_and_button_target_columns(
    account_review_repo: SqliteCrudRepository,
) -> None:
    """Purpose: workbook exposes identity fields, risk_level, and button_target.
    Why this matters: Account Review detail page and card CTAs need these columns.
    Setup summary: inspect schema + one client + one smart action row.
    """
    clients = account_review_repo.get_table_schema("clients")
    client_cols = clients.column_names
    for name in (
        "date_of_birth",
        "occupation",
        "residential_address",
        "email",
        "phone",
        "fatca_us_person",
        "marital_status",
        "crd_number",
        "risk_level",
    ):
        assert name in client_cols

    actions = account_review_repo.get_table_schema("smart_actions")
    assert "button_target" in actions.column_names

    nesterov = account_review_repo.list_rows(
        "clients",
        filters=FieldMap({"client_ref": "CH-priv-0187"}),
    ).rows[0]
    assert nesterov["risk_level"] == "Low"
    assert nesterov["crd_number"] == "CRD-CH-0187"
    assert nesterov["email"] == "a.nesterov@example.ch"

    action = account_review_repo.list_rows(
        "smart_actions",
        filters=FieldMap({"client_ref": "CH-priv-0187"}),
    ).rows[0]
    assert action["button_target"] == "cont_case_CH-priv-0187"
