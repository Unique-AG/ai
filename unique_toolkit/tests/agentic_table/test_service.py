import logging
from unittest.mock import AsyncMock, patch

import pytest
from unique_sdk import (
    AgenticTableSheetState,
    AgreementStatus,
    CellRendererTypes,
    FilterTypes,
    RowVerificationStatus,
    SelectionMethod,
)
from unique_sdk.api_resources._agentic_table import ActivityStatus, MagicTableAction

from unique_toolkit.agentic_table.schemas import (
    ArtifactType,
    LogEntry,
    MagicTableCell,
)
from unique_toolkit.agentic_table.service import (
    AgenticTableService,
    LockedAgenticTableError,
)

TABLE_ID = "table-123"
USER_ID = "user-1"
COMPANY_ID = "company-1"


@pytest.fixture
def service() -> AgenticTableService:
    return AgenticTableService(
        user_id=USER_ID,
        company_id=COMPANY_ID,
        table_id=TABLE_ID,
        event_id="event-1",
        logger=logging.getLogger("test-agentic-table"),
    )


@pytest.fixture
def sdk_cell_data() -> dict:
    return {
        "sheetId": "sheet-1",
        "rowOrder": 0,
        "columnOrder": 0,
        "rowLocked": False,
        "text": "hello",
        "logEntries": [],
    }


class TestInit:
    def test_stores_attributes(self, service: AgenticTableService):
        assert service.table_id == TABLE_ID
        assert service._user_id == USER_ID
        assert service._company_id == COMPANY_ID
        assert service._event_id == "event-1"

    def test_default_logger(self):
        svc = AgenticTableService(
            user_id=USER_ID, company_id=COMPANY_ID, table_id=TABLE_ID
        )
        assert svc.logger is not None
        assert svc._event_id is None


class TestSetCell:
    @pytest.mark.asyncio
    async def test_set_cell_without_log_entries(self, service: AgenticTableService):
        with patch(
            "unique_toolkit.agentic_table.service.AgenticTable.set_cell",
            new=AsyncMock(return_value=None),
        ) as mock_set_cell:
            await service.set_cell(row=1, column=2, text="value")

        mock_set_cell.assert_awaited_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            tableId=TABLE_ID,
            rowOrder=1,
            columnOrder=2,
            text="value",
            logEntries=[],
        )

    @pytest.mark.asyncio
    async def test_set_cell_with_log_entries(self, service: AgenticTableService):
        log_entry = LogEntry(text="log text", created_at="2024-01-01T00:00:00Z")

        with patch(
            "unique_toolkit.agentic_table.service.AgenticTable.set_cell",
            new=AsyncMock(return_value=None),
        ) as mock_set_cell:
            await service.set_cell(
                row=0, column=0, text="value", log_entries=[log_entry]
            )

        mock_set_cell.assert_awaited_once()
        kwargs = mock_set_cell.await_args.kwargs
        assert len(kwargs["logEntries"]) == 1

    @pytest.mark.asyncio
    async def test_set_cell_logs_on_exception(
        self, service: AgenticTableService, caplog: pytest.LogCaptureFixture
    ):
        with patch(
            "unique_toolkit.agentic_table.service.AgenticTable.set_cell",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ):
            with caplog.at_level(logging.ERROR, logger="test-agentic-table"):
                await service.set_cell(row=0, column=0, text="v")

        assert any("Error setting cell 0, 0" in rec.message for rec in caplog.records)


class TestGetCell:
    @pytest.mark.asyncio
    async def test_get_cell_returns_magic_table_cell(
        self, service: AgenticTableService, sdk_cell_data: dict
    ):
        with patch(
            "unique_toolkit.agentic_table.service.AgenticTable.get_cell",
            new=AsyncMock(return_value=sdk_cell_data),
        ) as mock_get_cell:
            result = await service.get_cell(row=0, column=0)

        mock_get_cell.assert_awaited_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            tableId=TABLE_ID,
            rowOrder=0,
            columnOrder=0,
            includeRowMetadata=True,
        )
        assert isinstance(result, MagicTableCell)
        assert result.text == "hello"
        assert result.row_order == 0


