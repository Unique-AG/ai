from unittest.mock import AsyncMock, patch

import pytest

from unique_toolkit.agentic_table.schemas import (
    MagicTableCell,
    RowMetadataEntry,
    RowMetadataEntryInput,
)
from unique_toolkit.agentic_table.service import AgenticTableService

_SDK = "unique_toolkit.agentic_table.service.AgenticTable"


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


@pytest.mark.asyncio
async def test_update_row_metadata_maps_entry():
    service = _service()
    with patch(
        f"{_SDK}.update_row_metadata", new=AsyncMock(return_value={"status": True})
    ) as mock_update:
        await service.update_row_metadata(
            "meta-1", RowMetadataEntryInput(key="client", value="UBP")
        )

    mock_update.assert_awaited_once_with(
        user_id="u1",
        company_id="c1",
        tableId="t1",
        metadataId="meta-1",
        key="client",
        value="UBP",
        exactFilter=False,
    )


@pytest.mark.asyncio
async def test_update_row_metadata_raises_on_api_failure():
    service = _service()
    with patch(
        f"{_SDK}.update_row_metadata",
        new=AsyncMock(return_value={"status": False, "message": "boom"}),
    ):
        with pytest.raises(Exception, match="boom"):
            await service.update_row_metadata(
                "meta-1", RowMetadataEntryInput(key="client", value="UBP")
            )


@pytest.mark.asyncio
async def test_delete_row_metadata_deletes_by_id():
    service = _service()
    with patch(
        f"{_SDK}.delete_row_metadata", new=AsyncMock(return_value={"status": True})
    ) as mock_delete:
        await service.delete_row_metadata("meta-1")

    mock_delete.assert_awaited_once_with(
        user_id="u1", company_id="c1", tableId="t1", metadataId="meta-1"
    )


@pytest.mark.asyncio
async def test_delete_row_metadata_raises_on_api_failure():
    service = _service()
    with patch(
        f"{_SDK}.delete_row_metadata",
        new=AsyncMock(return_value={"status": False, "message": "boom"}),
    ):
        with pytest.raises(Exception, match="boom"):
            await service.delete_row_metadata("meta-1")


def _entry(id: str, key: str, value: str, exact_filter: bool = False):
    return RowMetadataEntry(id=id, key=key, value=value, exact_filter=exact_filter)


def _patch_writes():
    return (
        patch(
            f"{_SDK}.update_row_metadata", new=AsyncMock(return_value={"status": True})
        ),
        patch(
            f"{_SDK}.delete_row_metadata", new=AsyncMock(return_value={"status": True})
        ),
        patch(
            f"{_SDK}.create_row_metadata", new=AsyncMock(return_value={"status": True})
        ),
    )


@pytest.mark.asyncio
async def test_replace_row_metadata_updates_changed_creates_missing_skips_equal():
    service = _service()
    existing = [
        _entry("m-client", "client", "Mercer"),
        _entry("m-strategy", "strategy", "CGM"),
        _entry("m-other", "untouched", "keep"),
    ]
    p_update, p_delete, p_create = _patch_writes()
    with p_update as mock_update, p_delete as mock_delete, p_create as mock_create:
        await service.replace_row_metadata(
            4,
            [
                RowMetadataEntryInput(key="client", value="UBP"),
                RowMetadataEntryInput(key="strategy", value="CGM"),
                RowMetadataEntryInput(key="region", value="EU"),
            ],
            row_id="row-9",
            existing=existing,
        )

    mock_update.assert_awaited_once()
    assert mock_update.await_args.kwargs["metadataId"] == "m-client"
    assert mock_update.await_args.kwargs["value"] == "UBP"
    mock_delete.assert_not_awaited()
    mock_create.assert_awaited_once()
    assert mock_create.await_args.kwargs["rowId"] == "row-9"
    assert mock_create.await_args.kwargs["entries"] == [
        {"key": "region", "value": "EU", "exactFilter": False}
    ]


