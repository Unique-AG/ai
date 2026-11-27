"""Unit tests for the Agentic Table lifecycle wrappers (create/import/export/sheet metadata).

These test the request shape (method, url, params) of the new public-API wrappers by
patching the static request layer; no network involved.
"""

from unittest.mock import AsyncMock, patch

import pytest

from unique_sdk._error import InvalidRequestError
from unique_sdk.api_resources._agentic_table import (
    AgenticTable,
    MagicTableArtifactType,
    RowVerificationStatus,
)

pytestmark = pytest.mark.ai

USER_ID = "user_1"
COMPANY_ID = "company_1"
TABLE_ID = "sheet_123"


@pytest.fixture
def mock_request():
    with patch.object(
        AgenticTable, "_static_request_async", new_callable=AsyncMock
    ) as mock:
        yield mock


async def test_create_sheet_posts_to_magic_table_root(mock_request):
    mock_request.return_value = {
        "sheetId": TABLE_ID,
        "dueDiligenceId": "dd_1",
        "name": "My sheet",
        "state": "IDLE",
        "createdBy": USER_ID,
        "companyId": COMPANY_ID,
        "createdAt": "2026-01-01T00:00:00.000Z",
    }

    result = await AgenticTable.create_sheet(
        USER_ID,
        COMPANY_ID,
        assistantId="assistant_1",
        name="My sheet",
    )

    mock_request.assert_awaited_once_with(
        "post",
        "/magic-table",
        USER_ID,
        COMPANY_ID,
        {"assistantId": "assistant_1", "name": "My sheet"},
    )
    assert result["sheetId"] == TABLE_ID
    assert result["dueDiligenceId"] == "dd_1"


async def test_add_metadata_posts_body_without_table_id(mock_request):
    mock_request.return_value = {"status": True}

    result = await AgenticTable.add_metadata(
        USER_ID,
        COMPANY_ID,
        tableId=TABLE_ID,
        questionFileIds=["cont_q1"],
        sourceFileIds=["cont_s1"],
        context="RFP context",
    )

    mock_request.assert_awaited_once_with(
        "post",
        f"/magic-table/{TABLE_ID}/metadata",
        USER_ID,
        COMPANY_ID,
        {
            "questionFileIds": ["cont_q1"],
            "sourceFileIds": ["cont_s1"],
            "context": "RFP context",
        },
    )
    assert result["status"] is True


async def test_generate_artifact_posts_artifact_types(mock_request):
    mock_request.return_value = {"status": True}

    await AgenticTable.generate_artifact(
        USER_ID,
        COMPANY_ID,
        tableId=TABLE_ID,
        artifactTypes=[MagicTableArtifactType.FULL_REPORT],
    )

    mock_request.assert_awaited_once_with(
        "post",
        f"/magic-table/{TABLE_ID}/generate-artifact",
        USER_ID,
        COMPANY_ID,
        {"artifactTypes": [MagicTableArtifactType.FULL_REPORT]},
    )


async def test_list_artifacts_gets_artifacts_route(mock_request):
    # The route responds with a `{object: "list", data: [...]}` envelope.
    mock_request.return_value = {
        "object": "list",
        "data": [
            {
                "id": "artifact_1",
                "artifactType": "FULL_REPORT",
                "artifactState": "DONE",
                "contentId": "cont_export",
                "createdAt": "2026-01-01T00:00:00.000Z",
                "updatedAt": "2026-01-01T00:01:00.000Z",
            }
        ],
    }

    result = await AgenticTable.list_artifacts(USER_ID, COMPANY_ID, tableId=TABLE_ID)

    mock_request.assert_awaited_once_with(
        "get",
        f"/magic-table/{TABLE_ID}/artifacts",
        USER_ID,
        COMPANY_ID,
    )
    assert len(result) == 1
    assert result[0]["contentId"] == "cont_export"


async def test_create_sheet_metadata_posts_entries(mock_request):
    mock_request.return_value = {"status": True}

    await AgenticTable.create_sheet_metadata(
        USER_ID,
        COMPANY_ID,
        tableId=TABLE_ID,
        entries=[{"key": "client", "value": "UBP", "exactFilter": True}],
    )

    mock_request.assert_awaited_once_with(
        "post",
        f"/magic-table/{TABLE_ID}/sheet/metadata",
        USER_ID,
        COMPANY_ID,
        {"entries": [{"key": "client", "value": "UBP", "exactFilter": True}]},
    )


async def test_create_row_metadata_posts_entries_to_row_url(mock_request):
    mock_request.return_value = {"status": True}

    await AgenticTable.create_row_metadata(
        USER_ID,
        COMPANY_ID,
        tableId=TABLE_ID,
        rowId="row_1",
        entries=[{"key": "client", "value": "UBP", "exactFilter": True}],
    )

    # Both tableId and rowId address the resource and must not survive into the body.
    mock_request.assert_awaited_once_with(
        "post",
        f"/magic-table/{TABLE_ID}/row/row_1/metadata",
        USER_ID,
        COMPANY_ID,
        {"entries": [{"key": "client", "value": "UBP", "exactFilter": True}]},
    )


async def test_update_row_metadata_posts_entry_to_metadata_url(mock_request):
    mock_request.return_value = {"status": True}

    await AgenticTable.update_row_metadata(
        USER_ID,
        COMPANY_ID,
        tableId=TABLE_ID,
        metadataId="meta_1",
        key="client",
        value="UBP",
        exactFilter=True,
    )

    mock_request.assert_awaited_once_with(
        "post",
        f"/magic-table/{TABLE_ID}/row/metadata/meta_1",
        USER_ID,
        COMPANY_ID,
        {"key": "client", "value": "UBP", "exactFilter": True},
    )


