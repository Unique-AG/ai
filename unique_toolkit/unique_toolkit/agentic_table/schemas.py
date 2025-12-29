from enum import StrEnum
from typing import Any, Generic, Literal, TypeVar

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)
from unique_sdk import (
    AgenticTableSheetState,
    AgreementStatus,
    SelectionMethod,
)
from unique_sdk import LogDetail as SDKLogDetail
from unique_sdk import LogEntry as SDKLogEntry
from unique_sdk.api_resources._agentic_table import (
    MagicTableAction,
    SheetType,
)

from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit.app.schemas import (
    ChatEvent,
    ChatEventAssistantMessage,
    ChatEventUserMessage,
)
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


class BaseMetadata(BaseModel):
    model_config = get_configuration_dict()

    sheet_type: SheetType = Field(
        description="The type of the sheet.",
        default=SheetType.DEFAULT,
    )


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

    @field_validator("context", mode="before")
    @classmethod
    def normalize_context(cls, v):
        if v is None:
            return ""
        return v


# Define template types
A = TypeVar("A", bound=MagicTableAction)
T = TypeVar("T", bound=BaseMetadata)


class MagicTableBasePayload(BaseModel, Generic[A, T]):
    model_config = get_configuration_dict()
    name: str = Field(description="The name of the module")
    sheet_name: str

    action: A
    chat_id: str
    assistant_id: str
    table_id: str
    user_message: ChatEventUserMessage = Field(
        default=ChatEventUserMessage(
            id="", text="", original_text="", created_at="", language=""
        )
    )
    assistant_message: ChatEventAssistantMessage = Field(
        default=ChatEventAssistantMessage(id="", created_at="")
    )
    configuration: dict[str, Any] = {}
    metadata: T
    metadata_filter: dict[str, Any] | None = None


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


class ArtifactType(StrEnum):
    QUESTIONS = "QUESTIONS"
    FULL_REPORT = "FULL_REPORT"


class ArtifactData(BaseModel):
    model_config = get_configuration_dict()
    artifact_type: ArtifactType


class MagicTableGenerateArtifactPayload(
    MagicTableBasePayload[Literal[MagicTableAction.GENERATE_ARTIFACT], BaseMetadata]
):
    data: ArtifactData


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


########### Magic Table Event definition ###########


class MagicTableEvent(ChatEvent):
    event: MagicTableEventTypes
    payload: (
        MagicTableUpdateCellPayload
        | MagicTableAddMetadataPayload
        | MagicTableGenerateArtifactPayload
        | MagicTableSheetCompletedPayload
        | MagicTableLibrarySheetRowVerifiedPayload
        | MagicTableSheetCreatedPayload
    ) = Field(discriminator="action")


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
    chat_id: str
    created_by: str
    company_id: str
    created_at: str
    magic_table_cells: list[MagicTableCell] = Field(
        default_factory=list, description="The cells in the sheet"
    )
    magic_table_sheet_metadata: list[RowMetadataEntry] = Field(
        default_factory=list, description="The metadata for the sheet"
    )
