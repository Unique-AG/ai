"""
Agentic Table Cell Updated Handler Examples

This file demonstrates how to handle cell update events in the Agentic Table,
such as when a user edits a cell value.
"""

from unique_toolkit.agentic_table.schemas import (
    MagicTableUpdateCellPayload,
    LogEntry,
)
from unique_toolkit.agentic_table.service import AgenticTableService
from unique_toolkit.language_model.schemas import LanguageModelMessageRole
from datetime import datetime
from logging import getLogger

logger = getLogger(__name__)


async def cell_updated_handler(
    at_service: AgenticTableService, payload: MagicTableUpdateCellPayload
) -> None:
    """
    Handle cell update events when a user edits a cell.
    
    This demonstrates how to:
    - Read the updated cell value
    - Perform validation
    - Update related cells
    - Add log entries to track changes
    """
    logger.info(
        f"Cell updated at row {payload.row_order}, column {payload.column_order}: {payload.data}"
    )
    
    # Get the full cell data including any existing metadata
    cell = await at_service.get_cell(
        row=payload.row_order, 
        column=payload.column_order
    )
    
    # Example 1: Simple validation
    if payload.column_order == 2:  # Assuming column 2 is a score column
        try:
            score = int(payload.data)
            if score < 0 or score > 100:
                logger.warning(f"Score out of range: {score}")
                # You could update the cell with validation feedback
                await at_service.set_cell(
                    row=payload.row_order,
                    column=payload.column_order + 1,
                    text="⚠️ Score must be between 0-100"
                )
        except ValueError:
            logger.warning(f"Invalid score format: {payload.data}")
    
    # Example 2: Add a log entry to track the change
    log_entries = [
        LogEntry(
            text=f"Cell updated by user to: {payload.data}",
            created_at=datetime.now().isoformat(),
            actor_type=LanguageModelMessageRole.USER,
        )
    ]
    
    await at_service.set_cell(
        row=payload.row_order,
        column=payload.column_order,
        text=payload.data,
        log_entries=log_entries
    )
    
    # Example 3: Update a related cell (e.g., timestamp column)
    # Assuming column 0 is the data column and column 3 is the "Last Updated" column
    if payload.column_order == 0:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await at_service.set_cell(
            row=payload.row_order,
            column=3,
            text=f"Updated: {current_time}"
        )
    
    # Example 4: Update a status column based on the data
    if payload.data.lower() in ["done", "completed", "finished"]:
        await at_service.set_cell(
            row=payload.row_order,
            column=4,  # Status column
            text="✓ Completed"
        )
    
    logger.info(f"Cell update processed successfully")

