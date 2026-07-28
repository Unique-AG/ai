from enum import StrEnum
from typing import Annotated, Any, Generic, Literal, TypeVar, override

from pydantic import (
    AliasChoices,
    BaseModel,
    Field,
    field_validator,
)
from unique_sdk import (
    AgenticTableSheetState,
    AgreementStatus,
    MagicTableArtifactState,
    MagicTableArtifactType,
    SelectionMethod,
)
from unique_sdk import LogDetail as SDKLogDetail
from unique_sdk import LogEntry as SDKLogEntry
from unique_sdk.api_resources._agentic_table import (
    MagicTableAction,
    SheetType,
)

from unique_toolkit._common.exception import ConfigurationException
from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit.app.schemas import (
    AssistantWebhookEvent,
    BaseEventPayload,
)
from unique_toolkit.app.unique_settings import UniqueChatEventFilterOptions
from unique_toolkit.language_model.schemas import (
    LanguageModelMessageRole,
    LanguageModelMessages,
)


class MagicTableEventTypes(StrEnum):
    IMPORT_COLUMNS = "unique.magic-table.import-columns"
    UPDATE_CELL = "unique.magic-table.update-cell"
    ADD_DATA = "unique.magic-table.add-document"
    ADD_META_DATA = "unique.magic-table.add-meta-data"
    GENERATE_ARTIFACT = "unique.magic-table.generate-artifact"
    SHEET_COMPLETED = "unique.magic-table.sheet-completed"
    LIBRARY_SHEET_ROW_VERIFIED = "unique.magic-table.library-sheet-row.verified"
    SHEET_CREATED = "unique.magic-table.sheet-created"
    RERUN_ROW = "unique.magic-table.rerun-row"


class BaseMetadata(BaseModel):
    model_config = get_configuration_dict()

    sheet_type: SheetType = Field(
        description="The type of the sheet.",
        default=SheetType.DEFAULT,
    )

    additional_sheet_information: dict[str, Any] = Field(
        default_factory=dict, description="Additional information for the sheet"
    )

    @field_validator("additional_sheet_information", mode="before")
    @classmethod
    def normalize_additional_sheet_information(cls, v):
        if v is None:
            return {}
        return v


class RowMetadataEntry(BaseModel):
    model_config = get_configuration_dict()
    id: str = Field(description="The ID of the metadata")
    key: str = Field(description="The key of the metadata")
    value: str = Field(description="The value of the metadata")
    exact_filter: bool = Field(
        default=False,
        description="Whether the metadata is to be used for strict filtering",
    )


class DDMetadata(BaseMetadata):
    model_config = get_configuration_dict()

    question_file_ids: list[str] = Field(
        default_factory=list, description="The IDs of the question files"
    )
    source_file_ids: list[str] = Field(
        default_factory=list, description="The IDs of the source files"
    )
    question_texts: list[str] = Field(
        default_factory=list, description="The texts of the questions"
    )
    context: str = Field(default="", description="The context text for the table.")

    rerun: bool = Field(
        default=False,
        description=(
            "Explicit re-run when sources change; bypasses auto_reprocess_on_source_add "
            "when true."
        ),
        validation_alias=AliasChoices("rerun", "Rerun"),
    )

    @field_validator("context", mode="before")
    @classmethod
    def normalize_context(cls, v):
        if v is None:
            return ""
        return v


# Define template types
A = TypeVar("A", bound=MagicTableAction)
T = TypeVar("T", bound=BaseMetadata)


class MagicTableBasePayload(BaseEventPayload, Generic[A, T]):
    """Magic-table-specific payload.

    Inherits the common envelope fields (``name``, ``chat_id``, ``assistant_id``,
    ``configuration``, ``metadata_filter``, ``correlation``) from
    :class:`BaseEventPayload` and adds magic-table-only fields.

    Note: previously this carried stub-empty ``user_message`` /
    ``assistant_message`` defaults so that ``MagicTableEvent`` could pose as
    a ``ChatEvent``. That coupling is gone; magic-table flows that need a
    chat context should construct a :class:`UniqueContext` explicitly.
    """

    model_config = get_configuration_dict()

    # Optional on magic-table (BaseEventPayload requires it for chat).
    configuration: dict[str, Any] = Field(default_factory=dict)
    sheet_name: str
    action: A
    table_id: str
    metadata: T


########### Specialized Payload definitions ###########


class MagicTableAddMetadataPayload(
    MagicTableBasePayload[Literal[MagicTableAction.ADD_META_DATA], DDMetadata]
): ...


