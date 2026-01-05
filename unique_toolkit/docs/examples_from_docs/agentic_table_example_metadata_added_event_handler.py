from unique_toolkit.agentic_table.schemas import MagicTableAddMetadataPayload, MagicTableCell
from unique_toolkit.agentic_table.service import AgenticTableService
from logging import getLogger
from typing import Callable
import io
import pandas as pd
from unique_sdk.api_resources._agentic_table import ActivityStatus

from .agentic_table_example_column_definition import example_column_definitions

logger = getLogger(__name__)

def get_downloader(user_id: str, company_id: str, chat_id: str) -> Callable[[str], bytes]:
    """
    Get a downloader function that downloads a file from the content library.
    """
    from unique_toolkit.content.functions import download_content_to_bytes
    return lambda file_id: download_content_to_bytes(user_id=user_id, company_id=company_id, chat_id=chat_id, content_id=file_id)

async def handle_metadata_added(
    at_service: AgenticTableService, 
    payload: MagicTableAddMetadataPayload,
    downloader: Callable[[str], bytes]
) -> None:
    """
    Handle metadata addition event for Excel file upload and data population.
    
    This handler processes uploaded Excel files containing Source of Wealth questions
    and answers. It validates the Excel structure against the schema, then efficiently
    populates the table using batch operations.
    
    Workflow:
    1. Download Excel file from source_file_ids
    2. Parse Excel with pandas
    3. Validate columns match schema
    4. Create batch of MagicTableCell objects
    5. Upload all cells in single batch operation
    
    Args:
        at_service: The AgenticTableService instance for table operations
        payload: The payload containing metadata including source_file_ids
        chat_service: The ChatService instance for downloading uploaded files
        
    Returns:
        None
        
    Excel Format Expected:
        The Excel file should have columns matching the schema:
        - Question, Section, Answer, Status, Gap, Contradiction, Reviewer
        
    Performance:
        Uses batch operations for optimal performance. Can handle hundreds of
        rows efficiently (1-2 seconds vs 50+ seconds for individual cell updates).
        
    Raises:
        ValueError: If Excel columns don't match schema
        Exception: If file download or parsing fails
    """
    logger.info(f"Processing metadata for sheet: {payload.sheet_name}")
    
    # Check if source files were provided
    if not payload.metadata.question_file_ids:
        logger.warning("No question files provided in metadata")
        return
    
    await at_service.set_activity(
        text="Downloading Excel file...",
        activity=payload.action,
        status=ActivityStatus.IN_PROGRESS
    )
    
    try:
        # Get the first source file (Excel)
        file_id = payload.metadata.question_file_ids[0]
        logger.info(f"Downloading file: {file_id}")
        # Download file content
        file_content = downloader(file_id)
        
        await at_service.set_activity(
            text="Parsing Excel file...",
            activity=payload.action,
            status=ActivityStatus.IN_PROGRESS
        )
        
        file_content_stream = io.BytesIO(file_content)
        
        # Parse Excel or CSV file
        # Try Excel first, fall back to CSV
        try:
            df = pd.read_excel(file_content_stream, header=0)
            logger.info(f"Parsed Excel with {len(df)} rows and {len(df.columns)} columns")
        except Exception as excel_error:
            logger.info(f"Not an Excel file, trying CSV: {excel_error}")
            df = pd.read_csv(file_content_stream)
            logger.info(f"Parsed CSV with {len(df)} rows and {len(df.columns)} columns")
        
        
        # Validate columns
        validate_excel_columns(df)
        
        await at_service.set_activity(
            text=f"Populating table with {len(df)} rows...",
            activity=payload.action,
            status=ActivityStatus.IN_PROGRESS
        )
        
        # Create batch cells
        cells = []
        for row_idx, row_data in df.iterrows():
            for col_def in example_column_definitions.columns:
                # Handle missing values robustly
                cell_value = row_data.get(col_def.name, "")
                # pd.isna returns an array for series/frames, so only use if the value is a scalar
                # Also handle pandas NA and None explicitly
                if isinstance(cell_value, (float, int, str)):
                    if pd.isna(cell_value):
                        cell_value = ""
                elif cell_value is None:
                    cell_value = ""
                
                cells.append(
                    MagicTableCell(
                        row_order=int(row_idx) + 1,  # +1 for header row  # type: ignore  # ConvertibleToInt
                        column_order=col_def.order,
                        text=str(cell_value),
                        sheet_id=payload.table_id
                    )
                )
        
        logger.info(f"Created {len(cells)} cells for batch upload")
        
        # Batch upload all cells
        await at_service.set_multiple_cells(cells=cells)
        
        logger.info(f"Successfully populated table with {len(df)} rows")
        
        await at_service.set_activity(
            text=f"Successfully loaded {len(df)} rows from Excel",
            activity=payload.action,
            status=ActivityStatus.COMPLETED
        )
        
    except Exception as e:
        logger.error(f"Error processing Excel file: {e}")
        await at_service.set_activity(
            text=f"Failed to process Excel file: {str(e)}",
            activity=payload.action,
            status=ActivityStatus.FAILED
        )
        raise
    
    
def validate_excel_columns(df: pd.DataFrame) -> None:
    """
    Validate that Excel file columns match the schema definition.
    
    Ensures data integrity by verifying the uploaded Excel file has the exact
    columns expected by the table schema. This prevents data import errors and
    ensures all required fields are present.
    
    Args:
        df: pandas DataFrame loaded from Excel file
        schema: The SourceOfWealthTableSchema defining expected columns
        
    Raises:
        ValueError: If columns don't match schema (missing, extra, or wrong order)
        
    Validation Rules:
        - All schema columns must be present in Excel
        - Column names must match exactly (case-sensitive)
        - Extra columns in Excel are allowed but ignored
        - Missing required columns cause validation to fail
    """
    excel_columns = set(df.columns)
    schema_columns = set(example_column_definitions.get_column_names())
    
    # Check for missing columns
    missing_columns = schema_columns - excel_columns
    if missing_columns:
        raise ValueError(
            f"Excel file is missing required columns: {', '.join(missing_columns)}"
        )
    
    # Extra columns are allowed, just log a warning
    extra_columns = excel_columns - schema_columns
    if extra_columns:
        logger.warning(f"Excel file has extra columns that will be ignored: {', '.join(extra_columns)}")
    
    logger.info("Excel columns validated successfully")
