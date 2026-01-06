import logging
from pathlib import Path

from unique_sdk.api_resources._agentic_table import ActivityStatus

from unique_toolkit import ChatService, KnowledgeBaseService
from unique_toolkit.agentic_table.schemas import MagicTableEvent
from unique_toolkit.agentic_table.schemas import MagicTableAction
from unique_toolkit.agentic_table.service import AgenticTableService
from unique_toolkit.agentic_table.schemas import MagicTableEventTypes
from unique_toolkit.app.fast_api_factory import build_unique_custom_app
from unique_toolkit.app.unique_settings import UniqueSettings

from docs.examples_from_docs.agentic_table_example_sheet_created_event_handler import (
    handle_sheet_created,
)
from docs.examples_from_docs.agentic_table_example_metadata_added_event_handler import (
    handle_metadata_added,
    get_downloader,
)
from docs.examples_from_docs.agentic_table_example_cell_updated_event_handler import (
    handle_cell_updated,
)
from docs.examples_from_docs.agentic_table_example_artifact_generated_event_handler import (
    handle_artifact_generated,
    get_uploader,
)


# Configure logging at module level so it works regardless of how the app is started
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
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

    try:
        # We use if-else statements here instead of match/case because it enables more precise typing and type narrowing for the payload based on the action (which functions as a discriminator).
        # Depending on the event received/action, run the corresponding functionality
        if event.payload.action == MagicTableAction.SHEET_CREATED:
            # This event is triggered when a new sheet is created.
            # You can use this for housekeeping tasks like displaying the table headers, etc.
            #
            # Payload type (MagicTableSheetCreatedPayload):
            logger.info(f"Sheet created: {event.payload.sheet_name}")

            # Deregister the agent to unblock upcoming events
            await at_service.deregister_agent()

            # Handle the sheet creation event (This is usally to setup the headers and column styles)
            await handle_sheet_created(at_service, event.payload)

            # In a standard workflow the user will select sources and a question file
            # This will trigger the add_metadata event and it can come quite quickly after the sheet_created event
            # therefore we need to deregister the agent to unblock the upcoming events

        elif event.payload.action == MagicTableAction.ADD_META_DATA:
            # This event is triggered when a new question or question file or source file is added.
            #
            # Payload type (MagicTableAddMetadataPayload):
            logger.info(f"Metadata added: {event.payload.metadata}")

            downloader = get_downloader(
                event.user_id, event.company_id, event.payload.chat_id
            )
            await handle_metadata_added(at_service, event.payload, downloader)

        elif event.payload.action == MagicTableAction.UPDATE_CELL:
            # This event is triggered when a cell is updated.
            #
            # Payload type (MagicTableUpdateCellPayload):
            logger.info(
                f"Cell updated: {event.payload.column_order}, {event.payload.row_order}, {event.payload.data}"
            )

            await handle_cell_updated(at_service, event.payload)

        elif event.payload.action == MagicTableAction.GENERATE_ARTIFACT:
            # This event is triggered when a report generation button is clicked.
            #
            # Payload type (MagicTableGenerateArtifactPayload):
            logger.info(f"Artifact generated: {event.payload.data}")

            uploader = get_uploader(
                event.user_id, event.company_id, event.payload.chat_id
            )

            await handle_artifact_generated(at_service, event.payload, uploader)

        elif event.payload.action == MagicTableAction.SHEET_COMPLETED:
            # This event is triggered when the sheet is marked as completed.
            #
            # Payload type (MagicTableSheetCompletedPayload):
            logger.info(f"Sheet completed: {event.payload.sheet_name}")

            # Here you can call a handler function that will handle the sheet completion event.

        elif event.payload.action == MagicTableAction.LIBRARY_SHEET_ROW_VERIFIED:
            # This event is triggered when a row in a "Library" sheet is verified.
            # This is a special sheet type and is only relevant within the context of Rfp Agent.
            # You can ignore this event/block if you are not working with the library feature.
            #
            # Payload type (MagicTableLibrarySheetRowVerifiedPayload):
            logger.info(
                f"Library sheet row verified: {event.payload.metadata.row_order}"
            )

            # Here you can call a handler function that will handle the library sheet row verified event.

        else:
            logger.error(f"Unknown action: {event.payload.action}")
            await at_service.set_activity(
                activity=event.payload.action,
                status=ActivityStatus.FAILED,
                text=f"Unknown action: {event.payload.action}",
            )
        return 0 # Success
    
    except Exception as e:
        logger.error(f"Error in agentic table event handler: {e}")
        return 1 # Failure
    
    finally:
        # De-register the agent
        await at_service.deregister_agent()


# Create the default app instance at module level
# This MUST be at module level so uvicorn can find it when importing

_SETTINGS = UniqueSettings.from_env(env_file=Path(__file__).parent / "unique.env")
_SETTINGS.init_sdk()

# Create app using factory
_MINIMAL_APP = build_unique_custom_app(
    title="Unique Minimal Agentic Table App",
    settings=_SETTINGS,
    event_handler=agentic_table_event_handler,
    event_constructor=MagicTableEvent,
    subscribed_event_names=[ev.value for ev in MagicTableEventTypes],
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

    # Run the server
    uvicorn.run(
        "fastapi_app_agentic_table:_MINIMAL_APP",
        host="0.0.0.0",
        port=5001,
        reload=True,
        log_level="debug",
    )
