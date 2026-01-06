from unique_toolkit.agentic_table.schemas import MagicTableUpdateCellPayload
from unique_toolkit.agentic_table.service import AgenticTableService
from logging import getLogger
from datetime import datetime
from unique_toolkit.language_model.schemas import LanguageModelMessageRole
from unique_sdk import RowVerificationStatus
from unique_toolkit.agentic_table.schemas import LogEntry
from .agentic_table_example_column_definition import (
    example_column_definitions,
    ExampleColumnNames,
)

logger = getLogger(__name__)


async def handle_cell_updated(
    at_service: AgenticTableService, payload: MagicTableUpdateCellPayload
) -> None:
    """
    Example handler for the cell update event.

    This demo shows a simple workflow automation: when the Critical Consistency column
    changes to "Consistent", it adds a log entry and updates
    the row verification status.

    Args:
        at_service: Service instance for table operations
        payload: Event payload with row, column, and new value
    """
    logger.info(
        f"Cell updated at row {payload.row_order}, "
        f"column {payload.column_order}: {payload.data}"
    )

    critical_consistency_col = example_column_definitions.get_column_by_name(
        ExampleColumnNames.CRITICAL_CONSISTENCY
    )

    # Check if the Critical Consistency column was updated
    if payload.column_order == critical_consistency_col.order:
        status_value = payload.data.strip()

        logger.info(f"Status changed to: {status_value}")

        # Check if status is Completed or Verified (lock row)
        if status_value.lower() in ["consistent"]:
            logger.info(
                f"Locking row {payload.row_order} due to status: {status_value}"
            )

            # Note: Column-level locking affects all rows. In a production system,
            # you might track locked rows in metadata and validate edits server-side.
            # Here we demonstrate the pattern with a log entry.

            # Add log entry to document the status change and locking
            log_entries = [
                LogEntry(
                    text=f"Row {payload.row_order} marked as {status_value}. Further edits should be restricted.",
                    created_at=datetime.now().isoformat(),
                    actor_type=LanguageModelMessageRole.ASSISTANT,
                )
            ]

            await at_service.set_cell(
                row=payload.row_order,
                column=payload.column_order,
                text=status_value,
                log_entries=log_entries,
            )

            # Update row verification status
            await at_service.update_row_verification_status(
                row_orders=[payload.row_order], status=RowVerificationStatus.VERIFIED
            )

            logger.info(f"Row {payload.row_order} verified and logged")
