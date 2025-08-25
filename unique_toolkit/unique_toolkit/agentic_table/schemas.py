from enum import StrEnum
from typing import Any, Literal

from humps import camelize
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)
from unique_sdk import (
    AgenticTableSheetState,
    AgreementStatus,
    SelectionMethod,
)

from unique_toolkit.app.schemas import (
    ChatEvent,
    ChatEventAssistantMessage,
    ChatEventUserMessage,
)
from unique_toolkit.language_model.schemas import LanguageModelMessageRole

model_config = ConfigDict(
    alias_generator=camelize,
    populate_by_name=True,
    arbitrary_types_allowed=True,
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


class MagicTableAction(StrEnum):
    DELETE_ROW = "DeleteRow"
    DELETE_COLUMN = "DeleteColumn"
    UPDATE_CELL = "UpdateCell"
    ADD_QUESTION_TEXT = "AddQuestionText"
    ADD_META_DATA = "AddMetaData"
    GENERATE_ARTIFACT = "GenerateArtifact"
    SHEET_COMPLETED = "SheetCompleted"
    LIBRARY_SHEET_ROW_VERIFIED = "LibrarySheetRowVerified"
    SHEET_CREATED = "SheetCreated"


class ActivityStatus(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SheetType(StrEnum):
    DEFAULT = "DEFAULT"
    LIBRARY = "LIBRARY"


class BaseMetadata(BaseModel):
    model_config = model_config

    sheet_type: SheetType = Field(
        description="The type of the sheet.",
        default=SheetType.DEFAULT,
    )


class DDMetadata(BaseMetadata):
    model_config = model_config

    question_file_ids: list[str] = Field(
        default_factory=list, description="The IDs of the question files"
    )
    source_file_ids: list[str] = Field(
        default_factory=list, description="The IDs of the source files"
    )
    question_texts: list[str] = Field(
        default_factory=list, description="The texts of the questions"
    )


class MagicTableBasePayload(BaseModel):
    model_config = model_config
    name: str = Field(description="The name of the module")
    sheet_name: str

    action: MagicTableAction
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
    metadata: BaseMetadata
    metadata_filter: dict[str, Any] | None = None


########### Specialized Payload definitions ###########


class MagicTableAddMetadataPayload(MagicTableBasePayload):
    action: Literal[MagicTableAction.ADD_META_DATA]
    metadata: DDMetadata


class MagicTableUpdateCellPayload(MagicTableBasePayload):
    action: Literal[MagicTableAction.UPDATE_CELL]
    column_order: int
    row_order: int
    data: str
    metadata: DDMetadata


class ArtifactType(StrEnum):
    QUESTIONS = "QUESTIONS"
    FULL_REPORT = "FULL_REPORT"


class ArtifactData(BaseModel):
    model_config = model_config
    artifact_type: ArtifactType


class MagicTableGenerateArtifactPayload(MagicTableBasePayload):
    action: Literal[MagicTableAction.GENERATE_ARTIFACT]

    data: ArtifactData


########## Sheet Completed Payload ##########


class SheetCompletedMetadata(BaseMetadata):
    model_config = model_config
    sheet_id: str = Field(description="The ID of the sheet that was completed.")
    library_sheet_id: str = Field(
        description="The ID of the library corresponding to the sheet."
    )


class MagicTableSheetCompletedPayload(MagicTableBasePayload):
    action: Literal[MagicTableAction.SHEET_COMPLETED]
    metadata: SheetCompletedMetadata


########## Sheet Created Payload ##########
class SheetCreatedMetadata(BaseMetadata):
    pass


class MagicTableSheetCreatedPayload(MagicTableBasePayload):
    action: Literal[MagicTableAction.SHEET_CREATED]
    metadata: SheetCreatedMetadata


########## Library Sheet Row Verified Payload ##########


class LibrarySheetRowVerifiedMetadata(BaseMetadata):
    model_config = model_config
    row_order: int = Field(description="The row index of the row that was verified.")


class MagicTableLibrarySheetRowVerifiedPayload(MagicTableBasePayload):
    action: Literal[MagicTableAction.LIBRARY_SHEET_ROW_VERIFIED]
    metadata: LibrarySheetRowVerifiedMetadata


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
    model_config = model_config
    text: str
    message_id: str | None


class LogEntry(BaseModel):
    model_config = model_config

    text: str
    created_at: str
    actor_type: LanguageModelMessageRole
    message_id: str | None = None
    details: list[LogDetail] = Field(
        default_factory=list, description="The details of the log entry"
    )

    @field_validator("actor_type", mode="before")
    @classmethod
    def normalize_actor_type(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v


class MagicTableCellMetaData(BaseModel):
    model_config = model_config
    row_order: int
    column_order: int
    selected: bool | None = None
    selection_method: SelectionMethod | None = None
    agreement_status: AgreementStatus | None = None


class MagicTableCell(BaseModel):
    model_config = model_config
    sheet_id: str
    row_order: int
    column_order: int
    row_locked: bool = Field(default=False, description="Lock status of the row.")
    text: str
    log_entries: list[LogEntry] = Field(
        default_factory=list, description="The log entries for the cell"
    )
    meta_data: MagicTableCellMetaData | None = Field(
        default=None, description="The metadata for the cell"
    )


class MagicTableSheet(BaseModel):
    model_config = model_config
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
