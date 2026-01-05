"""
Agentic Table Metadata Added Handler Examples

This file demonstrates how to handle metadata additions in the Agentic Table,
such as when questions or source files are added.
"""

from unique_toolkit.agentic_table.schemas import MagicTableAddMetadataPayload
from unique_toolkit.agentic_table.service import AgenticTableService
from logging import getLogger

logger = getLogger(__name__)


async def metadata_added_handler(
    at_service: AgenticTableService, payload: MagicTableAddMetadataPayload
) -> None:
    """
    Handle metadata addition events (questions, files added to the table).
    
    This demonstrates how to:
    - Read metadata from the payload
    - Add rows to the table based on new questions
    - Populate cells with question data
    """
    logger.info(f"Metadata added to sheet: {payload.sheet_name}")
    
    # Access the metadata
    metadata = payload.metadata
    
    # Log what was added
    if metadata.question_texts:
        logger.info(f"Added {len(metadata.question_texts)} questions")
    if metadata.question_file_ids:
        logger.info(f"Added {len(metadata.question_file_ids)} question files")
    if metadata.source_file_ids:
        logger.info(f"Added {len(metadata.source_file_ids)} source files")
    
    # Example: Add rows for each new question
    if metadata.question_texts:
        # Get current number of rows to know where to start adding
        num_rows = await at_service.get_num_rows()
        
        # Add a row for each question
        for idx, question_text in enumerate(metadata.question_texts):
            row_number = num_rows + idx
            
            # Add question to column 0
            await at_service.set_cell(row=row_number, column=0, text=question_text)
            
            # Add placeholder for answer in column 1
            await at_service.set_cell(row=row_number, column=1, text="Pending")
            
            # Add source reference if available
            if idx < len(metadata.source_file_ids):
                source_file_id = metadata.source_file_ids[idx]
                await at_service.set_cell(row=row_number, column=2, text=f"Source: {source_file_id}")
        
        logger.info(f"Added {len(metadata.question_texts)} rows to the table")
    
    # Example: Handle context if provided
    if metadata.context:
        logger.info(f"Context provided: {metadata.context}")
        # You could use this context for processing or display purposes

