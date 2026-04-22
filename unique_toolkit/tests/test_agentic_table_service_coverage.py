"""Coverage for ``AgenticTableService`` paths introduced or tightened with SDK 0.11.12 (diff-cover)."""

from unittest.mock import AsyncMock, patch

import pytest
from unique_sdk import MagicTableArtifactType, RowVerificationStatus

from unique_toolkit.agentic_table.service import (
    AgenticTableService,
    _sheet_batch_cells_include_row_metadata_from_api,
)


def test_sheet_batch_helper_empty_cells() -> None:
    assert _sheet_batch_cells_include_row_metadata_from_api([]) is True


@pytest.mark.asyncio
async def test_get_sheet_row_metadata_empty_cell_batch_evaluates_helper() -> None:
    """Empty ``magicTableCells`` still calls the helper (``return True`` for empty list)."""
    header = {
        "sheetId": "sheet-1",
        "name": "Test",
        "state": "IDLE",
        "magicTableRowCount": 1,
        "chatId": "chat-1",
        "createdBy": "user-1",
        "companyId": "company-1",
        "createdAt": "2020-01-01T00:00:00Z",
    }
    batch_empty = {**header, "magicTableCells": []}

    async def fake_get_sheet_data(
        *_args: object,
        **kwargs: object,
    ) -> dict:
        if kwargs.get("includeCells") is False:
            return header
        return batch_empty

    svc = AgenticTableService("user-1", "company-1", "table-1")
    with patch(
        "unique_toolkit.agentic_table.service.AgenticTable.get_sheet_data",
        new_callable=AsyncMock,
        side_effect=fake_get_sheet_data,
    ):
        with patch.object(svc, "get_cell", new_callable=AsyncMock) as get_cell:
            sheet = await svc.get_sheet(
                start_row=0,
                end_row=1,
                include_row_metadata=True,
            )

    get_cell.assert_not_awaited()
    assert sheet.magic_table_cells == []


@pytest.mark.asyncio
async def test_get_num_rows_returns_count() -> None:
    svc = AgenticTableService("user-1", "company-1", "table-1")
    with patch(
        "unique_toolkit.agentic_table.service.AgenticTable.get_sheet_data",
        new_callable=AsyncMock,
        return_value={
            "sheetId": "s",
            "name": "n",
            "state": "IDLE",
            "magicTableRowCount": 42,
        },
    ):
        assert await svc.get_num_rows() == 42


@pytest.mark.asyncio
async def test_get_num_rows_raises_when_row_count_missing() -> None:
    svc = AgenticTableService("user-1", "company-1", "table-1")
    with patch(
        "unique_toolkit.agentic_table.service.AgenticTable.get_sheet_data",
        new_callable=AsyncMock,
        return_value={"sheetId": "s", "name": "n", "state": "IDLE"},
    ):
        with pytest.raises(RuntimeError, match="magicTableRowCount"):
            await svc.get_num_rows()


@pytest.mark.asyncio
async def test_get_sheet_raises_when_total_rows_missing() -> None:
    svc = AgenticTableService("user-1", "company-1", "table-1")
    with patch(
        "unique_toolkit.agentic_table.service.AgenticTable.get_sheet_data",
        new_callable=AsyncMock,
        return_value={"sheetId": "s", "name": "n", "state": "IDLE"},
    ):
        with pytest.raises(RuntimeError, match="magicTableRowCount"):
            await svc.get_sheet()


@pytest.mark.asyncio
async def test_get_sheet_metadata_parses_entries() -> None:
    svc = AgenticTableService("user-1", "company-1", "table-1")
    sheet_info = {
        "sheetId": "sheet-1",
        "name": "Test",
        "state": "IDLE",
        "createdBy": "user-1",
        "companyId": "company-1",
        "createdAt": "2020-01-01T00:00:00Z",
        "magicTableSheetMetadata": [
            {"id": "m1", "key": "k1", "value": "v1", "exactFilter": False},
        ],
    }
    with patch(
        "unique_toolkit.agentic_table.service.AgenticTable.get_sheet_data",
        new_callable=AsyncMock,
        return_value=sheet_info,
    ):
        rows = await svc.get_sheet_metadata()

    assert len(rows) == 1
    assert rows[0].key == "k1"


@pytest.mark.parametrize(
    ("mime_type", "name"),
    [
        (None, None),
        ("application/pdf", None),
        (None, "report.pdf"),
        ("application/pdf", "report.pdf"),
    ],
)
@pytest.mark.asyncio
async def test_set_artifact_optional_extras(
    mime_type: str | None,
    name: str | None,
) -> None:
    svc = AgenticTableService("user-1", "company-1", "table-1")
    with patch(
        "unique_toolkit.agentic_table.service.AgenticTable.set_artifact",
        new_callable=AsyncMock,
    ) as set_artifact:
        await svc.set_artifact(
            MagicTableArtifactType.QUESTIONS,
            "content-1",
            mime_type=mime_type,
            name=name,
        )

    kwargs = set_artifact.await_args.kwargs
    assert kwargs["artifactType"] == MagicTableArtifactType.QUESTIONS
    assert kwargs["contentId"] == "content-1"
    if mime_type is None:
        assert "mimeType" not in kwargs
    else:
        assert kwargs["mimeType"] == mime_type
    if name is None:
        assert "name" not in kwargs
    else:
        assert kwargs["name"] == name


@pytest.mark.asyncio
async def test_update_row_verification_status_without_locked() -> None:
    svc = AgenticTableService("user-1", "company-1", "table-1")
    with patch(
        "unique_toolkit.agentic_table.service.AgenticTable.bulk_update_status",
        new_callable=AsyncMock,
    ) as bulk:
        await svc.update_row_verification_status(
            [0, 1],
            RowVerificationStatus.NEEDS_REVIEW,
        )

    assert "locked" not in bulk.await_args.kwargs


@pytest.mark.asyncio
async def test_update_row_verification_status_with_locked() -> None:
    svc = AgenticTableService("user-1", "company-1", "table-1")
    with patch(
        "unique_toolkit.agentic_table.service.AgenticTable.bulk_update_status",
        new_callable=AsyncMock,
    ) as bulk:
        await svc.update_row_verification_status(
            [2],
            RowVerificationStatus.VERIFIED,
            locked=True,
        )

    assert bulk.await_args.kwargs.get("locked") is True