class MagicTableUpdateCellPayload(
    MagicTableBasePayload[Literal[MagicTableAction.UPDATE_CELL], DDMetadata]
):
    column_order: int
    row_order: int
    data: str


# Same wire values as ``MagicTableArtifactType`` / public ``POST .../artifact`` (unique-sdk 0.11.12+).
ArtifactType = MagicTableArtifactType


class ArtifactData(BaseModel):
    model_config = get_configuration_dict()
    artifact_type: MagicTableArtifactType


class MagicTableGenerateArtifactPayload(
    MagicTableBasePayload[Literal[MagicTableAction.GENERATE_ARTIFACT], BaseMetadata]
):
    data: ArtifactData
    requested_by_user_id: str | None = Field(
        default=None,
        description=(
            "User who initiated the export when the event top-level user_id is the "
            "sheet owner (set by node-chat as requestedByUserId)."
        ),
    )


########## Sheet Completed Payload ##########


class SheetCompletedMetadata(BaseMetadata):
    model_config = get_configuration_dict()
    sheet_id: str = Field(description="The ID of the sheet that was completed.")
    library_sheet_id: str = Field(
        description="The ID of the library corresponding to the sheet."
    )
    context: str = Field(default="", description="The context text for the table.")

    @field_validator("context", mode="before")
    @classmethod
    def normalize_context(cls, v):
        if v is None:
            return ""
        return v


class MagicTableSheetCompletedPayload(
    MagicTableBasePayload[
        Literal[MagicTableAction.SHEET_COMPLETED], SheetCompletedMetadata
    ]
): ...


class SheetCreatedMetadata(BaseMetadata): ...


class MagicTableSheetCreatedPayload(
    MagicTableBasePayload[Literal[MagicTableAction.SHEET_CREATED], SheetCreatedMetadata]
): ...


########## Library Sheet Row Verified Payload ##########


class LibrarySheetRowVerifiedMetadata(BaseMetadata):
    model_config = get_configuration_dict()
    row_order: int = Field(description="The row index of the row that was verified.")


class MagicTableLibrarySheetRowVerifiedPayload(
    MagicTableBasePayload[
        Literal[MagicTableAction.LIBRARY_SHEET_ROW_VERIFIED],
        LibrarySheetRowVerifiedMetadata,
    ]
): ...


########## Rerun Row Payload ##########


class RerunRowMetadata(BaseMetadata):
    model_config = get_configuration_dict()
    source_file_ids: list[str] = Field(
        description="The IDs of the source files to be used for this rerun"
    )
    row_order: int = Field(description="The row index of the row to rerun.")
    context: str = Field(default="", description="The context text for the rerun.")

    @field_validator("context", mode="before")
    @classmethod
    def normalize_context(cls, v):
        if v is None:
            return ""
        return v


class MagicTableRerunRowPayload(
    MagicTableBasePayload[Literal[MagicTableAction.RERUN_ROW], RerunRowMetadata]
): ...


########### Magic Table Event definition ###########


PayloadTypes = (
    MagicTableUpdateCellPayload
    | MagicTableAddMetadataPayload
    | MagicTableGenerateArtifactPayload
    | MagicTableSheetCompletedPayload
    | MagicTableLibrarySheetRowVerifiedPayload
    | MagicTableSheetCreatedPayload
    | MagicTableRerunRowPayload
)

MagicTablePayloadTypes = Annotated[PayloadTypes, Field(discriminator="action")]


class MagicTableEvent(
    AssistantWebhookEvent[UniqueChatEventFilterOptions, MagicTablePayloadTypes]
):
    """Magic-table webhook event, sibling of :class:`ChatEvent`.

    No longer extends ``ChatEvent``; both events are siblings under
    :class:`AssistantWebhookEvent`. This makes ``isinstance(magic_table_event,
    ChatEvent)`` correctly return ``False`` and prevents silently passing a
    magic-table event to services that require chat-only fields.
    """

    event: MagicTableEventTypes  # pyright: ignore[reportIncompatibleVariableOverride]

    @override
    def filter_event(
        self, *, filter_options: UniqueChatEventFilterOptions | None = None
    ) -> bool:
        if filter_options is None:
            return False

        if not filter_options.assistant_ids and not filter_options.references_in_code:
            raise ConfigurationException(
                "No filter options provided, all events will be filtered! \n"
                "Please define: \n"
                " - 'UNIQUE_CHAT_EVENT_FILTER_OPTIONS_ASSISTANT_IDS' \n"
                " - 'UNIQUE_CHAT_EVENT_FILTER_OPTIONS_REFERENCES_IN_CODE' \n"
                "in your environment variables."
            )

        if (
            filter_options.assistant_ids
            and self.payload.assistant_id not in filter_options.assistant_ids
        ):
            return True

        if (
            filter_options.references_in_code
            and self.payload.name not in filter_options.references_in_code
        ):
            return True

        return super().filter_event(filter_options=filter_options)