class TestSetMultipleCells:
    @pytest.mark.asyncio
    async def test_set_multiple_cells_single_batch(self, service: AgenticTableService):
        cells = [
            MagicTableCell(
                sheet_id="s",
                row_order=i,
                column_order=0,
                row_locked=False,
                text=f"t{i}",
            )
            for i in range(3)
        ]

        with patch(
            "unique_toolkit.agentic_table.service.AgenticTable.set_multiple_cells",
            new=AsyncMock(return_value=None),
        ) as mock_set:
            await service.set_multiple_cells(cells=cells)

        assert mock_set.await_count == 1

    @pytest.mark.asyncio
    async def test_set_multiple_cells_batched(self, service: AgenticTableService):
        cells = [
            MagicTableCell(
                sheet_id="s",
                row_order=i,
                column_order=0,
                row_locked=False,
                text="t",
            )
            for i in range(5)
        ]

        with patch(
            "unique_toolkit.agentic_table.service.AgenticTable.set_multiple_cells",
            new=AsyncMock(return_value=None),
        ) as mock_set:
            await service.set_multiple_cells(cells=cells, batch_size=2)

        assert mock_set.await_count == 3


class TestSetActivity:
    @pytest.mark.asyncio
    async def test_set_activity_default_status(self, service: AgenticTableService):
        with patch(
            "unique_toolkit.agentic_table.service.AgenticTable.set_activity",
            new=AsyncMock(return_value=None),
        ) as mock_set:
            await service.set_activity(
                text="working",
                activity=MagicTableAction.RERUN_ROW,
            )

        mock_set.assert_awaited_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            tableId=TABLE_ID,
            activity=MagicTableAction.RERUN_ROW.value,
            status=ActivityStatus.IN_PROGRESS.value,
            text="working",
        )

    @pytest.mark.asyncio
    async def test_set_activity_explicit_status(self, service: AgenticTableService):
        with patch(
            "unique_toolkit.agentic_table.service.AgenticTable.set_activity",
            new=AsyncMock(return_value=None),
        ) as mock_set:
            await service.set_activity(
                text="done",
                activity=MagicTableAction.RERUN_ROW,
                status=ActivityStatus.COMPLETED,
            )

        assert mock_set.await_args.kwargs["status"] == ActivityStatus.COMPLETED.value


class TestRegisterAgent:
    @pytest.mark.asyncio
    async def test_register_agent_when_idle(self, service: AgenticTableService):
        with (
            patch(
                "unique_toolkit.agentic_table.service.AgenticTable.get_sheet_state",
                new=AsyncMock(return_value=AgenticTableSheetState.IDLE),
            ) as mock_state,
            patch(
                "unique_toolkit.agentic_table.service.AgenticTable.update_sheet_state",
                new=AsyncMock(return_value=None),
            ) as mock_update,
        ):
            await service.register_agent()

        mock_state.assert_awaited_once()
        mock_update.assert_awaited_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            tableId=TABLE_ID,
            state=AgenticTableSheetState.PROCESSING,
        )

    @pytest.mark.asyncio
    async def test_register_agent_raises_when_processing(
        self, service: AgenticTableService
    ):
        with (
            patch(
                "unique_toolkit.agentic_table.service.AgenticTable.get_sheet_state",
                new=AsyncMock(return_value=AgenticTableSheetState.PROCESSING),
            ),
            patch(
                "unique_toolkit.agentic_table.service.AgenticTable.update_sheet_state",
                new=AsyncMock(return_value=None),
            ) as mock_update,
        ):
            with pytest.raises(LockedAgenticTableError):
                await service.register_agent()
            mock_update.assert_not_awaited()


class TestDeregisterAgent:
    @pytest.mark.asyncio
    async def test_deregister_agent_sets_idle(self, service: AgenticTableService):
        with patch(
            "unique_toolkit.agentic_table.service.AgenticTable.update_sheet_state",
            new=AsyncMock(return_value=None),
        ) as mock_update:
            await service.deregister_agent()

        mock_update.assert_awaited_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            tableId=TABLE_ID,
            state=AgenticTableSheetState.IDLE,
        )


class TestSetArtifact:
    @pytest.mark.asyncio
    async def test_set_artifact_passes_enum_value(self, service: AgenticTableService):
        with patch(
            "unique_toolkit.agentic_table.service.AgenticTable.set_artifact",
            new=AsyncMock(return_value=None),
        ) as mock_set:
            await service.set_artifact(
                artifact_type=ArtifactType.AGENTIC_REPORT,
                content_id="content-1",
                mime_type="application/pdf",
                name="report.pdf",
            )

        mock_set.assert_awaited_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            tableId=TABLE_ID,
            artifactType=ArtifactType.AGENTIC_REPORT.value,
            contentId="content-1",
            mimeType="application/pdf",
            name="report.pdf",
        )


