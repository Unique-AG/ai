"""
Agentic Table Sheet Completed Handler Examples

This file demonstrates how to handle sheet completion events in the Agentic Table,
such as when a sheet is marked as completed.
"""

from unique_toolkit.agentic_table.schemas import MagicTableSheetCompletedPayload
from unique_toolkit.agentic_table.service import AgenticTableService
from unique_sdk import RowVerificationStatus
from logging import getLogger

logger = getLogger(__name__)


async def sheet_completed_handler(
    at_service: AgenticTableService, payload: MagicTableSheetCompletedPayload
) -> None:
    """
    Handle sheet completion events.
    
    This demonstrates how to:
    - Read final sheet state
    - Perform validation
    - Update row verification statuses
    - Log completion and cleanup
    """
    logger.info(f"Sheet completed: {payload.sheet_name}")
    logger.info(f"Sheet ID: {payload.metadata.sheet_id}")
    logger.info(f"Library Sheet ID: {payload.metadata.library_sheet_id}")
    
    # Get the final sheet data
    sheet = await at_service.get_sheet(start_row=0, end_row=None)
    total_rows = await at_service.get_num_rows()
    
    logger.info(f"Sheet has {total_rows} rows with {len(sheet.magic_table_cells)} cells")
    
    # Example 1: Validate data completeness
    # Check if all required columns are filled
    incomplete_rows = []
    rows_data = {}
    
    # Organize cells by row
    for cell in sheet.magic_table_cells:
        if cell.row_order not in rows_data:
            rows_data[cell.row_order] = {}
        rows_data[cell.row_order][cell.column_order] = cell.text
    
    # Check for incomplete rows (excluding header row 0)
    for row_num in range(1, total_rows):
        if row_num in rows_data:
            row = rows_data[row_num]
            # Assuming columns 0 and 1 are required
            if 0 not in row or not row[0].strip():
                incomplete_rows.append(row_num)
            elif 1 not in row or not row[1].strip():
                incomplete_rows.append(row_num)
    
    if incomplete_rows:
        logger.warning(f"Found {len(incomplete_rows)} incomplete rows: {incomplete_rows}")
        # You could mark these rows for review
        for row_num in incomplete_rows[:5]:  # Mark first 5 as examples
            await at_service.set_cell(
                row=row_num,
                column=5,  # Status column
                text="⚠️ Incomplete"
            )
    else:
        logger.info("All rows are complete!")
    
    # Example 2: Mark all complete rows as verified
    complete_rows = [row for row in range(1, total_rows) if row not in incomplete_rows]
    if complete_rows:
        await at_service.update_row_verification_status(
            row_orders=complete_rows,
            status=RowVerificationStatus.VERIFIED
        )
        logger.info(f"Marked {len(complete_rows)} rows as verified")
    
    # Example 3: Add completion timestamp
    if total_rows > 0:
        from datetime import datetime
        completion_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await at_service.set_cell(
            row=0,
            column=6,  # Add in a new column
            text=f"Completed: {completion_time}"
        )
    
    # Example 4: Log context if provided
    if payload.metadata.context:
        logger.info(f"Sheet context: {payload.metadata.context}")
    
    # Example 5: Get sheet metadata for additional processing
    sheet_metadata = await at_service.get_sheet_metadata()
    logger.info(f"Sheet has {len(sheet_metadata)} metadata entries")
    
    logger.info("Sheet completion processing finished")

