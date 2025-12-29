import logging

from typing_extensions import deprecated
from unique_sdk import (
    AgenticTable,
    AgenticTableSheetState,
    AgreementStatus,
    CellRendererTypes,
    FilterTypes,
    RowVerificationStatus,
    SelectionMethod,
)
from unique_sdk import AgenticTableCell as SDKAgenticTableCell
from unique_sdk.api_resources._agentic_table import ActivityStatus

from .schemas import (
    ArtifactType,
    LogEntry,
    MagicTableAction,
    MagicTableCell,
    MagicTableSheet,
    RowMetadataEntry,
)


class LockedAgenticTableError(Exception):
    pass


class AgenticTableService:
    """
    Provides methods to interact with the Agentic Table.

    Attributes:
        #event (ChatEvent): The ChatEvent object.
        logger (Optional[logging.Logger]): The logger object. Defaults to None.
    """

    def __init__(
        self,
        user_id: str,
        company_id: str,
        table_id: str,
        event_id: str | None = None,
        logger: logging.Logger = logging.getLogger(__name__),
    ):
        self._event_id = event_id
        self._user_id = user_id
        self._company_id = company_id
        self.table_id = table_id
        self.logger = logger

    async def set_cell(
        self,
        row: int,
        column: int,
        text: str,
        log_entries: list[LogEntry] | None = None,
    ):
        """
        Sets the value of a cell in the Magic Table.

        Args:
            row (int): The row index.
            column (int): The column index.
            text (str): The text to set.
            log_entries (Optional[list[LogEntry]]): The log entries to set.
        """
        if log_entries is None:
            log_entries_new = []
        else:
            log_entries_new = [
                log_entry.to_sdk_log_entry() for log_entry in log_entries
            ]
        try:
            await AgenticTable.set_cell(
                user_id=self._user_id,
                company_id=self._company_id,
                tableId=self.table_id,
                rowOrder=row,
                columnOrder=column,
                text=text,
                logEntries=log_entries_new,
            )
        except Exception as e:
            self.logger.error(f"Error setting cell {row}, {column}: {e}.")

    async def get_cell(
        self, row: int, column: int, include_row_metadata: bool = True
    ) -> MagicTableCell:
        """
        Gets the value of a cell in the Magic Table.

        Args:
            row (int): The row index.
            column (int): The column index.
            include_row_metadata (bool): Whether to include the row metadata. Defaults to True.

        Returns:
            MagicTableCell: The MagicTableCell object.

        """
        cell_data = await AgenticTable.get_cell(
            user_id=self._user_id,
            company_id=self._company_id,
            tableId=self.table_id,
            rowOrder=row,
            columnOrder=column,
            includeRowMetadata=include_row_metadata,  # type: ignore[arg-type]
        )
        return MagicTableCell.model_validate(cell_data)

    async def set_multiple_cells(
        self, cells: list[MagicTableCell], batch_size: int = 4000
    ):
        """
        Sets the values of multiple cells in the Magic Table.

        Args:
            cells (list[MagicTableCell]): The cells to set sorted by row and column.
            batch_size (int): Number of cells to set in a single request.
        """
        for i in range(0, len(cells), batch_size):
            batch = cells[i : i + batch_size]
            await AgenticTable.set_multiple_cells(
                user_id=self._user_id,
                company_id=self._company_id,
                tableId=self.table_id,
                cells=[
                    SDKAgenticTableCell(
                        rowOrder=cell.row_order,
                        columnOrder=cell.column_order,
                        text=cell.text,
                    )
                    for cell in batch
                ],
            )

    async def set_activity(
        self,
        text: str,
        activity: MagicTableAction,
        status: ActivityStatus = ActivityStatus.IN_PROGRESS,
    ):
        """
        Sets the activity of the Agentic Table.

        Args:
            activity (str): The activity to set.
        """
        await AgenticTable.set_activity(
            user_id=self._user_id,
            company_id=self._company_id,
            tableId=self.table_id,
            activity=activity.value,  # type: ignore[arg-type]
            status=status.value,  # type: ignore[arg-type]
            text=text,
        )

    async def register_agent(self) -> None:
        state = await AgenticTable.get_sheet_state(
            user_id=self._user_id,
            company_id=self._company_id,
            tableId=self.table_id,
        )
        if state == AgenticTableSheetState.IDLE:
            await AgenticTable.update_sheet_state(
                user_id=self._user_id,
                company_id=self._company_id,
                tableId=self.table_id,
                state=AgenticTableSheetState.PROCESSING,
            )
            return
        # If the sheet is not idle, we cannot register the agent
        raise LockedAgenticTableError(
            f"Agentic Table is busy. Cannot register agent {self._event_id or self.table_id}."
        )

    async def deregister_agent(self):
        await AgenticTable.update_sheet_state(
            user_id=self._user_id,
            company_id=self._company_id,
            tableId=self.table_id,
            state=AgenticTableSheetState.IDLE,
        )

    async def set_artifact(
        self,
        artifact_type: ArtifactType,
        content_id: str,
        mime_type: str,
        name: str,
    ):
        await AgenticTable.set_artifact(
            user_id=self._user_id,
            company_id=self._company_id,
            tableId=self.table_id,
            artifactType=artifact_type.value,
            contentId=content_id,
            mimeType=mime_type,
            name=name,
        )

    @deprecated("Use set_column_style instead.")
    async def set_column_width(self, column: int, width: int):
        await self.set_column_style(column=column, width=width)

    async def set_column_style(
        self,
        column: int,
        width: int | None = None,
        cell_renderer: CellRendererTypes | None = None,
        filter: FilterTypes | None = None,
        editable: bool | None = None,
    ):
        """
        Sets the style of a column in the Magic Table.

        Args:
            column (int): The column index.
            width (int | None, optional): The width of the column. Defaults to None.
            cell_renderer (CellRenderer | None, optional): The cell renderer of the column. Defaults to None.
            filter (FilterComponents | None, optional): The filter of the column. Defaults to None.
            editable (bool | None, optional): Whether the column is editable. Defaults to None.

        Raises:
            Exception: If the column style is not set.
        """
        # Convert the input to the correct format
        params = {}
        if width is not None:
            params["columnWidth"] = width
        if cell_renderer is not None:
            params["cellRenderer"] = cell_renderer.value
        if filter is not None:
            params["filter"] = filter.value
        if editable is not None:
            params["editable"] = editable
        status, message = await AgenticTable.set_column_metadata(
            user_id=self._user_id,
            company_id=self._company_id,
            tableId=self.table_id,
            columnOrder=column,
            **params,
        )
        if status:
            return
        raise Exception(message)

    async def get_num_rows(self) -> int:
        sheet_info = await AgenticTable.get_sheet_data(
            user_id=self._user_id,
            company_id=self._company_id,
            tableId=self.table_id,
            includeRowCount=True,
            includeCells=False,
            includeLogHistory=False,
        )
        return sheet_info["magicTableRowCount"]

    async def get_sheet(
        self,
        start_row: int = 0,
        end_row: int | None = None,
        batch_size: int = 100,
        include_log_history: bool = False,
        include_cell_meta_data: bool = False,
        include_row_metadata: bool = False,
    ) -> MagicTableSheet:
        """
        Gets the sheet data from the Magic Table paginated by batch_size.

        Args:
            start_row (int): The start row (inclusive).
            end_row (int | None): The end row (not inclusive).
            batch_size (int): The batch size.
            include_log_history (bool): Whether to include the log history.
            include_cell_meta_data (bool): Whether to include the cell metadata (renderer, selection, agreement status).
            include_row_metadata (bool): Whether to include the row metadata (key value pairs).
        Returns:
            MagicTableSheet: The sheet data.
        """
        # Find the total number of rows
        sheet_info = await AgenticTable.get_sheet_data(
            user_id=self._user_id,
            company_id=self._company_id,
            tableId=self.table_id,
            includeRowCount=True,
            includeCells=False,
            includeLogHistory=False,
            includeCellMetaData=False,
        )
        total_rows = sheet_info["magicTableRowCount"]
        if end_row is None or end_row > total_rows:
            end_row = total_rows
        if start_row > end_row:
            raise Exception("Start row is greater than end row")
        if start_row < 0 or end_row < 0:
            raise Exception("Start row or end row is negative")

        # Get the cells
        cells = []
        for row in range(start_row, end_row, batch_size):
            end_row_batch = min(row + batch_size, end_row)
            sheet_partial = await AgenticTable.get_sheet_data(
                user_id=self._user_id,
                company_id=self._company_id,
                tableId=self.table_id,
                includeCells=True,
                includeLogHistory=include_log_history,
                includeRowCount=False,
                includeCellMetaData=include_cell_meta_data,  # renderer, selection, agreement status
                startRow=row,
                endRow=end_row_batch - 1,
            )
            if "magicTableCells" in sheet_partial:
                if include_row_metadata:
                    # If include_row_metadata is true, we need to get the row metadata for each cell.
                    row_metadata_map = {}
                    # TODO: @thea-unique This routine is not efficient and would be nice if we had this data passed on in get_sheet_data.
                    for cell in sheet_partial["magicTableCells"]:
                        row_order = cell.get("rowOrder")  # type: ignore[assignment]
                        if row_order is not None and row_order not in row_metadata_map:
                            column_order = cell.get("columnOrder")  # type: ignore[assignment]
                            self.logger.info(
                                f"Getting row metadata for cell {row_order}, {column_order}"
                            )
                            cell_with_row_metadata = await self.get_cell(
                                row_order,
                                column_order,  # type: ignore[arg-type]
                            )
                            if cell_with_row_metadata.row_metadata:
                                print(cell_with_row_metadata.row_metadata)
                                row_metadata_map[cell_with_row_metadata.row_order] = (
                                    cell_with_row_metadata.row_metadata
                                )
                                cell["rowMetadata"] = (  # type: ignore[assignment]
                                    cell_with_row_metadata.row_metadata
                                )
                    # Assign row_metadata to all cells
                    for cell in sheet_partial["magicTableCells"]:
                        row_order = cell.get("rowOrder")  # type: ignore[assignment]
                        if row_order is not None and row_order in row_metadata_map:
                            cell["rowMetadata"] = row_metadata_map[  # type: ignore[assignment]
                                row_order
                            ]

                cells.extend(sheet_partial["magicTableCells"])

        sheet_info["magicTableCells"] = cells
        return MagicTableSheet.model_validate(sheet_info)

    async def get_sheet_metadata(self) -> list[RowMetadataEntry]:
        sheet_info = await AgenticTable.get_sheet_data(
            user_id=self._user_id,
            company_id=self._company_id,
            tableId=self.table_id,
            includeSheetMetadata=True,  # type: ignore[arg-type]
        )
        return [
            RowMetadataEntry.model_validate(metadata)
            for metadata in sheet_info["magicTableSheetMetadata"]
        ]

    async def set_cell_metadata(
        self,
        row: int,
        column: int,
        selected: bool | None = None,
        selection_method: SelectionMethod | None = None,
        agreement_status: AgreementStatus | None = None,
    ) -> None:
        params = {}
        if selected is not None:
            params["selected"] = selected
        if selection_method is not None:
            params["selectionMethod"] = selection_method
        if agreement_status is not None:
            params["agreementStatus"] = agreement_status
        result = await AgenticTable.set_cell_metadata(
            user_id=self._user_id,
            company_id=self._company_id,
            tableId=self.table_id,
            rowOrder=row,
            columnOrder=column,
            **params,
        )
        if result["status"]:  # type: ignore
            return
        raise Exception(result["message"])  # type: ignore

    async def update_row_verification_status(
        self,
        row_orders: list[int],
        status: RowVerificationStatus,
    ):
        await AgenticTable.bulk_update_status(
            user_id=self._user_id,
            company_id=self._company_id,
            tableId=self.table_id,
            rowOrders=row_orders,
            status=status,
        )
