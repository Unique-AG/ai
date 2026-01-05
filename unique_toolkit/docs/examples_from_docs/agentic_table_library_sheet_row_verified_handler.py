"""
Agentic Table Library Sheet Row Verified Handler Examples

This file demonstrates how to handle library sheet row verification events.
This is a specialized feature for library sheets in the Agentic Table.
"""

from unique_toolkit.agentic_table.schemas import MagicTableLibrarySheetRowVerifiedPayload
from unique_toolkit.agentic_table.service import AgenticTableService
from unique_sdk import RowVerificationStatus
from logging import getLogger

logger = getLogger(__name__)


async def library_sheet_row_verified_handler(
    at_service: AgenticTableService, 
    payload: MagicTableLibrarySheetRowVerifiedPayload
) -> None:
    """
    Handle library sheet row verification events.
    
    This is a specialized handler for the library feature. If you're not using
    the library feature, you can ignore this event type.
    
    This demonstrates how to:
    - Get the verified row data
    - Update related cells
    - Mark the row as processed
    """
    verified_row = payload.metadata.row_order
    logger.info(f"Library sheet row verified: row {verified_row}")
    logger.info(f"Sheet: {payload.sheet_name}")
    
    # Get the verified row data
    # Read all cells in the verified row
    row_data = {}
    for col in range(10):  # Check up to 10 columns
        try:
            cell = await at_service.get_cell(row=verified_row, column=col)
            row_data[col] = cell.text
        except Exception as e:
            # Column might not exist
            break
    
    logger.info(f"Verified row data: {row_data}")
    
    # Example 1: Mark the row as processed in a status column
    status_column = 0  # Assuming column 0 is the status column
    await at_service.set_cell(
        row=verified_row,
        column=status_column,
        text="✓ Verified"
    )
    
    # Example 2: Add a verification timestamp
    from datetime import datetime
    verification_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamp_column = len(row_data)  # Add in the next available column
    await at_service.set_cell(
        row=verified_row,
        column=timestamp_column,
        text=f"Verified: {verification_time}"
    )
    
    # Example 3: Update the row verification status
    await at_service.update_row_verification_status(
        row_orders=[verified_row],
        status=RowVerificationStatus.VERIFIED
    )
    
    # Example 4: Process the verified data
    # In a library context, you might want to:
    # - Copy verified data to another sheet
    # - Trigger downstream processing
    # - Update related records
    
    if row_data.get(1):  # If there's data in column 1
        logger.info(f"Processing verified data: {row_data.get(1)}")
        # Add your custom processing logic here
    
    # Example 5: Check if this is part of a batch verification
    # You might want to track how many rows have been verified
    total_rows = await at_service.get_num_rows()
    logger.info(f"Row {verified_row} of {total_rows} verified")
    
    # Example 6: Set cell metadata to mark selection
    await at_service.set_cell_metadata(
        row=verified_row,
        column=0,
        selected=True
    )
    
    logger.info(f"Library row {verified_row} verification processing completed")