class LogDetail(BaseModel):
    model_config = get_configuration_dict()
    llm_request: LanguageModelMessages | None = Field(
        default=None, description="The LLM request for the log detail"
    )

    def to_sdk_log_detail(self) -> SDKLogDetail:
        llm_request = None
        if self.llm_request:
            llm_request = self.llm_request.model_dump()
        return SDKLogDetail(llmRequest=llm_request)


class LogEntry(BaseModel):
    model_config = get_configuration_dict()

    text: str
    created_at: str
    actor_type: LanguageModelMessageRole
    message_id: str | None = None
    details: LogDetail | None = Field(
        default=None, description="The details of the log entry"
    )

    @field_validator("actor_type", mode="before")
    @classmethod
    def normalize_actor_type(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v

    def to_sdk_log_entry(self) -> SDKLogEntry:
        params: dict[str, Any] = {
            "text": self.text,
            "createdAt": self.created_at,
            "actorType": self.actor_type.value.upper(),
        }
        if self.details:
            params["details"] = self.details.to_sdk_log_detail()

        return SDKLogEntry(**params)


class MagicTableCellMetaData(BaseModel):
    model_config = get_configuration_dict()
    row_order: int = Field(description="The row index of the cell.")
    column_order: int = Field(description="The column index of the cell.")
    selected: bool | None = None
    selection_method: SelectionMethod | None = None
    agreement_status: AgreementStatus | None = None


class MagicTableCell(BaseModel):
    model_config = get_configuration_dict()
    sheet_id: str
    row_order: int = Field(description="The row index of the cell.")
    column_order: int = Field(description="The column index of the cell.")
    row_locked: bool = Field(default=False, description="Lock status of the row.")
    text: str
    log_entries: list[LogEntry] = Field(
        default_factory=list, description="The log entries for the cell"
    )
    meta_data: MagicTableCellMetaData | None = Field(
        default=None, description="The metadata for the cell"
    )
    row_metadata: list[RowMetadataEntry] = Field(
        default_factory=list,
        description="The metadata (key value pairs)for the rows.",
    )


class MagicTableSheet(BaseModel):
    model_config = get_configuration_dict()
    sheet_id: str
    name: str
    state: AgenticTableSheetState
    total_number_of_rows: int = Field(
        default=0,
        description="The total number of rows in the sheet",
        alias="magicTableRowCount",
    )
    chat_id: str | None = Field(
        default=None,
        description="Chat that owns the sheet when returned by the API (may be omitted).",
    )
    created_by: str
    company_id: str
    created_at: str
    magic_table_cells: list[MagicTableCell] = Field(
        default_factory=list, description="The cells in the sheet"
    )
    magic_table_sheet_metadata: list[RowMetadataEntry] = Field(
        default_factory=list, description="The metadata for the sheet"
    )


class CreatedMagicTableSheet(BaseModel):
    """Response of `POST /magic-table` (create sheet in a space)."""

    model_config = get_configuration_dict()
    sheet_id: str
    due_diligence_id: str = Field(
        description="Identifier of the due-diligence record backing this sheet."
    )
    name: str
    state: AgenticTableSheetState
    chat_id: str | None = Field(
        default=None, description="Chat that owns the sheet (may be null)."
    )
    created_by: str
    company_id: str
    created_at: str
    due_at: str | None = None


class MagicTableArtifact(BaseModel):
    """Export artifact of a sheet as returned by `GET /magic-table/{tableId}/artifacts`."""

    model_config = get_configuration_dict()
    id: str
    name: str | None = None
    content_id: str | None = Field(
        default=None,
        description="Content id of the generated file. Only present once the artifact is DONE; download it via the Content API.",
    )
    mime_type: str | None = None
    artifact_type: MagicTableArtifactType
    artifact_state: MagicTableArtifactState = Field(
        description="IN_PROGRESS while the agent is generating the export, DONE when ready."
    )
    created_at: str
    updated_at: str


class SheetMetadataEntryInput(BaseModel):
    """Input entry for creating sheet metadata (key/value pairs) on a sheet."""

    model_config = get_configuration_dict()
    key: str
    value: str
    exact_filter: bool = Field(
        default=False,
        description="Whether the metadata is to be used for strict filtering",
    )
