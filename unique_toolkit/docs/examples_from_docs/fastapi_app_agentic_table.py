
import logging
from pathlib import Path

from unique_sdk.api_resources._agentic_table import ActivityStatus

from unique_toolkit.agentic_table.schemas import MagicTableEvent
from unique_toolkit.agentic_table.schemas import MagicTableAction
from unique_toolkit.agentic_table.service import AgenticTableService
from unique_toolkit.app.fast_api_factory import build_agentic_table_custom_app
from unique_toolkit.app.unique_settings import UniqueSettings
logger = logging.getLogger(__name__)


# Default event handler
async def agentic_table_event_handler(event: MagicTableEvent) -> int:
    """
    Default event handler that serves as a controller for the Agentic Table.
    """
    # Initialize Agentic Table Service to interact with agentic table.
    at_service = AgenticTableService(
        user_id=event.user_id,
        company_id=event.company_id,
        table_id=event.payload.table_id,
    )

    # Initialize the configuration from the event for your custom application
    # config = YourConfigClass.model_validate(event.payload.configuration)

    # You can now potentially use this configuration to initialize any other services needed for your application.
    ...


    # Register the agent
    # This locks the table from any modifications until the agent is completed.
    # Once registered the sheet status is shown as "Updating"
    await at_service.register_agent()

    # Depending on the event received/action, run the corresponding functionality
    match event.payload.action:
        case MagicTableAction.SHEET_CREATED:
            # This event is triggered when a new sheet is created.
            # You can use this for housekeeping tasks like displaying the table headers, etc.
            #
            # Payload Structure (MagicTableSheetCreatedPayload):
            # - name: str - The name of the module
            # - sheet_name: str - The name of the sheet
            # - action: MagicTableAction.SHEET_CREATED
            # - chat_id: str - The chat ID associated with the table
            # - assistant_id: str - The assistant ID
            # - table_id: str - The table ID
            # - user_message: ChatEventUserMessage - User message details (id, text, original_text, created_at, language)
            # - assistant_message: ChatEventAssistantMessage - Assistant message details (id, created_at)
            # - configuration: dict[str, Any] - Custom configuration dictionary
            # - metadata: SheetCreatedMetadata - Contains:
            #     * sheet_type: SheetType - The type of the sheet (DEFAULT or LIBRARY)
            # - metadata_filter: dict[str, Any] | None - Optional metadata filter
            #
            # Since this is also simply house keeping, you might not want to lock the table functionality.
            # await at_service.deregister_agent() 
            ...
        case MagicTableAction.ADD_META_DATA:
            # This event is triggered when a new question or question file or source file is added.
            #
            # Payload Structure (MagicTableAddMetadataPayload):
            # - name: str - The name of the module
            # - sheet_name: str - The name of the sheet
            # - action: MagicTableAction.ADD_META_DATA
            # - chat_id: str - The chat ID associated with the table
            # - assistant_id: str - The assistant ID
            # - table_id: str - The table ID
            # - user_message: ChatEventUserMessage - User message details (id, text, original_text, created_at, language)
            # - assistant_message: ChatEventAssistantMessage - Assistant message details (id, created_at)
            # - configuration: dict[str, Any] - Custom configuration dictionary
            # - metadata: DDMetadata - Contains:
            #     * sheet_type: SheetType - The type of the sheet (DEFAULT or LIBRARY)
            #     * question_file_ids: list[str] - List of file IDs of question files added to the table
            #     * source_file_ids: list[str] - List of file IDs of source files added to the table
            #     * question_texts: list[str] - List of question texts added via the question text input box
            #     * context: str - The context text for the table
            # - metadata_filter: dict[str, Any] | None - Optional metadata filter
            #
            # The schema of the metadata is defined in unique_toolkit.agentic_table.schemas.DDMetadata.
            # You can pass this information to your agent/workflow.
            ...
        case MagicTableAction.UPDATE_CELL:
            # This event is triggered when a cell is updated.
            #
            # Payload Structure (MagicTableUpdateCellPayload):
            # - name: str - The name of the module
            # - sheet_name: str - The name of the sheet
            # - action: MagicTableAction.UPDATE_CELL
            # - chat_id: str - The chat ID associated with the table
            # - assistant_id: str - The assistant ID
            # - table_id: str - The table ID
            # - user_message: ChatEventUserMessage - User message details (id, text, original_text, created_at, language)
            # - assistant_message: ChatEventAssistantMessage - Assistant message details (id, created_at)
            # - configuration: dict[str, Any] - Custom configuration dictionary
            # - metadata: DDMetadata - Contains:
            #     * sheet_type: SheetType - The type of the sheet (DEFAULT or LIBRARY)
            #     * question_file_ids: list[str] - List of file IDs of question files
            #     * source_file_ids: list[str] - List of file IDs of source files
            #     * question_texts: list[str] - List of question texts
            #     * context: str - The context text for the table
            # - metadata_filter: dict[str, Any] | None - Optional metadata filter
            # - column_order: int - The column index (0-based) of the updated cell
            # - row_order: int - The row index (0-based) of the updated cell
            # - data: str - The new cell data/text value
            ...
        case MagicTableAction.GENERATE_ARTIFACT:
            # This event is triggered when a report generation button is clicked.
            #
            # Payload Structure (MagicTableGenerateArtifactPayload):
            # - name: str - The name of the module
            # - sheet_name: str - The name of the sheet
            # - action: MagicTableAction.GENERATE_ARTIFACT
            # - chat_id: str - The chat ID associated with the table
            # - assistant_id: str - The assistant ID
            # - table_id: str - The table ID
            # - user_message: ChatEventUserMessage - User message details (id, text, original_text, created_at, language)
            # - assistant_message: ChatEventAssistantMessage - Assistant message details (id, created_at)
            # - configuration: dict[str, Any] - Custom configuration dictionary
            # - metadata: BaseMetadata - Contains:
            #     * sheet_type: SheetType - The type of the sheet (DEFAULT or LIBRARY)
            # - metadata_filter: dict[str, Any] | None - Optional metadata filter
            # - data: ArtifactData - Contains:
            #     * artifact_type: ArtifactType - The type of artifact to generate (QUESTIONS or FULL_REPORT)
            ...
        case MagicTableAction.SHEET_COMPLETED:
            # This event is triggered when the sheet is marked as completed.
            #
            # Payload Structure (MagicTableSheetCompletedPayload):
            # - name: str - The name of the module
            # - sheet_name: str - The name of the sheet
            # - action: MagicTableAction.SHEET_COMPLETED
            # - chat_id: str - The chat ID associated with the table
            # - assistant_id: str - The assistant ID
            # - table_id: str - The table ID
            # - user_message: ChatEventUserMessage - User message details (id, text, original_text, created_at, language)
            # - assistant_message: ChatEventAssistantMessage - Assistant message details (id, created_at)
            # - configuration: dict[str, Any] - Custom configuration dictionary
            # - metadata: SheetCompletedMetadata - Contains:
            #     * sheet_type: SheetType - The type of the sheet (DEFAULT or LIBRARY)
            #     * sheet_id: str - The ID of the sheet that was completed
            #     * library_sheet_id: str - The ID of the library corresponding to the sheet
            #     * context: str - The context text for the table
            # - metadata_filter: dict[str, Any] | None - Optional metadata filter
            ...
        case MagicTableAction.LIBRARY_SHEET_ROW_VERIFIED:
            # This event is triggered when a row in a "Library" sheet is verified.
            # This is a special sheet type and is only relevant within the context of Rfp Agent.
            # You can ignore this event/block if you are not working with the library feature.
            #
            # Payload Structure (MagicTableLibrarySheetRowVerifiedPayload):
            # - name: str - The name of the module
            # - sheet_name: str - The name of the sheet
            # - action: MagicTableAction.LIBRARY_SHEET_ROW_VERIFIED
            # - chat_id: str - The chat ID associated with the table
            # - assistant_id: str - The assistant ID
            # - table_id: str - The table ID
            # - user_message: ChatEventUserMessage - User message details (id, text, original_text, created_at, language)
            # - assistant_message: ChatEventAssistantMessage - Assistant message details (id, created_at)
            # - configuration: dict[str, Any] - Custom configuration dictionary
            # - metadata: LibrarySheetRowVerifiedMetadata - Contains:
            #     * sheet_type: SheetType - The type of the sheet (DEFAULT or LIBRARY)
            #     * row_order: int - The row index (0-based) of the row that was verified
            # - metadata_filter: dict[str, Any] | None - Optional metadata filter
            ...
        case _:
            logger.error(f"Unknown action: {event.payload.action}")
            await at_service.deregister_agent()
            await at_service.set_activity(
                activity=event.payload.action,
                status=ActivityStatus.FAILED,
                text=f"Unknown action: {event.payload.action}",
            )

    # De-register the agent
    await at_service.deregister_agent()
    return 0 # Success

# Create the default app instance at module level
# This MUST be at module level so uvicorn can find it when importing

_SETTINGS = UniqueSettings.from_env(env_file=Path(__file__).parent / "unique.env")
_SETTINGS.init_sdk()

# Create app using factory
_MINIMAL_APP = build_agentic_table_custom_app(
    title="Unique Minimal Agentic Table App", 
    settings=_SETTINGS,
    event_handler=agentic_table_event_handler,
)


if __name__ == "__main__":
    import logging
    import uvicorn

    # Initialize settings
       
    # Enable debug logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    uvicorn.run(
        "fastapi_app_agentic_table:_MINIMAL_APP",
        host="0.0.0.0",
        port=5001,
        reload=True,
        log_level="debug",
    )