class TestSetColumnStyle:
    @pytest.mark.asyncio
    async def test_set_column_style_builds_params(self, service: AgenticTableService):
        with patch(
            "unique_toolkit.agentic_table.service.AgenticTable.set_column_metadata",
            new=AsyncMock(return_value=(True, "ok")),
        ) as mock_set:
            await service.set_column_style(
                column=1,
                width=100,
                cell_renderer=CellRendererTypes.CHECKBOX_LOCK_CELL_RENDERER,
                filter=FilterTypes.VALUE_MATCH_FILTER,
                editable=True,
            )

        kwargs = mock_set.await_args.kwargs
        assert kwargs["columnOrder"] == 1
        assert kwargs["columnWidth"] == 100
        assert (
            kwargs["cellRenderer"]
            == CellRendererTypes.CHECKBOX_LOCK_CELL_RENDERER.value
        )
        assert kwargs["filter"] == FilterTypes.VALUE_MATCH_FILTER.value
        assert kwargs["editable"] is True

    @pytest.mark.asyncio
    async def test_set_column_style_raises_on_failure(
        self, service: AgenticTableService
    ):
        with patch(
            "unique_toolkit.agentic_table.service.AgenticTable.set_column_metadata",
            new=AsyncMock(return_value=(False, "boom")),
        ):
            with pytest.raises(Exception, match="boom"):
                await service.set_column_style(column=1, width=50)

    @pytest.mark.asyncio
    async def test_set_column_width_delegates(self, service: AgenticTableService):
        with patch(
            "unique_toolkit.agentic_table.service.AgenticTable.set_column_metadata",
            new=AsyncMock(return_value=(True, "ok")),
        ) as mock_set:
            await service.set_column_width(column=2, width=42)

        kwargs = mock_set.await_args.kwargs
        assert kwargs["columnOrder"] == 2
        assert kwargs["columnWidth"] == 42


class TestGetNumRows:
    @pytest.mark.asyncio
    async def test_get_num_rows_returns_count(self, service: AgenticTableService):
        """Covers line 285: return sheet_info["magicTableRowCount"]."""
        with patch(
            "unique_toolkit.agentic_table.service.AgenticTable.get_sheet_data",
            new=AsyncMock(return_value={"magicTableRowCount": 7}),
        ) as mock_get:
            result = await service.get_num_rows()

        assert result == 7
        mock_get.assert_awaited_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            tableId=TABLE_ID,
            includeRowCount=True,
            includeCells=False,
            includeLogHistory=False,
        )


