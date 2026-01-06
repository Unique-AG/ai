from unique_toolkit.agentic_table.schemas import (
    MagicTableAddMetadataPayload,
    MagicTableCell,
)
from unique_toolkit.agentic_table.service import AgenticTableService
from logging import getLogger
from typing import Callable
import io
import pandas as pd
from unique_sdk.api_resources._agentic_table import ActivityStatus

from .agentic_table_example_column_definition import example_column_definitions

logger = getLogger(__name__)


def get_downloader(
    user_id: str, company_id: str, chat_id: str
) -> Callable[[str], bytes]:
    """
    Factory function to create a file downloader with authentication context.

    Returns a function that downloads files by content_id.
    """
    from unique_toolkit.content.functions import download_content_to_bytes

    return lambda file_id: download_content_to_bytes(
        user_id=user_id, company_id=company_id, chat_id=chat_id, content_id=file_id
    )


async def handle_metadata_added(
    at_service: AgenticTableService,
    payload: MagicTableAddMetadataPayload,
    downloader: Callable[[str], bytes],
) -> None:
    """
    Example handler for the metadata addition event.

    This demo shows how to populate a table from an uploaded CSV file:
    - Downloads the file from the question_file_ids
    - Parses with pandas (only CSV is supported)
    - Batch uploads all cells to the table

    Args:
        at_service: Service instance for table operations
        payload: Event payload with metadata and file IDs
        downloader: Function to download file contents
    """
    logger.info(f"Processing metadata for sheet: {payload.sheet_name}")

    # Check if question files were provided
    if not payload.metadata.question_file_ids:
        logger.warning("No question files provided in metadata")
        return
    # Note: You can also create your own condition based on the source files: payload.metadata.source_file_ids

    await at_service.set_activity(
        text="Downloading CSV file...",
        activity=payload.action,
        status=ActivityStatus.IN_PROGRESS,
    )

    try:
        # Get the first question file (Excel)
        file_id = payload.metadata.question_file_ids[0]

        logger.info(f"Downloading file: {file_id}")
        # Download file content
        file_content = downloader(file_id)

        await at_service.set_activity(
            text="Parsing CSV file...",
            activity=payload.action,
            status=ActivityStatus.IN_PROGRESS,
        )

        file_content_stream = io.BytesIO(file_content)

        # Parse CSV file
        df = pd.read_csv(file_content_stream)
        logger.info(f"Parsed CSV with {len(df)} rows and {len(df.columns)} columns")

        await at_service.set_activity(
            text=f"Populating table with {len(df)} rows...",
            activity=payload.action,
            status=ActivityStatus.IN_PROGRESS,
        )

        # Create batch cells
        cells = []
        for row_idx, row_data in df.iterrows():
            for col_def in example_column_definitions.columns:
                cell_value = row_data.get(col_def.name, "")
                cells.append(
                    MagicTableCell(
                        row_order=int(row_idx) # type: ignore[arg-type]
                        + 1,  # +1 for header row  
                        column_order=col_def.order,
                        text=str(cell_value),
                        sheet_id=payload.table_id,
                    )
                )

        logger.info(f"Created {len(cells)} cells for batch upload")

        # Batch upload all cells
        await at_service.set_multiple_cells(cells=cells)

        logger.info(f"Successfully populated table with {len(df)} rows")

        # Setting the activity to update the user on the status operation with a popup banner
        # This is different from the LogEntry which shows in the cell history
        await at_service.set_activity(
            text=f"Successfully loaded {len(df)} rows from Excel",
            activity=payload.action,
            status=ActivityStatus.COMPLETED,
        )

    except Exception as e:
        logger.error(f"Error processing CSV file: {e}")
        await at_service.set_activity(
            text=f"Failed to process CSV file: {str(e)}",
            activity=payload.action,
            status=ActivityStatus.FAILED,
        )
        raise
