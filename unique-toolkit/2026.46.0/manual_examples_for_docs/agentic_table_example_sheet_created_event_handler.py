from logging import getLogger

from unique_sdk.api_resources._agentic_table import ActivityStatus

from unique_toolkit.agentic_table.schemas import MagicTableSheetCreatedPayload
from unique_toolkit.agentic_table.service import AgenticTableService

from .agentic_table_example_column_definition import example_column_definitions

logger = getLogger(__name__)


async def handle_sheet_created(
    at_service: AgenticTableService, payload: MagicTableSheetCreatedPayload
) -> None:
    """
    Example handler for the sheet creation event.

    This demo shows how to initialize a new table by:
    - Setting column headers in row 0
    - Applying column styles (width, renderer type, editability)

    The table is ready to receive data after initialization.

    Args:
        at_service: Service instance for table operations
        payload: Event payload with table_id and sheet_name
    """
    logger.info(f"Initializing Source of Wealth table: {payload.sheet_name}")

    # Set activity status
    await at_service.set_activity(
        text="Initializing table schema...",
        activity=payload.action,
        status=ActivityStatus.IN_PROGRESS,
    )

    # Set headers in row 0
    for col_def in example_column_definitions.columns:
        await at_service.set_cell(row=0, column=col_def.order, text=col_def.name.value)

    logger.info(f"Set {len(example_column_definitions.columns)} column headers")

    # Apply column styles
    for col_def in example_column_definitions.columns:
        await at_service.set_column_style(
            column=col_def.order,
            width=col_def.width,
            cell_renderer=col_def.renderer,
            editable=col_def.editable,
        )

    logger.info("Applied column styles with all CellRendererTypes")

    # Set completion status
    await at_service.set_activity(
        text="Table schema initialized successfully",
        activity=payload.action,
        status=ActivityStatus.COMPLETED,
    )