class TestGetSheet:
    @pytest.mark.asyncio
    async def test_get_sheet_empty_table(self, service: AgenticTableService):
        """Covers line 319 via initial row-count fetch."""
        sheet_info = {
            "sheetId": "sheet-1",
            "name": "My Sheet",
            "state": AgenticTableSheetState.IDLE.value,
            "magicTableRowCount": 0,
            "chatId": "chat-1",
            "createdBy": "user-1",
            "companyId": COMPANY_ID,
            "createdAt": "2024-01-01T00:00:00Z",
        }
        with patch(
            "unique_toolkit.agentic_table.service.AgenticTable.get_sheet_data",
            new=AsyncMock(return_value=sheet_info),
        ) as mock_get:
            sheet = await service.get_sheet()

        mock_get.assert_awaited_once()
        assert sheet.total_number_of_rows == 0
        assert sheet.magic_table_cells == []

    @pytest.mark.asyncio
    async def test_get_sheet_paginates_batches(self, service: AgenticTableService):
        sheet_info = {
            "sheetId": "sheet-1",
            "name": "My Sheet",
            "state": AgenticTableSheetState.IDLE.value,
            "magicTableRowCount": 3,
            "chatId": "chat-1",
            "createdBy": "user-1",
            "companyId": COMPANY_ID,
            "createdAt": "2024-01-01T00:00:00Z",
        }
        batch1 = {
            "magicTableCells": [
                {
                    "sheetId": "sheet-1",
                    "rowOrder": 0,
                    "columnOrder": 0,
                    "rowLocked": False,
                    "text": "a",
                    "logEntries": [],
                },
                {
                    "sheetId": "sheet-1",
                    "rowOrder": 1,
                    "columnOrder": 0,
                    "rowLocked": False,
                    "text": "b",
                    "logEntries": [],
                },
            ]
        }
        batch2 = {
            "magicTableCells": [
                {
                    "sheetId": "sheet-1",
                    "rowOrder": 2,
                    "columnOrder": 0,
                    "rowLocked": False,
                    "text": "c",
                    "logEntries": [],
                },
            ]
        }

        with patch(
            "unique_toolkit.agentic_table.service.AgenticTable.get_sheet_data",
            new=AsyncMock(side_effect=[sheet_info, batch1, batch2]),
        ) as mock_get:
            sheet = await service.get_sheet(batch_size=2)

        assert mock_get.await_count == 3
        assert sheet.total_number_of_rows == 3
        assert len(sheet.magic_table_cells) == 3
        assert [c.text for c in sheet.magic_table_cells] == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_get_sheet_caps_end_row_to_total(self, service: AgenticTableService):
        sheet_info = {
            "sheetId": "sheet-1",
            "name": "My Sheet",
            "state": AgenticTableSheetState.IDLE.value,
            "magicTableRowCount": 2,
            "chatId": "chat-1",
            "createdBy": "user-1",
            "companyId": COMPANY_ID,
            "createdAt": "2024-01-01T00:00:00Z",
        }
        batch = {"magicTableCells": []}
        with patch(
            "unique_toolkit.agentic_table.service.AgenticTable.get_sheet_data",
            new=AsyncMock(side_effect=[sheet_info, batch]),
        ):
            sheet = await service.get_sheet(start_row=0, end_row=100, batch_size=10)
        assert sheet.total_number_of_rows == 2

    @pytest.mark.asyncio
    async def test_get_sheet_raises_when_start_greater_than_end(
        self, service: AgenticTableService
    ):
        sheet_info = {
            "sheetId": "sheet-1",
            "name": "My Sheet",
            "state": AgenticTableSheetState.IDLE.value,
            "magicTableRowCount": 10,
            "chatId": "chat-1",
            "createdBy": "user-1",
            "companyId": COMPANY_ID,
            "createdAt": "2024-01-01T00:00:00Z",
        }
        with patch(
            "unique_toolkit.agentic_table.service.AgenticTable.get_sheet_data",
            new=AsyncMock(return_value=sheet_info),
        ):
            with pytest.raises(Exception, match="Start row is greater than end row"):
                await service.get_sheet(start_row=5, end_row=2)

    @pytest.mark.asyncio
    async def test_get_sheet_raises_when_negative_rows(
        self, service: AgenticTableService
    ):
        sheet_info = {
            "sheetId": "sheet-1",
            "name": "My Sheet",
            "state": AgenticTableSheetState.IDLE.value,
            "magicTableRowCount": 10,
            "chatId": "chat-1",
            "createdBy": "user-1",
            "companyId": COMPANY_ID,
            "createdAt": "2024-01-01T00:00:00Z",
        }
        with patch(
            "unique_toolkit.agentic_table.service.AgenticTable.get_sheet_data",
            new=AsyncMock(return_value=sheet_info),
        ):
            with pytest.raises(Exception, match="negative"):
                await service.get_sheet(start_row=-1, end_row=5)

    @pytest.mark.asyncio
    async def test_get_sheet_with_row_metadata(self, service: AgenticTableService):
        """Covers line 370: second-pass assignment from row_metadata_map.

        Two cells in the same row ensure the second cell takes its
        ``rowMetadata`` entry from the already-populated map.
        """
        sheet_info = {
            "sheetId": "sheet-1",
            "name": "My Sheet",
            "state": AgenticTableSheetState.IDLE.value,
            "magicTableRowCount": 1,
            "chatId": "chat-1",
            "createdBy": "user-1",
            "companyId": COMPANY_ID,
            "createdAt": "2024-01-01T00:00:00Z",
        }
        batch = {
            "magicTableCells": [
                {
                    "sheetId": "sheet-1",
                    "rowOrder": 0,
                    "columnOrder": 0,
                    "rowLocked": False,
                    "text": "a",
                    "logEntries": [],
                },
                {
                    "sheetId": "sheet-1",
                    "rowOrder": 0,
                    "columnOrder": 1,
                    "rowLocked": False,
                    "text": "b",
                    "logEntries": [],
                },
            ]
        }
        cell_with_metadata = {
            "sheetId": "sheet-1",
            "rowOrder": 0,
            "columnOrder": 0,
            "rowLocked": False,
            "text": "a",
            "logEntries": [],
            "rowMetadata": [
                {
                    "id": "meta-1",
                    "key": "clientId",
                    "value": "123",
                    "exactFilter": False,
                }
            ],
        }

        with (
            patch(
                "unique_toolkit.agentic_table.service.AgenticTable.get_sheet_data",
                new=AsyncMock(side_effect=[sheet_info, batch]),
            ),
            patch(
                "unique_toolkit.agentic_table.service.AgenticTable.get_cell",
                new=AsyncMock(return_value=cell_with_metadata),
            ) as mock_get_cell,
        ):
            sheet = await service.get_sheet(include_row_metadata=True)

        mock_get_cell.assert_awaited_once()
        assert len(sheet.magic_table_cells) == 2
        for cell in sheet.magic_table_cells:
            assert len(cell.row_metadata) == 1
            assert cell.row_metadata[0].key == "clientId"

    @pytest.mark.asyncio
    async def test_get_sheet_row_metadata_empty_not_assigned(
        self, service: AgenticTableService
    ):
        """When cell has no row metadata, map stays empty and no assignment occurs."""
        sheet_info = {
            "sheetId": "sheet-1",
            "name": "My Sheet",
            "state": AgenticTableSheetState.IDLE.value,
            "magicTableRowCount": 1,
            "chatId": "chat-1",
            "createdBy": "user-1",
            "companyId": COMPANY_ID,
            "createdAt": "2024-01-01T00:00:00Z",
        }
        batch = {
            "magicTableCells": [
                {
                    "sheetId": "sheet-1",
                    "rowOrder": 0,
                    "columnOrder": 0,
                    "rowLocked": False,
                    "text": "a",
                    "logEntries": [],
                },
            ]
        }
        cell_without_metadata = {
            "sheetId": "sheet-1",
            "rowOrder": 0,
            "columnOrder": 0,
            "rowLocked": False,
            "text": "a",
            "logEntries": [],
        }
        with (
            patch(
                "unique_toolkit.agentic_table.service.AgenticTable.get_sheet_data",
                new=AsyncMock(side_effect=[sheet_info, batch]),
            ),
            patch(
                "unique_toolkit.agentic_table.service.AgenticTable.get_cell",
                new=AsyncMock(return_value=cell_without_metadata),
            ),
        ):
            sheet = await service.get_sheet(include_row_metadata=True)

        assert sheet.magic_table_cells[0].row_metadata == []


