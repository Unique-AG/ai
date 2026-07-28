from enum import StrEnum
from typing import (
    Any,
    Literal,
    NotRequired,
    TypedDict,
    cast,
)

from typing_extensions import Unpack

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class AgenticTableSheetState(StrEnum):
    STOPPED_BY_USER = "STOPPED_BY_USER"
    PROCESSING = "PROCESSING"
    IDLE = "IDLE"


class LogDetail(TypedDict, total=False):
    llmRequest: list[dict[str, Any]] | None


class LogEntry(TypedDict):
    text: str
    createdAt: str
    actorType: Literal["USER", "SYSTEM", "ASSISTANT", "TOOL"]
    messageId: NotRequired[str]
    details: NotRequired[LogDetail]


class FilterTypes(StrEnum):
    VALUE_MATCH_FILTER = "ValueMatchFilter"
    PARTIAL_MATCH_FILTER = "PartialMatchFilter"
    REFERENCE_FILTER = "ReferenceFilter"
    HALLUCINATION_FILTER = "HallucinationFilter"
    REVIEW_STATUS_FILTER = "ReviewStatusFilter"
    ASSIGNEE_FILTER = "AssigneeFilter"


class CellRendererTypes(StrEnum):
    CHECKBOX_LOCK_CELL_RENDERER = "CheckboxLockCellRenderer"
    COLLABORATOR_DROPDOWN = "CollaboratorDropdown"
    REVIEW_STATUS_DROPDOWN = "ReviewStatusDropdown"
    CUSTOM_CELL_RENDERER = "CustomCellRenderer"
    SELECTABLE_CELL_RENDERER = "SelectableCellRenderer"


class MagicTableAction(StrEnum):
    """Workflow action strings for `POST /magic-table/{tableId}/activity` (matches `MagicTableAgenticWorkflowAction`)."""

    DELETE_ROW = "DeleteRow"
    DELETE_COLUMN = "DeleteColumn"
    INSERT_ROW = "InsertRow"
    UPDATE_CELL = "UpdateCell"
    ADD_QUESTION_TEXT = "AddQuestionText"
    ADD_META_DATA = "AddMetaData"
    GENERATE_ARTIFACT = "GenerateArtifact"
    SHEET_COMPLETED = "SheetCompleted"
    LIBRARY_SHEET_ROW_VERIFIED = "LibrarySheetRowVerified"
    SHEET_CREATED = "SheetCreated"
    GENERATE_OVERVIEW = "GenerateOverview"
    RERUN_ROW = "RerunRow"


