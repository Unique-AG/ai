from unittest.mock import AsyncMock, patch

import pytest

from unique_toolkit.agentic_table.schemas import MagicTableCell, RowMetadataEntryInput
from unique_toolkit.agentic_table.service import AgenticTableService


def _service() -> AgenticTableService:
    return AgenticTableService(
        user_id="u1", company_id="c1", table_id="t1", event_id="e1"
    )


def _cell(row_id: str | None = "row-123") -> MagicTableCell:
    return MagicTableCell(
        sheetId="t1", rowId=row_id, rowOrder=4, columnOrder=0, text=""
    )


@pytest.mark.asyncio
async def test_create_row_metadata_resolves_row_id_and_maps_entries():
    service = _service()
    entries = [
        RowMetadataEntryInput(key="client", value="Mercer", exact_filter=True),
        RowMetadataEntryInput(key="strategy", value="CGM", exact_filter=True),
    ]
    with (
        patch.object(
            AgenticTableService, "get_cell", new=AsyncMock(return_value=_cell())
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
async def test_create_row_metadata_uses_provided_row_id_without_lookup():
    # Batch callers read the row range once and pass the id; paying a get_cell
    # per row is what makes a large library push O(n) round trips.
    service = _service()
    with (
        patch.object(AgenticTableService, "get_cell", new=AsyncMock()) as mock_get_cell,
        patch(
            "unique_toolkit.agentic_table.service.AgenticTable.create_row_metadata",
            new=AsyncMock(return_value={"status": True}),
        ) as mock_create,
    ):
        await service.create_row_metadata(
            4,
            [RowMetadataEntryInput(key="client", value="Mercer")],
            row_id="row-456",
        )

    mock_get_cell.assert_not_awaited()
    assert mock_create.await_args.kwargs["rowId"] == "row-456"


@pytest.mark.asyncio
async def test_create_row_metadata_defaults_exact_filter_to_false():
    service = _service()
    with (
        patch.object(
            AgenticTableService, "get_cell", new=AsyncMock(return_value=_cell())
        ),
        patch(
            "unique_toolkit.agentic_table.service.AgenticTable.create_row_metadata",
            new=AsyncMock(return_value={"status": True}),
        ) as mock_create,
    ):
        await service.create_row_metadata(
            4, [RowMetadataEntryInput(key="reviewer", value="Alex")]
        )

    assert mock_create.await_args.kwargs["entries"] == [
        {"key": "reviewer", "value": "Alex", "exactFilter": False}
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
        AgenticTableService, "get_cell", new=AsyncMock(return_value=_cell(row_id=None))
    ):
        with pytest.raises(ValueError):
            await service.create_row_metadata(
                4, [RowMetadataEntryInput(key="client", value="Mercer")]
            )


@pytest.mark.asyncio
async def test_create_row_metadata_raises_on_api_failure():
    service = _service()
    with (
        patch.object(
            AgenticTableService, "get_cell", new=AsyncMock(return_value=_cell())
        ),
        patch(
            "unique_toolkit.agentic_table.service.AgenticTable.create_row_metadata",
            new=AsyncMock(return_value={"status": False, "message": "boom"}),
        ),
    ):
        with pytest.raises(Exception, match="boom"):
            await service.create_row_metadata(
                4, [RowMetadataEntryInput(key="client", value="Mercer")]
            )
