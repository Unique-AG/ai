import io
from logging import getLogger
from typing import Callable

import pandas as pd
from unique_sdk.api_resources._agentic_table import ActivityStatus

from unique_toolkit.agentic_table.schemas import (
    MagicTableAddMetadataPayload,
    MagicTableCell,
)
from unique_toolkit.agentic_table.service import AgenticTableService
from unique_toolkit.content import Content, ContentChunk

from .agentic_table_example_column_definition import (
    ExampleColumnNames,
    example_column_definitions,
)
from .agentic_table_helper_functions import ContentRegistry, create_id_map

logger = getLogger(__name__)


async def handle_question_files(
    at_service: AgenticTableService,
    payload: MagicTableAddMetadataPayload,
    downloader_fn: Callable[[str], bytes],
) -> int:
    """
    Handle question files by downloading and parsing CSV to populate the table.

    Args:
        at_service: Service instance for table operations
        payload: Event payload with metadata and file IDs
        downloader_fn: Function to download file contents

    Returns:
        Number of rows added to the table

    Raises:
        Exception: If CSV processing fails
    """
    # Check if question files were provided
    if not payload.metadata.question_file_ids:
        logger.warning("No question files provided in metadata")
        return 0

    await at_service.set_activity(
        text="Downloading CSV file...",
        activity=payload.action,
        status=ActivityStatus.IN_PROGRESS,
    )

    # Get the first question file (CSV)
    file_id = payload.metadata.question_file_ids[0]

    logger.info(f"Downloading file: {file_id}")
    # Download file content
    file_content = downloader_fn(file_id)

    await at_service.set_activity(
        text="Parsing CSV file...",
        activity=payload.action,
        status=ActivityStatus.IN_PROGRESS,
    )

    file_content_stream = io.BytesIO(file_content)

    # Parse CSV file
    df = pd.read_csv(file_content_stream)
    df = df.fillna("")  # Convert NA values to empty strings
    logger.info(f"Parsed CSV with {len(df)} rows and {len(df.columns)} columns")
    logger.info(df.head())

    await at_service.set_activity(
        text=f"Populating table with {len(df)} rows...",
        activity=payload.action,
        status=ActivityStatus.IN_PROGRESS,
    )

    # Create batch cells
    cells = []
    for row_idx, row_data in df.iterrows():
        for col_def in example_column_definitions.columns:
            cell_value = row_data.get(col_def.name.value, "")
            if not cell_value:
                continue
            cells.append(
                MagicTableCell(
                    row_order=int(row_idx)  # type: ignore[arg-type]
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

    return len(df)


async def handle_source_files(
    at_service: AgenticTableService,
    payload: MagicTableAddMetadataPayload,
    file_content_getter_fn: Callable[[str], Content | None],
    augmented_text_with_references_fn: Callable[
        [str, dict[str, Content | ContentChunk], str, str], str
    ],
) -> int:
    """
    Handle source files by retrieving content and organizing by metadata.
    
    This handler demonstrates two key framework capabilities:
    1. Retrieving file content and accessing metadata
    2. Creating clickable references that link table cells to source documents
    
    The example shows:
    - How to fetch Content objects for uploaded files
    - How to use ContentRegistry to group files by metadata keys
    - How to generate text with inline citations and convert them to clickable references
    - How to populate table cells with referenced content

    Args:
        at_service: Service instance for table operations
        payload: Event payload with metadata and file IDs
        file_content_getter_fn: Function to retrieve file content objects
        augmented_text_with_references_fn: Function to convert citations to references

    Returns:
        Number of content items processed
    """
    # Check if source files were provided
    if not payload.metadata.source_file_ids:
        logger.warning("No source files provided in metadata")
        return 0

    await at_service.set_activity(
        text="Processing source files metadata...",
        activity=payload.action,
        status=ActivityStatus.IN_PROGRESS,
    )
    cells_to_update: list[MagicTableCell] = []

    num_rows = await at_service.get_num_rows()

    # STEP 1: Retrieve Content objects for all source files
    # Each Content object contains:
    # - content.id: Unique identifier
    # - content.metadata: Custom key-value pairs (e.g., {"section": "Finance"})
    # - content.title: File name or title
    # - content.text: Extracted text content
    # - content.chunks: List of ContentChunk objects for chunked documents
    all_contents = []
    for file_id in payload.metadata.source_file_ids:
        content = file_content_getter_fn(file_id)
        if content is None:
            logger.warning(f"No content found for file: {file_id}")
            continue
        if content.metadata is None:
            logger.warning(f"No metadata found for file: {file_id}")
            continue
        all_contents.append(content)

    # STEP 2: Organize content by metadata keys
    # This example assumes source files have metadata like:
    # {"Team": "true"}, {"Finance": "true"}, {"Technical": "true"}, etc.
    sections_of_interest = [
        "Team",
        "Finance",
        "Technical",
        "Planning",
    ]

    # ContentRegistry groups files by metadata keys
    # You can later retrieve all files tagged with "Finance", "Team", etc.
    content_registry = ContentRegistry(keys=sections_of_interest, contents=all_contents)

    # STEP 3: Process each row in the table
    # This demonstrates row-by-row processing where each row might need different source files
    for row_index in range(1, num_rows + 1):
        # Retrieve the current row to check what data it has
        row_cells = await at_service.get_sheet(
            start_row=row_index, end_row=row_index + 1
        )
        retrieved_cells: dict[ExampleColumnNames, MagicTableCell] = {
            example_column_definitions.get_column_name_by_order(cell.column_order): cell
            for cell in row_cells.magic_table_cells
        }

        logger.info(f"Retrieved cells: {retrieved_cells}")

        answer_cell = retrieved_cells.get(ExampleColumnNames.ANSWER)

        # Check if the answer cell exists. This means that the answer was already generated.
        if answer_cell is not None:
            logger.info(f"Answer found for row {row_index}: {answer_cell.text}")
        else:
            # Get the section for this row (e.g., "Finance", "Team")
            section_name = retrieved_cells.get(ExampleColumnNames.SECTION)
            
            if section_name is None:
                logger.warning(f"No section found for row {row_index}")
                continue

            # STEP 4: Retrieve relevant content based on row metadata
            # Use the ContentRegistry to get all files tagged with this section
            relevant_contents = content_registry.get_contents_by_metadata_key(
                section_name.text
            )
            
            if len(relevant_contents) == 0:
                logger.warning(f"No contents found for section '{section_name}'")
                continue

            logger.info(
                f"Found {len(relevant_contents)} content items for section '{section_name}'"
            )

            # STEP 5: Create a reference registry for citation mapping
            # This creates temporary IDs like "chunk_a1b2c3d4" for each content item
            # These IDs will be used in inline citations: [chunk_a1b2c3d4]
            chunk_prefix = "chunk"
            reference_registry = create_id_map(relevant_contents, chunk_prefix)
            
            logger.info(f"Reference registry: {reference_registry.keys()}")

            # STEP 6: Generate text with inline citations
            # In a real application, this would be AI-generated text with citations
            # Here we simulate it by listing the content titles with citation markers
            simulated_text_generation_with_references = (
                "The following are the contents of the section: \n"
            )
            for chunk_id, content in reference_registry.items():
                # Add inline citation in format [chunk_xxx]
                simulated_text_generation_with_references += (
                    f"{content.title} [{chunk_id}]\n"
                )

            # STEP 7: Convert inline citations to clickable references
            # This transforms [chunk_a1b2c3d4] into numbered references like [1], [2]
            # The frontend will render these as clickable links to the source files
            augmented_text = augmented_text_with_references_fn(
                simulated_text_generation_with_references,
                reference_registry,  # type: ignore[arg-type]
                chunk_prefix,
                r"\[chunk_([a-zA-Z0-9\-]+)\]",  # Citation pattern to match
            )
            
            # STEP 8: Update the table cell with referenced text
            cells_to_update.append(
                MagicTableCell(
                    row_order=row_index,
                    column_order=example_column_definitions.get_column_by_name(
                        ExampleColumnNames.ANSWER
                    ).order,
                    text=augmented_text,
                    sheet_id=payload.table_id,
                )
            )

    # Apply any cell updates
    if cells_to_update:
        await at_service.set_multiple_cells(cells=cells_to_update)

    await at_service.set_activity(
        text=f"Successfully processed {len(all_contents)} source files",
        activity=payload.action,
        status=ActivityStatus.COMPLETED,
    )

    return len(all_contents)


async def handle_metadata_added(
    at_service: AgenticTableService,
    payload: MagicTableAddMetadataPayload,
    downloader_fn: Callable[[str], bytes],
    file_content_getter_fn: Callable[[str], Content | None],
    augmented_text_with_references_fn: Callable[
        [str, dict[str, Content | ContentChunk], str, str], str
    ],
) -> None:
    """
    Example handler for the metadata addition event.

    This demo shows how to populate a table from uploaded files:
    - Process question files: Downloads CSV files and populates the table
    - Process source files: Retrieves content and groups by metadata

    Args:
        at_service: Service instance for table operations
        payload: Event payload with metadata and file IDs
        downloader_fn: Function to download file contents
        file_content_getter_fn: Function to retrieve file content objects
    """
    logger.info(f"Processing metadata for sheet: {payload.sheet_name}")

    try:
        # Handle question files (CSV processing)
        num_question_rows = await handle_question_files(
            at_service=at_service,
            payload=payload,
            downloader_fn=downloader_fn,
        )

        # Handle source files (content and metadata processing)
        num_source_rows = await handle_source_files(
            at_service=at_service,
            payload=payload,
            file_content_getter_fn=file_content_getter_fn,
            augmented_text_with_references_fn=augmented_text_with_references_fn,
        )

        # This is different from the LogEntry which shows in the cell history
        await at_service.set_activity(
            text=f"Successfully loaded {num_question_rows} rows from CSV and {num_source_rows} source file metadata rows",
            activity=payload.action,
            status=ActivityStatus.COMPLETED,
        )

    except Exception as e:
        logger.exception(f"Error processing files: {e}", exc_info=True)
        await at_service.set_activity(
            text=f"Failed to process files: {str(e)}",
            activity=payload.action,
            status=ActivityStatus.FAILED,
        )
        raise