class ActivityStatus(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SheetType(StrEnum):
    DEFAULT = "DEFAULT"
    LIBRARY = "LIBRARY"


class SelectionMethod(StrEnum):
    DEFAULT = "DEFAULT"
    MANUAL = "MANUAL"


class AgreementStatus(StrEnum):
    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"


class RowVerificationStatus(StrEnum):
    """Row verification status for `POST .../rows/bulk-update-status` (matches `MagicTableRowStatus`)."""

    NEEDS_REVIEW = "NEEDS_REVIEW"
    READY_FOR_VERIFICATION = "READY_FOR_VERIFICATION"
    VERIFIED = "VERIFIED"


class MagicTableArtifactType(StrEnum):
    """Artifact type for `POST /magic-table/{tableId}/artifact` (matches `MagicTableArtifactType`)."""

    QUESTIONS = "QUESTIONS"
    FULL_REPORT = "FULL_REPORT"
    AGENTIC_REPORT = "AGENTIC_REPORT"


class MagicTableArtifactState(StrEnum):
    """Artifact generation state (matches `MagicTableArtifactState`)."""

    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    ERROR = "ERROR"


class MagicTableMetadataEntry(TypedDict, total=False):
    """Row or sheet metadata entry as returned by the public magic-table API."""

    id: str
    key: str
    value: str
    exactFilter: bool


class AgenticTableCellMetaData(TypedDict, total=False):
    """Per-cell metadata object (`metaData` on `AgenticTableCell`) when `includeCellMetaData` is used."""

    selected: bool
    selectionMethod: SelectionMethod
    agreementStatus: AgreementStatus
    rowOrder: int
    columnOrder: int


class _AgenticTableCellRequired(TypedDict):
    rowOrder: int
    columnOrder: int
    text: str


class AgenticTableCell(_AgenticTableCellRequired, total=False):
    sheetId: str
    rowLocked: bool
    logEntries: list[LogEntry] | None
    metaData: AgenticTableCellMetaData
    rowMetadata: list[MagicTableMetadataEntry]


class ColumnMetadataUpdateStatus(TypedDict, total=False):
    status: bool
    message: str | None


class MagicTableActivityResponse(TypedDict):
    """Response body from `POST /magic-table/{tableId}/activity` (publish activity)."""

    status: bool


class MagicTableActionResult(TypedDict, total=False):
    """Generic `{status, message?}` response from lifecycle mutations (import, generate-artifact, sheet metadata writes)."""

    status: bool
    message: str | None


class _CreatedAgenticTableSheetRequired(TypedDict):
    sheetId: str
    dueDiligenceId: str
    name: str
    state: AgenticTableSheetState
    createdBy: str
    companyId: str
    createdAt: str


class CreatedAgenticTableSheet(_CreatedAgenticTableSheetRequired, total=False):
    """Response body from `POST /magic-table` (create sheet)."""

    chatId: str | None
    dueAt: str | None


class MagicTableArtifact(TypedDict, total=False):
    """Artifact entry from `GET /magic-table/{tableId}/artifacts`.

    ``contentId`` is only present once ``artifactState`` is ``DONE``; download the
    file via the Content API.
    """

    id: str
    name: str | None
    contentId: str | None
    mimeType: str | None
    artifactType: MagicTableArtifactType
    artifactState: MagicTableArtifactState
    createdAt: str
    updatedAt: str


class MagicTableArtifactList(TypedDict):
    """List envelope returned by `GET /magic-table/{tableId}/artifacts` (`{object: "list", data: [...]}`)."""

    object: Literal["list"]
    data: list[MagicTableArtifact]


class _AgenticTableSheetRequired(TypedDict):
    sheetId: str
    name: str
    state: AgenticTableSheetState
    createdBy: str
    companyId: str
    createdAt: str


class AgenticTableSheet(_AgenticTableSheetRequired, total=False):
    chatId: str
    magicTableRowCount: int
    magicTableCells: list[AgenticTableCell]
    magicTableSheetMetadata: list[MagicTableMetadataEntry]


class AgenticTable(APIResource["AgenticTable"]):
    """
    This object represents the magic table route. It is used to run complex APIs on the Unique platform
    """

    class SetCell(RequestOptions):
        tableId: str
        rowOrder: int
        columnOrder: int
        text: str
        logEntries: NotRequired[list[LogEntry]]

    class GetCell(RequestOptions):
        tableId: str
        rowOrder: int
        columnOrder: int
        includeRowMetadata: NotRequired[bool]

    class SetActivityStatus(RequestOptions):
        tableId: str
        activity: MagicTableAction
        status: ActivityStatus
        text: str

    class SetArtifact(RequestOptions):
        tableId: str
        contentId: str
        artifactType: MagicTableArtifactType
        name: NotRequired[str]
        mimeType: NotRequired[str]

    class UpdateSheet(RequestOptions):
        tableId: str
        state: NotRequired[AgenticTableSheetState]
        name: NotRequired[str]

    class UpdateSheetResponse(RequestOptions):
        status: bool
        message: str

    class SetColumnMetadata(RequestOptions):
        tableId: str
        columnOrder: int
        columnWidth: NotRequired[int]
        filter: NotRequired[FilterTypes]
        cellRenderer: NotRequired[str]
        editable: NotRequired[bool]

    class GetSheetData(RequestOptions):
        """Query params for `GET /magic-table/{tableId}` (public `2023-12-06`)."""

        tableId: str
        includeCells: NotRequired[bool]
        includeLogHistory: NotRequired[bool]
        includeRowCount: NotRequired[bool]
        includeCellMetaData: NotRequired[bool]
        includeSheetMetadata: NotRequired[bool]
        includeRowMetadata: NotRequired[bool]
        scopeToAssignedRows: NotRequired[bool]
        startRow: NotRequired[int]
        endRow: NotRequired[int]

    class SetCellMetadata(RequestOptions):
        tableId: str
        rowOrder: int
        columnOrder: int
        selected: NotRequired[bool]
        selectionMethod: NotRequired[SelectionMethod]
        agreementStatus: NotRequired[AgreementStatus]

    class BulkUpdateStatus(RequestOptions):
        tableId: str
        rowOrders: list[int]
        status: RowVerificationStatus
        locked: NotRequired[bool]

    class CreateSheet(RequestOptions):
        """Body for `POST /magic-table` (create a new sheet in a space)."""

        assistantId: str
        name: NotRequired[str]
        dueAt: NotRequired[str]

    class AddMetaData(RequestOptions):
        """Body for `POST /magic-table/{tableId}/metadata` (import questions/sources).

        Delta semantics: ids/texts already on the sheet are silently skipped. The
        agent run is only triggered when new questions (file ids or texts) are
        provided; adding only sources does not trigger a run.
        """

        tableId: str
        questionFileIds: NotRequired[list[str]]
        questionTexts: NotRequired[list[str]]
        sourceFileIds: NotRequired[list[str]]
        context: NotRequired[str]

    class GenerateArtifact(RequestOptions):
        """Body for `POST /magic-table/{tableId}/generate-artifact` (trigger export)."""

        tableId: str
        artifactTypes: list[MagicTableArtifactType]

    class CreateSheetMetadata(RequestOptions):
        """Body for `POST /magic-table/{tableId}/sheet/metadata` (create sheet metadata entries)."""

        tableId: str
        entries: list[MagicTableMetadataEntry]

    @classmethod
    async def set_cell(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["AgenticTable.SetCell"],
    ) -> "AgenticTableCell":
        """ """
        url = f"/magic-table/{params['tableId']}/cell"
        return cast(
            "AgenticTableCell",
            await cls._static_request_async(
                "post",
                url,
                user_id,
                company_id,
                params,
            ),
        )

    @classmethod
    async def get_cell(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["AgenticTable.GetCell"],
    ) -> "AgenticTableCell":
        """ """
        url = f"/magic-table/{params['tableId']}/cell?rowOrder={params['rowOrder']}&columnOrder={params['columnOrder']}"
        params.pop("tableId")
        params.pop("rowOrder")
        params.pop("columnOrder")
        return cast(
            "AgenticTableCell",
            await cls._static_request_async(
                "get",
                url,
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def set_activity(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["AgenticTable.SetActivityStatus"],
    ) -> MagicTableActivityResponse:
        url = f"/magic-table/{params['tableId']}/activity"
        return cast(
            MagicTableActivityResponse,
            await cls._static_request_async(
                "post",
                url,
                user_id,
                company_id,
                params,
            ),
        )

    @classmethod
    async def set_artifact(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["AgenticTable.SetArtifact"],
    ) -> ColumnMetadataUpdateStatus:
        url = f"/magic-table/{params['tableId']}/artifact"
        return cast(
            ColumnMetadataUpdateStatus,
            await cls._static_request_async(
                "post",
                url,
                user_id,
                company_id,
                params,
            ),
        )

    @classmethod
    async def update_sheet_state(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["AgenticTable.UpdateSheet"],
    ) -> "AgenticTable.UpdateSheetResponse":
        url = f"/magic-table/{params['tableId']}"
        return cast(
            "AgenticTable.UpdateSheetResponse",
            await cls._static_request_async("post", url, user_id, company_id, params),
        )

    @classmethod
    async def set_column_metadata(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["AgenticTable.SetColumnMetadata"],
    ) -> ColumnMetadataUpdateStatus:
        url = f"/magic-table/{params['tableId']}/column/metadata"
        # Remove tableId from params
        params.pop("tableId")
        response = await cls._static_request_async(
            "post", url, user_id, company_id, params
        )
        return cast(
            ColumnMetadataUpdateStatus,
            response,
        )

    @classmethod
    async def get_sheet_data(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["AgenticTable.GetSheetData"],
    ) -> AgenticTableSheet:
        url = f"/magic-table/{params['tableId']}"
        return cast(
            AgenticTableSheet,
            await cls._static_request_async("get", url, user_id, company_id, params),
        )

    @classmethod
    async def get_sheet_state(
        cls, user_id: str, company_id: str, tableId: str
    ) -> AgenticTableSheetState:
        sheet = await cls.get_sheet_data(
            user_id=user_id,
            company_id=company_id,
            tableId=tableId,
            includeCells=False,
        )
        return sheet["state"]

    @classmethod
    async def set_cell_metadata(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["AgenticTable.SetCellMetadata"],
    ) -> ColumnMetadataUpdateStatus:
        url = f"/magic-table/{params['tableId']}/cell/metadata"
        return cast(
            "ColumnMetadataUpdateStatus",
            await cls._static_request_async("post", url, user_id, company_id, params),
        )

    @classmethod
    async def set_multiple_cells(
        cls,
        user_id: str,
        company_id: str,
        tableId: str,
        cells: list[AgenticTableCell],
    ) -> ColumnMetadataUpdateStatus:
        url = f"/magic-table/{tableId}/cells/bulk-upsert"
        try:
            params_api = {
                "cells": [
                    {
                        "rowOrder": cell["rowOrder"],
                        "columnOrder": cell["columnOrder"],
                        "data": cell["text"],
                    }
                    for cell in cells
                ]
            }
        except Exception as e:
            raise ValueError(f"Invalid data or missing required fields: {e}")
        return cast(
            "ColumnMetadataUpdateStatus",
            await cls._static_request_async(
                "post", url, user_id, company_id, params=params_api
            ),
        )

    @classmethod
    async def bulk_update_status(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["AgenticTable.BulkUpdateStatus"],
    ) -> ColumnMetadataUpdateStatus:
        url = f"/magic-table/{params['tableId']}/rows/bulk-update-status"
        return cast(
            "ColumnMetadataUpdateStatus",
            await cls._static_request_async(
                "post",
                url,
                user_id,
                company_id,
                params,
            ),
        )

    @classmethod
    async def create_sheet(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["AgenticTable.CreateSheet"],
    ) -> CreatedAgenticTableSheet:
        """Create a new Agentic Table sheet in a space (`POST /magic-table`).

        The caller must have access to the space (``assistantId``). The response
        includes ``sheetId`` (use it as ``tableId`` for all subsequent calls) and
        ``dueDiligenceId``.
        """
        return cast(
            CreatedAgenticTableSheet,
            await cls._static_request_async(
                "post",
                "/magic-table",
                user_id,
                company_id,
                params,
            ),
        )

    @classmethod
    async def add_metadata(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["AgenticTable.AddMetaData"],
    ) -> MagicTableActionResult:
        """Import question files/texts and source files (`POST /magic-table/{tableId}/metadata`).

        Triggers the agent when new questions are included. Rejected with 422 while
        the sheet is ``PROCESSING``.
        """
        url = f"/magic-table/{params['tableId']}/metadata"
        params.pop("tableId")
        return cast(
            MagicTableActionResult,
            await cls._static_request_async(
                "post",
                url,
                user_id,
                company_id,
                params,
            ),
        )

    @classmethod
    async def generate_artifact(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["AgenticTable.GenerateArtifact"],
    ) -> MagicTableActionResult:
        """Trigger export generation (`POST /magic-table/{tableId}/generate-artifact`).

        Generation is asynchronous: poll `list_artifacts` until the artifact of the
        requested type reaches state ``DONE``, then download its ``contentId`` via
        the Content API.
        """
        url = f"/magic-table/{params['tableId']}/generate-artifact"
        params.pop("tableId")
        return cast(
            MagicTableActionResult,
            await cls._static_request_async(
                "post",
                url,
                user_id,
                company_id,
                params,
            ),
        )

    @classmethod
    async def list_artifacts(
        cls,
        user_id: str,
        company_id: str,
        tableId: str,
    ) -> list[MagicTableArtifact]:
        """List export artifacts of a sheet (`GET /magic-table/{tableId}/artifacts`).

        The route responds with a ``{object: "list", data: [...]}`` envelope; this
        method unwraps it and returns the artifact entries.
        """
        url = f"/magic-table/{tableId}/artifacts"
        response = cast(
            MagicTableArtifactList,
            await cls._static_request_async(
                "get",
                url,
                user_id,
                company_id,
            ),
        )
        return response["data"]

    @classmethod
    async def create_sheet_metadata(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["AgenticTable.CreateSheetMetadata"],
    ) -> MagicTableActionResult:
        """Create sheet metadata entries (`POST /magic-table/{tableId}/sheet/metadata`)."""
        url = f"/magic-table/{params['tableId']}/sheet/metadata"
        params.pop("tableId")
        return cast(
            MagicTableActionResult,
            await cls._static_request_async(
                "post",
                url,
                user_id,
                company_id,
                params,
            ),
        )

    @classmethod
    async def delete_sheet_metadata(
        cls,
        user_id: str,
        company_id: str,
        tableId: str,
        metadataId: str,
    ) -> MagicTableActionResult:
        """Delete a sheet metadata entry (`DELETE /magic-table/{tableId}/sheet/metadata/{metadataId}`)."""
        url = f"/magic-table/{tableId}/sheet/metadata/{metadataId}"
        return cast(
            MagicTableActionResult,
            await cls._static_request_async(
                "delete",
                url,
                user_id,
                company_id,
            ),
        )