class TestGetSheetMetadata:
    @pytest.mark.asyncio
    async def test_get_sheet_metadata(self, service: AgenticTableService):
        sheet_info = {
            "magicTableSheetMetadata": [
                {"id": "m1", "key": "a", "value": "1", "exactFilter": False},
                {"id": "m2", "key": "b", "value": "2", "exactFilter": True},
            ]
        }
        with patch(
            "unique_toolkit.agentic_table.service.AgenticTable.get_sheet_data",
            new=AsyncMock(return_value=sheet_info),
        ):
            result = await service.get_sheet_metadata()

        assert len(result) == 2
        assert result[0].key == "a"
        assert result[1].exact_filter is True


class TestSetCellMetadata:
    @pytest.mark.asyncio
    async def test_set_cell_metadata_success(self, service: AgenticTableService):
        with patch(
            "unique_toolkit.agentic_table.service.AgenticTable.set_cell_metadata",
            new=AsyncMock(return_value={"status": True, "message": "ok"}),
        ) as mock_set:
            await service.set_cell_metadata(
                row=0,
                column=0,
                selected=True,
                selection_method=SelectionMethod.MANUAL,
                agreement_status=AgreementStatus.AGREE,
            )

        kwargs = mock_set.await_args.kwargs
        assert kwargs["selected"] is True
        assert kwargs["selectionMethod"] == SelectionMethod.MANUAL
        assert kwargs["agreementStatus"] == AgreementStatus.AGREE

    @pytest.mark.asyncio
    async def test_set_cell_metadata_failure_raises(
        self, service: AgenticTableService
    ):
        with patch(
            "unique_toolkit.agentic_table.service.AgenticTable.set_cell_metadata",
            new=AsyncMock(return_value={"status": False, "message": "nope"}),
        ):
            with pytest.raises(Exception, match="nope"):
                await service.set_cell_metadata(row=0, column=0, selected=True)


class TestUpdateRowVerificationStatus:
    @pytest.mark.asyncio
    async def test_update_row_verification_status(
        self, service: AgenticTableService
    ):
        with patch(
            "unique_toolkit.agentic_table.service.AgenticTable.bulk_update_status",
            new=AsyncMock(return_value=None),
        ) as mock_bulk:
            await service.update_row_verification_status(
                row_orders=[1, 2, 3],
                status=RowVerificationStatus.VERIFIED,
            )

        mock_bulk.assert_awaited_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            tableId=TABLE_ID,
            rowOrders=[1, 2, 3],
            status=RowVerificationStatus.VERIFIED,
        )
