import asyncio
import logging
import time
from typing import Any, cast

from typing_extensions import deprecated
from unique_sdk import (
    AgenticTable,
    AgenticTableSheetState,
    AgreementStatus,
    CellRendererTypes,
    FilterTypes,
    MagicTableArtifactState,
    MagicTableArtifactType,
    RowVerificationStatus,
    SelectionMethod,
)
from unique_sdk import AgenticTableCell as SDKAgenticTableCell
from unique_sdk.api_resources._agentic_table import ActivityStatus

from .schemas import (
    CreatedMagicTableSheet,
    LogEntry,
    MagicTableAction,
    MagicTableArtifact,
    MagicTableCell,
    MagicTableSheet,
    RowMetadataEntry,
    SheetMetadataEntryInput,
)


def _sheet_batch_cells_include_row_metadata_from_api(
    cells: list[SDKAgenticTableCell],
) -> bool:
    """True when `get_sheet_data` already returned per-cell ``rowMetadata`` (UN-19884+).

    Used to skip N+1 ``get_cell`` hydration. If the batch is empty, there is nothing
    to hydrate, so we treat that as satisfied.

    When the gateway does not yet populate ``rowMetadata`` on sheet payloads, the
    first cell typically omits the key entirely — then callers fall back to
    ``get_cell`` per distinct row (legacy compat; removable after deprecation).
    """
    if not cells:
        return True
    first = cells[0]
    rm = first.get("rowMetadata")
    return "rowMetadata" in first and isinstance(rm, list)


class LockedAgenticTableError(Exception):
    pass


class AgenticTableRunNotStartedError(TimeoutError):
    """Raised by ``wait_for_run`` when the sheet never left IDLE within the start timeout."""


class AgenticTableRunTimeoutError(TimeoutError):
    """Raised by ``wait_for_run``/``wait_for_artifacts`` when the operation did not complete in time."""


