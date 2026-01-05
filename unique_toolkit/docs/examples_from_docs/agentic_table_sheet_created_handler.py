"""
Agentic Table Sheet Created Handler Examples

This file demonstrates various ways to use the AgenticTableService
when handling sheet creation events.
"""

from unique_toolkit.agentic_table.schemas import (
    MagicTableSheetCreatedPayload,
    MagicTableCell,
    MagicTableAction,
    LogEntry,
)
from unique_toolkit.agentic_table.service import AgenticTableService
from unique_sdk import RowVerificationStatus, CellRendererTypes
from unique_sdk.api_resources._agentic_table import ActivityStatus
from unique_toolkit.language_model.schemas import LanguageModelMessageRole
from datetime import datetime
from logging import getLogger
import asyncio

logger = getLogger(__name__)


async def sheet_created_handler(at_service: AgenticTableService, payload: MagicTableSheetCreatedPayload) -> None:
    """Handle sheet created event."""
    logger.info(f"Sheet created: {payload.sheet_name}")
    match payload.sheet_name:
        case "basic_table":
            await basic_handle_sheet_created(at_service, payload)
        case "styled_table":
            await handle_sheet_created_with_styling(at_service, payload)
        case "batch_table":
            await handle_sheet_created_with_batch(at_service, payload)
        case "metadata_table":
            await handle_sheet_created_with_metadata(at_service, payload)
        case "read_data_table":
            await handle_sheet_created_read_data(at_service, payload)
        case "logs_table":
            await handle_sheet_created_with_logs(at_service, payload)
        case _:
            logger.error(f"Unknown sheet name: {payload.sheet_name}")


# Example 1: Basic table creation with headers and data
async def basic_handle_sheet_created(
    at_service: AgenticTableService, payload: MagicTableSheetCreatedPayload
) -> None:
    """Basic example showing how to create a simple table with headers and rows."""
    logger.info(f"Sheet created: {payload.sheet_name}")

    header_columns = {
        "Question": 0,
        "Answer": 1,
        "Context": 2,
        "File": 3,
    }

    # Add Header Rows
    for header, column in header_columns.items():
        await at_service.set_cell(row=0, column=column, text=header)

    # Add Row Contents
    for index in range(1, 10):
        await at_service.set_cell(
            row=index, column=header_columns["Question"], text=f"Question {index}"
        )
        await at_service.set_cell(
            row=index, column=header_columns["Answer"], text=f"Answer {index}"
        )
        await at_service.set_cell(
            row=index, column=header_columns["Context"], text=f"Context {index}"
        )
        await at_service.set_cell(
            row=index, column=header_columns["File"], text=f"File {index}"
        )


# Example 2: Table with column styling and cell renderers
async def handle_sheet_created_with_styling(
    at_service: AgenticTableService, payload: MagicTableSheetCreatedPayload
) -> None:
    """Example showing how to create a styled table demonstrating all available CellRendererTypes."""
    logger.info(f"Sheet created with styling: {payload.sheet_name}")

    # Define headers for all 5 CellRendererTypes plus a regular text column
    headers = ["Task", "Assignee", "Status", "Whatever Text", "Selectable", "Custom"]

    # Add headers to row 0
    for column, header in enumerate(headers):
        await at_service.set_cell(row=0, column=column, text=header)

    # Set column styles demonstrating all CellRendererTypes
    await at_service.set_column_style(
        column=0, 
        width=250, 
        editable=True
    )  # Task column - regular text, wide, editable
    
    await at_service.set_column_style(
        column=1, 
        width=180,
        cell_renderer=CellRendererTypes.COLLABORATOR_DROPDOWN
    )  # Assignee column with collaborator dropdown renderer
    
    await at_service.set_column_style(
        column=2, 
        width=150,
        cell_renderer=CellRendererTypes.REVIEW_STATUS_DROPDOWN
    )  # Status column with review status dropdown
    
    await at_service.set_column_style(
        column=3, 
        width=100,
        cell_renderer=CellRendererTypes.CHECKBOX_LOCK_CELL_RENDERER
    )  # Locked column with checkbox lock renderer
    
    await at_service.set_column_style(
        column=4,
        width=120,
        cell_renderer=CellRendererTypes.SELECTABLE_CELL_RENDERER
    )  # Selectable column with selectable cell renderer
    
    await at_service.set_column_style(
        column=5,
        width=150,
        cell_renderer=CellRendererTypes.CUSTOM_CELL_RENDERER
    )  # Custom column with custom cell renderer

    # Add sample data
    sample_data = [
        ["Implement login feature", "Alice", "In Progress", "false", "true", "Priority: High"],
        ["Fix navbar bug", "Bob", "Review", "true", "true", "Priority: Critical"],
        ["Update documentation", "Charlie", "Todo", "false", "false", "Priority: Low"],
        ["Add unit tests", "Alice", "Completed", "false", "true", "Priority: Medium"],
        ["Refactor API", "Bob", "In Progress", "false", "false", "Priority: Medium"],
    ]

    for row_idx, row_data in enumerate(sample_data, start=1):
        for col_idx, value in enumerate(row_data):
            await at_service.set_cell(row=row_idx, column=col_idx, text=value)