async def test_delete_row_deletes_one_row_by_id(mock_request):
    """Purpose: delete_row issues DELETE against the by-id route.
    Why this matters: A wrong path would hit row-order or metadata delete.
    Setup summary: The request layer is mocked and the URL is asserted.
    """
    mock_request.return_value = {
        "object": "magic-table-action",
        "id": TABLE_ID,
        "status": True,
        "message": "Agentic Table Row deleted successfully",
    }

    result = await AgenticTable.delete_row(
        USER_ID,
        COMPANY_ID,
        tableId=TABLE_ID,
        rowId="mt_row_abc",
    )

    assert result["object"] == "magic-table-action"
    assert result["id"] == TABLE_ID
    assert result["status"] is True
    mock_request.assert_awaited_once_with(
        "delete",
        f"/magic-table/{TABLE_ID}/row/mt_row_abc",
        USER_ID,
        COMPANY_ID,
    )


async def test_delete_row_encodes_a_slash_into_one_segment(mock_request):
    """Purpose: A slash in the row id stays inside the row-id path segment.
    Why this matters: An unencoded slash selects the row-metadata delete route.
    Setup summary: rowId is metadata/meta_1; the URL contains %2F and no extra segment.
    """
    mock_request.return_value = {"status": True}

    await AgenticTable.delete_row(
        USER_ID,
        COMPANY_ID,
        tableId=TABLE_ID,
        rowId="metadata/meta_1",
    )

    url = mock_request.await_args.args[1]
    assert url == f"/magic-table/{TABLE_ID}/row/metadata%2Fmeta_1"
    assert "/row/metadata/" not in url


@pytest.mark.parametrize("row_id", [".", ".."])
async def test_delete_row_rejects_dot_segments(mock_request, row_id: str):
    """Purpose: Dot path segments are refused before a request is sent.
    Why this matters: The HTTP client resolves them onto a different route.
    Setup summary: rowId is '.' or '..'; the request layer is not called.
    """
    with pytest.raises(InvalidRequestError):
        await AgenticTable.delete_row(
            USER_ID,
            COMPANY_ID,
            tableId=TABLE_ID,
            rowId=row_id,
        )

    mock_request.assert_not_awaited()


async def test_delete_row_metadata_deletes_by_id(mock_request):
    mock_request.return_value = {"status": True}

    await AgenticTable.delete_row_metadata(
        USER_ID,
        COMPANY_ID,
        tableId=TABLE_ID,
        metadataId="meta_1",
    )

    mock_request.assert_awaited_once_with(
        "delete",
        f"/magic-table/{TABLE_ID}/row/metadata/meta_1",
        USER_ID,
        COMPANY_ID,
    )


async def test_set_multiple_cells_sends_overwrite_library_rows_when_set(
    mock_request,
):
    mock_request.return_value = {"status": True}

    await AgenticTable.set_multiple_cells(
        USER_ID,
        COMPANY_ID,
        tableId=TABLE_ID,
        cells=[{"rowOrder": 1, "columnOrder": 2, "text": "answer"}],
        overwriteLibraryRows=True,
    )

    mock_request.assert_awaited_once_with(
        "post",
        f"/magic-table/{TABLE_ID}/cells/bulk-upsert",
        USER_ID,
        COMPANY_ID,
        params={
            "cells": [{"rowOrder": 1, "columnOrder": 2, "data": "answer"}],
            "overwriteLibraryRows": True,
        },
    )


async def test_set_multiple_cells_omits_overwrite_library_rows_by_default(
    mock_request,
):
    mock_request.return_value = {"status": True}

    await AgenticTable.set_multiple_cells(
        USER_ID,
        COMPANY_ID,
        tableId=TABLE_ID,
        cells=[{"rowOrder": 1, "columnOrder": 2, "text": "answer"}],
    )

    assert "overwriteLibraryRows" not in mock_request.await_args.kwargs["params"]


async def test_delete_sheet_metadata_deletes_by_id(mock_request):
    mock_request.return_value = {"status": True}

    await AgenticTable.delete_sheet_metadata(
        USER_ID,
        COMPANY_ID,
        tableId=TABLE_ID,
        metadataId="meta_1",
    )

    mock_request.assert_awaited_once_with(
        "delete",
        f"/magic-table/{TABLE_ID}/sheet/metadata/meta_1",
        USER_ID,
        COMPANY_ID,
    )


async def test_bulk_update_status_sends_emit_library_sheet_verified_event_when_set(
    mock_request,
):
    mock_request.return_value = {"status": True}

    await AgenticTable.bulk_update_status(
        USER_ID,
        COMPANY_ID,
        tableId=TABLE_ID,
        rowOrders=[0, 1],
        status=RowVerificationStatus.VERIFIED,
        emitLibrarySheetVerifiedEvent=False,
    )

    mock_request.assert_awaited_once_with(
        "post",
        f"/magic-table/{TABLE_ID}/rows/bulk-update-status",
        USER_ID,
        COMPANY_ID,
        {
            "tableId": TABLE_ID,
            "rowOrders": [0, 1],
            "status": RowVerificationStatus.VERIFIED,
            "emitLibrarySheetVerifiedEvent": False,
        },
    )


async def test_bulk_update_status_omits_emit_library_sheet_verified_event_by_default(
    mock_request,
):
    mock_request.return_value = {"status": True}

    await AgenticTable.bulk_update_status(
        USER_ID,
        COMPANY_ID,
        tableId=TABLE_ID,
        rowOrders=[0],
        status=RowVerificationStatus.VERIFIED,
    )

    body = mock_request.await_args.args[4]
    assert "emitLibrarySheetVerifiedEvent" not in body