class AgenticTableArtifactError(Exception):
    """Raised by ``wait_for_artifacts`` when an artifact ends up in the ERROR state."""


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
        self.created_sheet: CreatedMagicTableSheet | None = None

    @classmethod
    async def create_sheet(
        cls,
        user_id: str,
        company_id: str,
        assistant_id: str,
        name: str | None = None,
        due_at: str | None = None,
        logger: logging.Logger = logging.getLogger(__name__),
    ) -> "AgenticTableService":
        """Create a new Agentic Table sheet in a space and return a service bound to it.

        Args:
            user_id: The user creating the sheet (must have access to the space).
            company_id: The company id.
            assistant_id: The space (assistant) to create the sheet in.
            name: Optional sheet name.
            due_at: Optional due date (ISO 8601 string).

        Returns:
            AgenticTableService: A service bound to the new sheet. The full creation
            response (including ``due_diligence_id``) is available on ``created_sheet``.
        """
        params: dict[str, str] = {"assistantId": assistant_id}
        if name is not None:
            params["name"] = name
        if due_at is not None:
            params["dueAt"] = due_at
        # ``Unpack[CreateSheet]`` + dynamic keys: basedpyright cannot tie ``params`` to optional fields.
        created = await AgenticTable.create_sheet(
            user_id=user_id,
            company_id=company_id,
            **cast(Any, params),
        )
        sheet = CreatedMagicTableSheet.model_validate(created)
        service = cls(
            user_id=user_id,
            company_id=company_id,
            table_id=sheet.sheet_id,
            logger=logger,
        )
        service.created_sheet = sheet
        return service

    async def set_cell(
        self,
        row: int,
        column: int,
        text: str,
        log_entries: list[LogEntry] | None = None,
    ):
        """
        Sets the value of a cell in the Agentic Table.

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
        Gets the value of a cell in the Agentic Table.

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
            includeRowMetadata=include_row_metadata,
        )
        return MagicTableCell.model_validate(cell_data)

    async def set_multiple_cells(
        self, cells: list[MagicTableCell], batch_size: int = 4000
    ):
        """
        Sets the values of multiple cells in the Agentic Table.

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
            activity=activity.value,  # pyright: ignore[reportArgumentType]
            status=status.value,  # pyright: ignore[reportArgumentType]
            text=text,
        )

    async def register_agent(self) -> None:
        """
        Registers the agent for the Agentic Table by updating the sheet state to PROCESSING.

        Raises:
            LockedAgenticTableError: If the Agentic Table is busy.
        """
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
        """
        Deregisters the agent for the Agentic Table by updating the sheet state to IDLE.

        Raises:
            LockedAgenticTableError: If the Agentic Table is busy.
        """
        await AgenticTable.update_sheet_state(
            user_id=self._user_id,
            company_id=self._company_id,
            tableId=self.table_id,
            state=AgenticTableSheetState.IDLE,
        )

    async def set_artifact(
        self,
        artifact_type: MagicTableArtifactType,
        content_id: str,
        mime_type: str | None = None,
        name: str | None = None,
    ):
        """Upload/set report files to the Agentic Table.

        Args:
            artifact_type: The type of artifact to set (``MagicTableArtifactType`` / public API).
            content_id: The content ID of the artifact.
            mime_type: The MIME type of the artifact (optional on the wire; include when known).
            name: The display name of the artifact (optional on the wire; include when known).
        """
        extras: dict[str, str] = {}
        if mime_type is not None:
            extras["mimeType"] = mime_type
        if name is not None:
            extras["name"] = name
        # ``Unpack[SetArtifact]`` + dynamic keys: basedpyright cannot tie ``extras`` to optional fields.
        await AgenticTable.set_artifact(
            user_id=self._user_id,
            company_id=self._company_id,
            tableId=self.table_id,
            artifactType=artifact_type,
            contentId=content_id,
            **cast(Any, extras),
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
        Sets the style of a column in the Agentic Table.

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
        """
        Gets the number of rows in the Agentic Table.

        Returns:
            int: The number of rows in the Agentic Table.
        """
        sheet_info = await AgenticTable.get_sheet_data(
            user_id=self._user_id,
            company_id=self._company_id,
            tableId=self.table_id,
            includeRowCount=True,
            includeCells=False,
            includeLogHistory=False,
        )
        row_count = sheet_info.get("magicTableRowCount")
        if row_count is None:
            raise RuntimeError(
                "Expected magicTableRowCount in sheet response when includeRowCount=True"
            )
        return row_count

    async def get_sheet(
        self,
        start_row: int = 0,
        end_row: int | None = None,
        batch_size: int = 100,
        include_log_history: bool = False,
        include_cell_meta_data: bool = False,
        include_row_metadata: bool = False,
        scope_to_assigned_rows: bool = False,
    ) -> MagicTableSheet:
        """
        Gets the sheet data from the Agentic Table paginated by batch_size.

        Args:
            start_row (int): The start row (inclusive).
            end_row (int | None): The end row (not inclusive).
            batch_size (int): The batch size.
            include_log_history (bool): Whether to include the log history.
            include_cell_meta_data (bool): Whether to include the cell metadata (renderer, selection, agreement status).
            include_row_metadata (bool): Whether to include the row metadata (key value pairs).
            scope_to_assigned_rows (bool): When true, scope row count and cell batches to rows
                assigned to the current user (Can Answer role).
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
            scopeToAssignedRows=scope_to_assigned_rows,
        )
        total_rows = sheet_info.get("magicTableRowCount")
        if total_rows is None:
            raise RuntimeError(
                "Expected magicTableRowCount in sheet response when includeRowCount=True"
            )
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
            if include_row_metadata:
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
                    includeRowMetadata=True,
                    scopeToAssignedRows=scope_to_assigned_rows,
                )
            else:
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
                    scopeToAssignedRows=scope_to_assigned_rows,
                )
            if "magicTableCells" in sheet_partial:
                batch_cells = sheet_partial["magicTableCells"]
                if (
                    include_row_metadata
                    and not _sheet_batch_cells_include_row_metadata_from_api(
                        batch_cells
                    )
                ):
                    # Legacy: gateways before UN-19884 omit rowMetadata on sheet cells; hydrate
                    # via get_cell until all environments expose rowMetadata on GET sheet. This
                    # branch can be removed after an agreed deprecation window.
                    self.logger.debug(
                        "Magic table sheet cells lack rowMetadata; hydrating row metadata via get_cell."
                    )
                    row_metadata_map: dict[int, list[RowMetadataEntry]] = {}
                    for cell in batch_cells:
                        row_order = cell.get("rowOrder")  # type: ignore[assignment]
                        if row_order is not None and row_order not in row_metadata_map:  # pyright: ignore[reportUnnecessaryComparison]
                            column_order = cell.get("columnOrder")  # type: ignore[assignment]
                            cell_with_row_metadata = await self.get_cell(
                                row_order,
                                column_order,
                            )
                            if cell_with_row_metadata.row_metadata:
                                row_metadata_map[cell_with_row_metadata.row_order] = (
                                    cell_with_row_metadata.row_metadata
                                )
                                cell["rowMetadata"] = (  # pyright: ignore[reportGeneralTypeIssues]
                                    cell_with_row_metadata.row_metadata
                                )
                    for cell in batch_cells:
                        row_order = cell.get("rowOrder")  # type: ignore[assignment]
                        if row_order is not None and row_order in row_metadata_map:  # pyright: ignore[reportUnnecessaryComparison]
                            cell["rowMetadata"] = row_metadata_map[  # pyright: ignore[reportGeneralTypeIssues]
                                row_order
                            ]

                cells.extend(batch_cells)

        sheet_info["magicTableCells"] = cells
        return MagicTableSheet.model_validate(sheet_info)

    async def get_sheet_metadata(self) -> list[RowMetadataEntry]:
        """
        Gets the sheet metadata from the Agentic Table.

        Returns:
            list[RowMetadataEntry]: The sheet metadata.
        """
        sheet_info = await AgenticTable.get_sheet_data(
            user_id=self._user_id,
            company_id=self._company_id,
            tableId=self.table_id,
            includeSheetMetadata=True,
        )
        raw_metadata = sheet_info.get("magicTableSheetMetadata") or []
        return [RowMetadataEntry.model_validate(metadata) for metadata in raw_metadata]

    async def set_cell_metadata(
        self,
        row: int,
        column: int,
        selected: bool | None = None,
        selection_method: SelectionMethod | None = None,
        agreement_status: AgreementStatus | None = None,
    ) -> None:
        """
        Sets the cell metadata for the Agentic Table.
        NOTE: This is not to be confused with the sheet metadata and is associated rather with selection and agreement status, row locking etc.

        Args:
            row (int): The row index.
            column (int): The column index.
            selected (bool | None): Whether the cell is selected.
            selection_method (SelectionMethod | None): The method of selection.
            agreement_status (AgreementStatus | None): The agreement status.
        """
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
        if result["status"]:  # pyright: ignore[reportTypedDictNotRequiredAccess]
            return
        raise Exception(result["message"])  # pyright: ignore[reportTypedDictNotRequiredAccess]

    async def update_row_verification_status(
        self,
        row_orders: list[int],
        status: RowVerificationStatus,
        locked: bool | None = None,
    ):
        """Update the verification status of multiple rows at once.

        Args:
            row_orders: The row indexes to update.
            status: The verification status to set (``NEEDS_REVIEW``, etc.; matches public API).
            locked: When set, forwarded as ``locked`` on ``POST .../rows/bulk-update-status``.
        """
        if locked is None:
            await AgenticTable.bulk_update_status(
                user_id=self._user_id,
                company_id=self._company_id,
                tableId=self.table_id,
                rowOrders=row_orders,
                status=status,
            )
        else:
            await AgenticTable.bulk_update_status(
                user_id=self._user_id,
                company_id=self._company_id,
                tableId=self.table_id,
                rowOrders=row_orders,
                status=status,
                locked=locked,
            )

    async def import_questions_and_sources(
        self,
        question_file_ids: list[str] | None = None,
        question_texts: list[str] | None = None,
        source_file_ids: list[str] | None = None,
        context: str | None = None,
    ) -> None:
        """Import questions and source files into the sheet (`POST .../metadata`).

        Delta semantics: ids/texts already on the sheet are silently skipped. The
        agent run is only triggered when new questions (file ids or texts) are
        provided; adding only sources does not trigger a run. Rejected while the
        sheet is PROCESSING.

        Args:
            question_file_ids: Content ids of questionnaire files to import.
            question_texts: Question texts to import directly.
            source_file_ids: Content ids of source (knowledge) files to answer from.
            context: Optional free-text context passed to the agent.

        Raises:
            Exception: If the API reports a non-success status.
        """
        params: dict[str, Any] = {}
        if question_file_ids is not None:
            params["questionFileIds"] = question_file_ids
        if question_texts is not None:
            params["questionTexts"] = question_texts
        if source_file_ids is not None:
            params["sourceFileIds"] = source_file_ids
        if context is not None:
            params["context"] = context
        result = await AgenticTable.add_metadata(
            user_id=self._user_id,
            company_id=self._company_id,
            tableId=self.table_id,
            **cast(Any, params),
        )
        if not result.get("status"):
            raise Exception(result.get("message") or "Failed to import metadata")

    async def generate_artifacts(
        self,
        artifact_types: list[MagicTableArtifactType],
    ) -> None:
        """Trigger export generation (`POST .../generate-artifact`).

        Generation is asynchronous: this only initiates it. Use ``wait_for_artifacts``
        (or poll ``list_artifacts``) to detect completion, then download the artifact's
        ``content_id`` via the Content API.

        Raises:
            Exception: If the API reports a non-success status.
        """
        result = await AgenticTable.generate_artifact(
            user_id=self._user_id,
            company_id=self._company_id,
            tableId=self.table_id,
            artifactTypes=artifact_types,
        )
        if not result.get("status"):
            raise Exception(
                result.get("message") or "Failed to trigger artifact generation"
            )

    async def list_artifacts(self) -> list[MagicTableArtifact]:
        """List export artifacts of the sheet (`GET .../artifacts`)."""
        artifacts = await AgenticTable.list_artifacts(
            user_id=self._user_id,
            company_id=self._company_id,
            tableId=self.table_id,
        )
        return [MagicTableArtifact.model_validate(artifact) for artifact in artifacts]

    async def create_sheet_metadata(
        self,
        entries: list[SheetMetadataEntryInput],
    ) -> None:
        """Create sheet metadata entries (key/value pairs) on the sheet.

        Raises:
            Exception: If the API reports a non-success status.
        """
        result = await AgenticTable.create_sheet_metadata(
            user_id=self._user_id,
            company_id=self._company_id,
            tableId=self.table_id,
            entries=[
                cast(
                    Any,
                    entry.model_dump(by_alias=True, exclude_none=True),
                )
                for entry in entries
            ],
        )
        if not result.get("status"):
            raise Exception(result.get("message") or "Failed to create sheet metadata")

    async def delete_sheet_metadata(self, metadata_id: str) -> None:
        """Delete a sheet metadata entry by its id.

        Raises:
            Exception: If the API reports a non-success status.
        """
        result = await AgenticTable.delete_sheet_metadata(
            user_id=self._user_id,
            company_id=self._company_id,
            tableId=self.table_id,
            metadataId=metadata_id,
        )
        if not result.get("status"):
            raise Exception(result.get("message") or "Failed to delete sheet metadata")

    async def wait_for_run(
        self,
        start_timeout: float = 120.0,
        completion_timeout: float = 3600.0,
        poll_interval: float = 5.0,
    ) -> AgenticTableSheetState:
        """Wait for an agent run to start and complete, by polling the sheet state.

        Two-phase poll:
        1. Wait until the sheet enters PROCESSING (the agent picked up the trigger).
           Terminal state left over from an earlier run is not treated as a new
           run. If PROCESSING is never observed within ``start_timeout``, raise
           ``AgenticTableRunNotStartedError`` — most likely the trigger did not
           start a run (e.g. no new questions were imported).
        2. Wait until the sheet returns to IDLE or STOPPED_BY_USER (the run
           finished), up to ``completion_timeout``.

        Because the API exposes only the current state, a complete
        PROCESSING-to-IDLE transition between two polls cannot be observed.
        Keep ``poll_interval`` shorter than the expected minimum run duration.

        Args:
            start_timeout: Max seconds to wait for the run to start (phase 1).
            completion_timeout: Max seconds to wait for the run to finish (phase 2).
            poll_interval: Seconds between state polls.

        Returns:
            AgenticTableSheetState: The terminal state (IDLE or STOPPED_BY_USER).

        Raises:
            AgenticTableRunNotStartedError: The sheet never entered PROCESSING in phase 1.
            AgenticTableRunTimeoutError: The run did not finish within ``completion_timeout``.
        """
        deadline = time.monotonic() + start_timeout
        while True:
            state = await AgenticTable.get_sheet_state(
                user_id=self._user_id,
                company_id=self._company_id,
                tableId=self.table_id,
            )
            if state == AgenticTableSheetState.PROCESSING:
                break
            if time.monotonic() >= deadline:
                raise AgenticTableRunNotStartedError(
                    f"Sheet {self.table_id} never entered PROCESSING within {start_timeout}s. "
                    "Did the trigger start a run (e.g. were new questions imported)?"
                )
            await asyncio.sleep(poll_interval)

        self.logger.debug("Sheet %s run started (state=%s)", self.table_id, state)

        deadline = time.monotonic() + completion_timeout
        while state == AgenticTableSheetState.PROCESSING:
            if time.monotonic() >= deadline:
                raise AgenticTableRunTimeoutError(
                    f"Sheet {self.table_id} still PROCESSING after {completion_timeout}s."
                )
            await asyncio.sleep(poll_interval)
            state = await AgenticTable.get_sheet_state(
                user_id=self._user_id,
                company_id=self._company_id,
                tableId=self.table_id,
            )

        self.logger.debug("Sheet %s run finished (state=%s)", self.table_id, state)
        return state

    async def wait_for_artifacts(
        self,
        artifact_types: list[MagicTableArtifactType],
        timeout: float = 600.0,
        poll_interval: float = 5.0,
    ) -> list[MagicTableArtifact]:
        """Wait until artifacts of the given types are DONE, by polling ``list_artifacts``.

        Artifact records are upserted per type: triggering an export flips the record
        of that type to IN_PROGRESS and back to DONE when the file is ready. A
        terminal state is accepted only after IN_PROGRESS has been observed for
        that artifact type, so a result left over from an earlier generation is
        not mistaken for the newly triggered one.

        Because the API exposes only the current artifact state, a complete
        IN_PROGRESS-to-terminal transition between two polls cannot be observed.
        Keep ``poll_interval`` shorter than the expected minimum generation time.

        Args:
            artifact_types: The artifact types to wait for (as passed to ``generate_artifacts``).
            timeout: Max seconds to wait for all requested artifacts to be DONE.
            poll_interval: Seconds between polls.

        Returns:
            list[MagicTableArtifact]: The DONE artifacts, one per requested type.

        Raises:
            AgenticTableArtifactError: An artifact of a requested type is in the ERROR state.
            AgenticTableRunTimeoutError: Not all artifacts were DONE within ``timeout``.
        """
        wanted = set(artifact_types)
        started: set[MagicTableArtifactType] = set()
        deadline = time.monotonic() + timeout
        while True:
            artifacts = await self.list_artifacts()
            current = {
                a.artifact_type: a for a in artifacts if a.artifact_type in wanted
            }
            started.update(
                artifact_type
                for artifact_type, artifact in current.items()
                if artifact.artifact_state == MagicTableArtifactState.IN_PROGRESS
            )
            failed = [
                artifact
                for artifact_type, artifact in current.items()
                if artifact_type in started
                and artifact.artifact_state == MagicTableArtifactState.ERROR
            ]
            if failed:
                raise AgenticTableArtifactError(
                    f"Artifact generation failed for {[a.artifact_type for a in failed]} "
                    f"on sheet {self.table_id}."
                )
            done = {
                artifact_type: artifact
                for artifact_type, artifact in current.items()
                if artifact_type in started
                and artifact.artifact_state == MagicTableArtifactState.DONE
            }
            if wanted <= set(done.keys()):
                return [done[t] for t in artifact_types]
            if time.monotonic() >= deadline:
                missing = sorted(t.value for t in wanted - set(done.keys()))
                raise AgenticTableRunTimeoutError(
                    f"Artifacts {missing} not DONE within {timeout}s on sheet {self.table_id}."
                )
            await asyncio.sleep(poll_interval)