# Example 3: Batch operations for efficiency
async def handle_sheet_created_with_batch(
    at_service: AgenticTableService, payload: MagicTableSheetCreatedPayload
) -> None:
    """Example showing how to efficiently populate a table using batch operations."""
    logger.info(f"Sheet created with batch operations: {payload.sheet_name}")

    # Prepare all cells in memory first
    cells = []

    # Add headers
    headers = ["Product", "Category", "Price", "Stock", "Supplier"]
    for col_idx, header in enumerate(headers):
        cells.append(
            MagicTableCell(
                row_order=0, column_order=col_idx, text=header, sheet_id=payload.table_id
            )
        )

    # Generate product data (100 rows)
    categories = ["Electronics", "Clothing", "Food", "Books", "Toys"]
    suppliers = ["Supplier A", "Supplier B", "Supplier C", "Supplier D"]

    for row in range(1, 101):
        cells.append(
            MagicTableCell(
                row_order=row,
                column_order=0,
                text=f"Product {row}",
                sheet_id=payload.table_id,
            )
        )
        cells.append(
            MagicTableCell(
                row_order=row,
                column_order=1,
                text=categories[row % len(categories)],
                sheet_id=payload.table_id,
            )
        )
        cells.append(
            MagicTableCell(
                row_order=row,
                column_order=2,
                text=f"${row * 10}.99",
                sheet_id=payload.table_id,
            )
        )
        cells.append(
            MagicTableCell(
                row_order=row, column_order=3, text=str(row * 5), sheet_id=payload.table_id
            )
        )
        cells.append(
            MagicTableCell(
                row_order=row,
                column_order=4,
                text=suppliers[row % len(suppliers)],
                sheet_id=payload.table_id,
            )
        )

    # Set all cells at once using batch operation
    await at_service.set_multiple_cells(cells=cells)

    logger.info(f"Populated {len(cells)} cells in batch")




# Example 4: Cell metadata and row verification
async def handle_sheet_created_with_metadata(
    at_service: AgenticTableService, payload: MagicTableSheetCreatedPayload
) -> None:
    """Example showing how to use cell metadata and row verification status."""
    logger.info(f"Sheet created with metadata: {payload.sheet_name}")

    # Add headers
    headers = ["Task", "Priority", "Assignee", "Status"]
    for col_idx, header in enumerate(headers):
        await at_service.set_cell(row=0, column=col_idx, text=header)

    # Add tasks with different priorities
    tasks = [
        ["Implement login", "High", "Alice", "In Progress"],
        ["Fix navbar bug", "Critical", "Bob", "Review"],
        ["Update docs", "Low", "Charlie", "Todo"],
        ["Add tests", "Medium", "Alice", "Todo"],
    ]

    for row_idx, task_data in enumerate(tasks, start=1):
        for col_idx, value in enumerate(task_data):
            await at_service.set_cell(row=row_idx, column=col_idx, text=value)

        # Mark high/critical priority tasks as selected
        priority = task_data[1]
        if priority in ["High", "Critical"]:
            await at_service.set_cell_metadata(
                row=row_idx,
                column=1,  # Priority column
                selected=True,
            )

    # Update row verification status for reviewed rows
    await at_service.update_row_verification_status(
        row_orders=[2],  # Row with "Fix navbar bug"
        status=RowVerificationStatus.VERIFIED,
    )

    logger.info("Added task list with metadata and verification status")


