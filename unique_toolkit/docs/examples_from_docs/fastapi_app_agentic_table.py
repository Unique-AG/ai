
import logging
from pathlib import Path
from unique_toolkit.app.fast_api_factory import build_agentic_table_custom_app
from unique_toolkit import (
    ChatService,
    KnowledgeBaseService,
    LanguageModelName,
)
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.openai.message_builder import (
    OpenAIMessageBuilder,
)
from unique_toolkit.app.schemas import ChatEvent, EventName
from unique_toolkit.agentic_table.schemas import MagicTableEvent
from unique_toolkit.agentic_table.service import AgenticTableService
from unique_toolkit.agentic_table.schemas import MagicTableAction
logger = logging.getLogger(__name__)


# Default event handler
async def agentic_table_event_handler(event: MagicTableEvent) -> int:
    """
    Default event handler that serves as a controller for the Agentic Table.
    """
    # Initialize the configuration from the event for your custom application

    # Initialize any services needed
    at_service = AgenticTableService(
        user_id=event.user_id,
        company_id=event.company_id,
        table_id=event.payload.table_id,
    )

    # Register the agent
    # This locks the table from any modifications until the agent is completed.
    # Once registered the sheet status is shown as "Updating"
    await at_service.register_agent()

    # Depending on the event received/action, run the corresponding functionality
    match event.payload.action:
        case MagicTableAction.SHEET_CREATED:
            # This event is triggered when a new sheet is created.
            # You can use this for housekeeping tasks like displaying the table headers, etc.

            # Since this is also simply house keeping, you might not want to lock the table funcitonality.
            # await at_service.deregister_agent() 
            ...
        case MagicTableAction.ADD_META_DATA:
            # This event is triggered when a new question or question file or source file is added.
            ...
        case MagicTableAction.UPDATE_CELL:
            # This event is triggered when a cell is updated.
            ...
        case MagicTableAction.GENERATE_ARTIFACT:
            # This event is triggered when a report generation button is clicked.
            ...
        case MagicTableAction.SHEET_COMPLETED:
            # This event is triggered when the sheet is marked as completed.
            ...
        case MagicTableAction.LIBRARY_SHEET_ROW_VERIFIED:
            # This event is triggered when a row in a "Library" sheet is verified.
            # This is a special sheet type and is only relevant within the context of Rfp Agent.
            # You can ignore this event/block if you are not working with the library feature.
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

