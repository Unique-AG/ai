"""Tests for ``AgenticTableService.get_sheet`` row metadata (UN-19885, SDK PR #1467)."""

from unittest.mock import AsyncMock, patch

import pytest

from unique_toolkit.agentic_table.schemas import MagicTableCell
from unique_toolkit.agentic_table.service import AgenticTableService


def _minimal_sheet_header(*, row_count: int = 2) -> dict:
    return {
        "sheetId": "sheet-1",
        "name": "Test",
        "state": "IDLE",
        "magicTableRowCount": row_count,
        "chatId": "chat-1",
        "createdBy": "user-1",
        "companyId": "company-1",
        "createdAt": "2020-01-01T00:00:00Z",
    }


def _cell(row: int, col: int, *, row_metadata: list | None = None) -> dict:
    c: dict = {
        "sheetId": "sheet-1",
        "rowOrder": row,
        "columnOrder": col,
        "text": f"r{row}c{col}",
        "logEntries": [],
    }
    if row_metadata is not None:
        c["rowMetadata"] = row_metadata
    return c


@pytest.mark.asyncio
async def test_get_sheet_skips_get_cell_when_row_metadata_present_on_cells() -> None:
    header = _minimal_sheet_header()
    meta = [{"id": "m1", "key": "k", "value": "v", "exactFilter": False}]
    batch = {
        **_minimal_sheet_header(),
        "magicTableCells": [
            _cell(0, 0, row_metadata=meta),
            _cell(0, 1, row_metadata=meta),
        ],
    }

    async def fake_get_sheet_data(
        *_args: object,
        **kwargs: object,
    ) -> dict:
        if kwargs.get("includeCells") is False:
            return header
        return batch

    svc = AgenticTableService("user-1", "company-1", "table-1")
    with patch(
        "unique_toolkit.agentic_table.service.AgenticTable.get_sheet_data",
        new_callable=AsyncMock,
        side_effect=fake_get_sheet_data,
    ) as gsm:
        with patch.object(svc, "get_cell", new_callable=AsyncMock) as get_cell:
            sheet = await svc.get_sheet(
                start_row=0,
                end_row=2,
                batch_size=100,
                include_row_metadata=True,
            )

    batch_kwargs = [
        c.kwargs for c in gsm.await_args_list if c.kwargs.get("includeCells")
    ]
    assert len(batch_kwargs) == 1
    assert batch_kwargs[0].get("includeRowMetadata") is True
    get_cell.assert_not_awaited()
    assert len(sheet.magic_table_cells) == 2
    assert sheet.magic_table_cells[0].row_metadata[0].key == "k"


@pytest.mark.asyncio
async def test_get_sheet_legacy_fallback_calls_get_cell_when_row_metadata_absent() -> (
    None
):
    header = _minimal_sheet_header()
    batch = {
        **_minimal_sheet_header(),
        "magicTableCells": [
            _cell(0, 0),
            _cell(0, 1),
        ],
    }
    meta = [{"id": "m1", "key": "rk", "value": "rv", "exactFilter": False}]

    async def fake_get_sheet_data(
        *_args: object,
        **kwargs: object,
    ) -> dict:
        if kwargs.get("includeCells") is False:
            return header
        return batch

    hydrated = MagicTableCell.model_validate(
        {
            "sheetId": "sheet-1",
            "rowOrder": 0,
            "columnOrder": 0,
            "text": "r0c0",
            "logEntries": [],
            "rowMetadata": meta,
        }
    )

    svc = AgenticTableService("user-1", "company-1", "table-1")
    with patch(
        "unique_toolkit.agentic_table.service.AgenticTable.get_sheet_data",
        new_callable=AsyncMock,
        side_effect=fake_get_sheet_data,
    ):
        with patch.object(
            svc,
            "get_cell",
            new_callable=AsyncMock,
            return_value=hydrated,
        ) as get_cell:
            sheet = await svc.get_sheet(
                start_row=0,
                end_row=2,
                batch_size=100,
                include_row_metadata=True,
            )

    get_cell.assert_awaited()
    assert get_cell.await_count == 1
    assert len(sheet.magic_table_cells) == 2
    assert sheet.magic_table_cells[0].row_metadata[0].key == "rk"
    assert sheet.magic_table_cells[1].row_metadata[0].key == "rk"


@pytest.mark.asyncio
async def test_get_sheet_does_not_forward_include_row_metadata_when_disabled() -> None:
    header = _minimal_sheet_header()
    batch = {
        **_minimal_sheet_header(),
        "magicTableCells": [_cell(0, 0)],
    }

    async def fake_get_sheet_data(
        *_args: object,
        **kwargs: object,
    ) -> dict:
        if kwargs.get("includeCells") is False:
            return header
        return batch

    svc = AgenticTableService("user-1", "company-1", "table-1")
    with patch(
        "unique_toolkit.agentic_table.service.AgenticTable.get_sheet_data",
        new_callable=AsyncMock,
        side_effect=fake_get_sheet_data,
    ) as gsm:
        with patch.object(svc, "get_cell", new_callable=AsyncMock) as get_cell:
            await svc.get_sheet(
                start_row=0,
                end_row=1,
                include_row_metadata=False,
            )

    batch_kwargs = [
        c.kwargs for c in gsm.await_args_list if c.kwargs.get("includeCells")
    ]
    assert len(batch_kwargs) == 1
    assert "includeRowMetadata" not in batch_kwargs[0]
    get_cell.assert_not_awaited()
