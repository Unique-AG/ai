from unittest.mock import AsyncMock, patch

import pytest

from unique_toolkit.agentic_table.schemas import MagicTableCell, RowMetadataEntry
from unique_toolkit.agentic_table.service import AgenticTableService


def _service() -> AgenticTableService:
    return AgenticTableService(
        user_id="u1", company_id="c1", table_id="t1", event_id="e1"
    )


@pytest.mark.asyncio
async def test_create_row_metadata_resolves_row_id_and_maps_entries():
    service = _service()
    entries = [
        RowMetadataEntry(id="ignored-1", key="client", value="Mercer", exact_filter=True),
        RowMetadataEntry(id="ignored-2", key="strategy", value="CGM", exact_filter=True),
    ]
    with (
        patch.object(
            AgenticTableService,
            "get_cell",
            new=AsyncMock(
                return_value=MagicTableCell(
                    sheetId="t1", rowId="row-123", rowOrder=4, columnOrder=0, text=""
                )
            ),
        ),
        patch(
            "unique_toolkit.agentic_table.service.AgenticTable.create_row_metadata",
            new=AsyncMock(return_value={"status": True}),
        ) as mock_create,
    ):
        await service.create_row_metadata(4, entries)

    mock_create.assert_awaited_once()
    kwargs = mock_create.await_args.kwargs
    assert kwargs["tableId"] == "t1"
    assert kwargs["rowId"] == "row-123"
    assert kwargs["entries"] == [
        {"key": "client", "value": "Mercer", "exactFilter": True},
        {"key": "strategy", "value": "CGM", "exactFilter": True},
    ]


@pytest.mark.asyncio
async def test_create_row_metadata_noop_on_empty():
    service = _service()
    with patch(
        "unique_toolkit.agentic_table.service.AgenticTable.create_row_metadata",
        new=AsyncMock(),
    ) as mock_create:
        await service.create_row_metadata(4, [])
    mock_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_row_metadata_raises_without_row_id():
    service = _service()
    with patch.object(
        AgenticTableService,
        "get_cell",
        new=AsyncMock(
            return_value=MagicTableCell(
                sheetId="t1", rowOrder=4, columnOrder=0, text=""
            )
        ),
    ):
        with pytest.raises(ValueError):
            await service.create_row_metadata(
                4, [RowMetadataEntry(id="x", key="client", value="Mercer")]
            )


@pytest.mark.asyncio
async def test_create_row_metadata_raises_on_api_failure():
    service = _service()
    with (
        patch.object(
            AgenticTableService,
            "get_cell",
            new=AsyncMock(
                return_value=MagicTableCell(
                    sheetId="t1", rowId="row-123", rowOrder=4, columnOrder=0, text=""
                )
            ),
        ),
        patch(
            "unique_toolkit.agentic_table.service.AgenticTable.create_row_metadata",
            new=AsyncMock(return_value={"status": False, "message": "boom"}),
        ),
    ):
        with pytest.raises(Exception, match="boom"):
            await service.create_row_metadata(
                4, [RowMetadataEntry(id="x", key="client", value="Mercer")]
            )