@pytest.mark.asyncio
async def test_replace_row_metadata_updates_when_only_exact_filter_changes():
    service = _service()
    p_update, p_delete, p_create = _patch_writes()
    with p_update as mock_update, p_delete, p_create as mock_create:
        await service.replace_row_metadata(
            4,
            [RowMetadataEntryInput(key="client", value="UBP", exact_filter=True)],
            row_id="row-9",
            existing=[_entry("m-client", "client", "UBP", exact_filter=False)],
        )

    assert mock_update.await_args.kwargs["exactFilter"] is True
    mock_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_replace_row_metadata_keeps_matching_duplicate_and_deletes_rest():
    # A key held twice would leave a stale value searchable after re-add.
    service = _service()
    existing = [
        _entry("m-old", "client", "Mercer"),
        _entry("m-new", "client", "UBP"),
    ]
    p_update, p_delete, p_create = _patch_writes()
    with p_update as mock_update, p_delete as mock_delete, p_create:
        await service.replace_row_metadata(
            4,
            [RowMetadataEntryInput(key="client", value="UBP")],
            row_id="row-9",
            existing=existing,
        )

    mock_update.assert_not_awaited()
    mock_delete.assert_awaited_once()
    assert mock_delete.await_args.kwargs["metadataId"] == "m-old"


@pytest.mark.asyncio
async def test_replace_row_metadata_updates_first_duplicate_when_none_match():
    service = _service()
    existing = [
        _entry("m-a", "client", "Mercer"),
        _entry("m-b", "client", "Aon"),
    ]
    p_update, p_delete, p_create = _patch_writes()
    with p_update as mock_update, p_delete as mock_delete, p_create:
        await service.replace_row_metadata(
            4,
            [RowMetadataEntryInput(key="client", value="UBP")],
            row_id="row-9",
            existing=existing,
        )

    assert mock_update.await_args.kwargs["metadataId"] == "m-a"
    assert mock_delete.await_args.kwargs["metadataId"] == "m-b"


@pytest.mark.asyncio
async def test_replace_row_metadata_reads_row_when_existing_not_given():
    service = _service()
    cell = MagicTableCell(
        sheetId="t1",
        rowId="row-123",
        rowOrder=4,
        columnOrder=0,
        text="",
        rowMetadata=[{"id": "m-client", "key": "client", "value": "Mercer"}],
    )
    p_update, p_delete, p_create = _patch_writes()
    with (
        patch.object(
            AgenticTableService, "get_cell", new=AsyncMock(return_value=cell)
        ) as mock_get_cell,
        p_update as mock_update,
        p_delete,
        p_create as mock_create,
    ):
        await service.replace_row_metadata(
            4,
            [
                RowMetadataEntryInput(key="client", value="UBP"),
                RowMetadataEntryInput(key="region", value="EU"),
            ],
        )

    mock_get_cell.assert_awaited_once_with(4, 0, include_row_metadata=True)
    assert mock_update.await_args.kwargs["metadataId"] == "m-client"
    assert mock_create.await_args.kwargs["rowId"] == "row-123"


@pytest.mark.asyncio
async def test_replace_row_metadata_rejects_duplicate_input_keys():
    service = _service()
    with pytest.raises(ValueError, match="Duplicate"):
        await service.replace_row_metadata(
            4,
            [
                RowMetadataEntryInput(key="client", value="UBP"),
                RowMetadataEntryInput(key="client", value="Aon"),
            ],
            existing=[],
        )


@pytest.mark.asyncio
async def test_replace_row_metadata_noop_on_empty():
    service = _service()
    with patch.object(AgenticTableService, "get_cell", new=AsyncMock()) as mock_get:
        await service.replace_row_metadata(4, [])
    mock_get.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_multiple_cells_forwards_overwrite_library_rows():
    service = _service()
    with patch(
        f"{_SDK}.set_multiple_cells", new=AsyncMock(return_value={"status": True})
    ) as mock_set:
        await service.set_multiple_cells(
            [MagicTableCell(sheetId="t1", rowOrder=1, columnOrder=2, text="a")],
            overwrite_library_rows=True,
        )

    assert mock_set.await_args.kwargs["overwriteLibraryRows"] is True


@pytest.mark.asyncio
async def test_set_multiple_cells_passes_none_overwrite_by_default():
    service = _service()
    with patch(
        f"{_SDK}.set_multiple_cells", new=AsyncMock(return_value={"status": True})
    ) as mock_set:
        await service.set_multiple_cells(
            [MagicTableCell(sheetId="t1", rowOrder=1, columnOrder=2, text="a")]
        )

    assert mock_set.await_args.kwargs["overwriteLibraryRows"] is None