# Example 5: Reading data from the table
async def handle_sheet_created_read_data(
    at_service: AgenticTableService, payload: MagicTableSheetCreatedPayload
) -> None:
    """Example showing how to read data from the table and process it."""
    logger.info(f"Sheet created with read operations: {payload.sheet_name}")

    # First, populate some sample data
    headers = ["Name", "Age", "City"]
    for col_idx, header in enumerate(headers):
        await at_service.set_cell(row=0, column=col_idx, text=header)

    sample_data = [
        ["Alice", "30", "New York"],
        ["Bob", "25", "San Francisco"],
        ["Charlie", "35", "Boston"],
    ]

    for row_idx, row_data in enumerate(sample_data, start=1):
        for col_idx, value in enumerate(row_data):
            await at_service.set_cell(row=row_idx, column=col_idx, text=value)

    # Now read the data back
    logger.info("Reading data from table...")

    # Get a specific cell
    cell = await at_service.get_cell(row=1, column=0)
    logger.info(f"Cell at (1, 0): {cell.text}")

    # Get the number of rows
    num_rows = await at_service.get_num_rows()
    logger.info(f"Total rows in table: {num_rows}")

    # Get all sheet data
    sheet = await at_service.get_sheet(start_row=0, end_row=None, batch_size=10)
    logger.info(f"Retrieved sheet with {len(sheet.magic_table_cells)} cells")

    # Process the data - find all people from New York
    for cell in sheet.magic_table_cells:
        if cell.column_order == 2 and cell.text == "New York":
            # Get the name from the same row
            name_cell = next(
                (
                    c
                    for c in sheet.magic_table_cells
                    if c.row_order == cell.row_order and c.column_order == 0
                ),
                None,
            )
            if name_cell:
                logger.info(f"Found person from New York: {name_cell.text}")

    # Get sheet metadata
    metadata = await at_service.get_sheet_metadata()
    logger.info(f"Sheet has {len(metadata)} metadata entries")


# Example 6: Using log entries for traceability
async def handle_sheet_created_with_logs(
    at_service: AgenticTableService, payload: MagicTableSheetCreatedPayload
) -> None:
    """Example showing how to add log entries to cells for tracking changes and sources."""
    logger.info(f"Sheet created with log entries: {payload.sheet_name}")

    # Add headers
    headers = ["Metric", "Value", "Source"]
    for col_idx, header in enumerate(headers):
        await at_service.set_cell(row=0, column=col_idx, text=header)

    # Add data with log entries to track the source
    metrics = [
        {
            "name": "Total Users",
            "value": "1,234",
            "source": "Analytics Dashboard",
            "log": "Retrieved from Google Analytics API at 2024-01-15 10:30 AM",
        },
        {
            "name": "Active Sessions",
            "value": "456",
            "source": "Real-time Monitor",
            "log": "Live data from monitoring service",
        },
        {
            "name": "Conversion Rate",
            "value": "3.2%",
            "source": "Marketing Report",
            "log": "Calculated from last 30 days of data",
        },
    ]

    for row_idx, metric in enumerate(metrics, start=1):
        # Add metric name
        await at_service.set_cell(row=row_idx, column=0, text=metric["name"])

        # Add value with log entry showing the source
        log_entries = [
            LogEntry(
                text=metric["log"],
                created_at=datetime.now().isoformat(),
                actor_type=LanguageModelMessageRole.ASSISTANT,
            )
        ]

        await at_service.set_cell(
            row=row_idx, column=1, text=metric["value"], log_entries=log_entries
        )

        # Add source
        await at_service.set_cell(row=row_idx, column=2, text=metric["source"])

    logger.info("Added metrics with log entries for traceability")
