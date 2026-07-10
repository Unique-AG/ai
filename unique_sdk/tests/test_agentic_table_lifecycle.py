"""Unit tests for the Agentic Table lifecycle wrappers (create/import/export/sheet metadata).

These test the request shape (method, url, params) of the new public-API wrappers by
patching the static request layer; no network involved.
"""

from unittest.mock import AsyncMock, patch

import pytest

from unique_sdk.api_resources._agentic_table import (
    AgenticTable,
    MagicTableArtifactType,
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
    mock_request.return_value = [
        {
            "id": "artifact_1",
            "artifactType": "FULL_REPORT",
            "artifactState": "DONE",
            "contentId": "cont_export",
            "createdAt": "2026-01-01T00:00:00.000Z",
            "updatedAt": "2026-01-01T00:01:00.000Z",
        }
    ]

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
