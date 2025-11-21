from enum import StrEnum
from typing import (
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
    llmRequest: list[dict] | None


class LogEntry(TypedDict):
    text: str
    createdAt: str
    actorType: Literal["USER", "SYSTEM", "ASSISTANT", "TOOL"]
    messageId: NotRequired[str]
    details: NotRequired[list[LogDetail]]


class AgenticTableCell(TypedDict, total=False):
    sheetId: str
    rowOrder: int
    columnOrder: int
    rowLocked: bool
    text: str
    logEntries: list[LogEntry]


class ColumnMetadataUpdateStatus(TypedDict, total=False):
    status: bool
    message: str | None


class AgenticTableSheet(TypedDict):
    sheetId: str
    name: str
    state: AgenticTableSheetState
    chatId: str
    createdBy: str
    companyId: str
    createdAt: str
    magicTableRowCount: int
    magicTableCells: NotRequired[list[AgenticTableCell]]


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


class SelectionMethod(StrEnum):
    DEFAULT = "DEFAULT"
    MANUAL = "MANUAL"


class AgreementStatus(StrEnum):
    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"


class RowVerificationStatus(StrEnum):
    NEED_REVIEW = "NEED_REVIEW"
    READY_FOR_VERIFICATION = "READY_FOR_VERIFICATION"
    VERIFIED = "VERIFIED"


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

    class SetActivityStatus(RequestOptions):
        tableId: str
        activity: Literal[
            "DeleteRow",
            "DeleteColumn",
            "UpdateCell",
            "AddQuestionText",
            "AddMetaData",
            "GenerateArtifact",
            "SheetCompleted",
            "LibrarySheetRowVerified",
        ]
        status: Literal[
            "IN_PROGRESS",
            "COMPLETED",
            "FAILED",
        ]
        text: str

    class SetArtifact(RequestOptions):
        tableId: str
        name: str
        contentId: str
        mimeType: str
        artifactType: Literal["QUESTIONS", "FULL_REPORT"]

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
        tableId: str
        includeCells: NotRequired[bool]
        includeLogHistory: NotRequired[bool]
        includeRowCount: NotRequired[bool]
        includeCellMetaData: NotRequired[bool]
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
            cls._static_request(
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
        return cast(
            "AgenticTableCell",
            await cls._static_request_async(
                "get",
                url,
                user_id,
                company_id,
                params={},
            ),
        )

    @classmethod
    async def set_activity(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["AgenticTable.SetActivityStatus"],
    ) -> "AgenticTableCell":
        """ """
        url = f"/magic-table/{params['tableId']}/activity"
        return cast(
            "AgenticTableCell",
            cls._static_request(
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
    ) -> "AgenticTableCell":
        """ """
        url = f"/magic-table/{params['tableId']}/artifact"
        return cast(
            "AgenticTableCell",
            cls._static_request(
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
            cls._static_request("post", url, user_id, company_id, params),
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
        response = cls._static_request("post", url, user_id, company_id, params)
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
            cls._static_request("get", url, user_id, company_id, params),
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
            cls._static_request("post", url, user_id, company_id, params),
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
        # Map AgenticTableCell to PublicAgenticTableCellDto
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
            cls._static_request("post", url, user_id, company_id, params=params_api),
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
            cls._static_request(
                "post",
                url,
                user_id,
                company_id,
                params,
            ),
        )
