from typing import Callable

from docs.examples_from_docs.agentic_table_example_column_definition import ExampleColumnNames, example_column_definitions
from unique_toolkit.agentic_table.schemas import MagicTableGenerateArtifactPayload, MagicTableSheet
from unique_toolkit.agentic_table.service import AgenticTableService
from unique_toolkit import ChatService
from unique_sdk.api_resources._agentic_table import ActivityStatus
from logging import getLogger
from datetime import datetime
from unique_toolkit._common.docx_generator import DocxGeneratorService, DocxGeneratorConfig
from unique_toolkit.content.schemas import Content
logger = getLogger(__name__)


def get_uploader(user_id: str, company_id: str, chat_id: str) -> Callable[[bytes, str, str], Content]:
    """
    Factory function to create a file uploader with authentication context.
    
    Returns a function that uploads files to the chat.
    """
    from unique_toolkit.content.functions import upload_content_from_bytes
    def uploader(content: bytes, mime_type: str, content_name: str) -> Content:
        return upload_content_from_bytes( user_id=user_id, company_id=company_id, content=content, mime_type=mime_type, content_name=content_name, chat_id=chat_id, skip_ingestion=True)
    return uploader

async def handle_artifact_generated(
    at_service: AgenticTableService,
    payload: MagicTableGenerateArtifactPayload,
    uploader: Callable[[bytes, str, str], Content]
) -> None:
    """
    Example handler for the artifact generation event.
    
    This demo shows how to export table data as a Word document:
    - Fetches all table data
    - Organizes it by sections
    - Generates a markdown report
    - Converts to DOCX and uploads it
    - Links the artifact back to the table
    
    Args:
        at_service: Service instance for table operations
        payload: Event payload with artifact type
        uploader: Function to upload the generated file
    """
    logger.info(f"Generating artifact of type: {payload.data.artifact_type}")
    
    await at_service.set_activity(
        text="Starting report generation...",
        activity=payload.action,
        status=ActivityStatus.IN_PROGRESS
    )
    
    try:
        # Read and organize data
        sheet = await at_service.get_sheet(start_row=0, end_row=None)
        rows_data = organize_sheet_data(sheet)
        
        # Build markdown report
        markdown = build_markdown_report(rows_data)
        
        # Generate DOCX
        await at_service.set_activity(
            text="Generating document...",
            activity=payload.action,
            status=ActivityStatus.IN_PROGRESS
        )
        
        docx_generator = DocxGeneratorService(
            config=DocxGeneratorConfig(
                template_content_id="content-template-generic",
            )
        )
        
        content_fields = docx_generator.parse_markdown_to_list_content_fields(markdown)
        docx_file = docx_generator.generate_from_template(content_fields)
        
        if not docx_file:
            raise Exception("Failed to generate DOCX file")
        
        # Upload to chat
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Table_Report_{timestamp}.docx"
        
        content = uploader(
            docx_file,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename,
        )
        
        # Set artifact reference
        await at_service.set_artifact(
            artifact_type=payload.data.artifact_type,
            content_id=content.id,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            name=filename
        )
        
        await at_service.set_activity(
            text=f"Report generated successfully: {filename}",
            activity=payload.action,
            status=ActivityStatus.COMPLETED
        )
        
    except Exception as e:
        logger.error(f"Error generating artifact: {e}")
        await at_service.set_activity(
            text=f"Report generation failed: {str(e)}",
            activity=payload.action,
            status=ActivityStatus.FAILED
        )
        raise

def organize_sheet_data(sheet: MagicTableSheet) -> dict[int, dict[int, str]]:
    """
    Convert flat cell list to nested dictionary structure.
    
    Returns:
        Dictionary with structure {row_order: {column_order: cell_text}}
    """
    rows_data: dict[int, dict[int, str]] = {}
    
    for cell in sheet.magic_table_cells:
        if cell.row_order not in rows_data:
            rows_data[cell.row_order] = {}
        rows_data[cell.row_order][cell.column_order] = cell.text
    
    return rows_data

def build_markdown_report(rows_data: dict[int, dict[int, str]]) -> str:
    """
    Build a markdown report grouped by sections.
    
    Returns:
        Markdown string with sections and question details
    """
    markdown_lines = [
        "# Table Report",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
    ]
    
    # Get column definitions
    question_col = example_column_definitions.get_column_by_name(ExampleColumnNames.QUESTION).order
    section_col = example_column_definitions.get_column_by_name(ExampleColumnNames.SECTION).order
    answer_col = example_column_definitions.get_column_by_name(ExampleColumnNames.ANSWER).order
    consistency_col = example_column_definitions.get_column_by_name(ExampleColumnNames.CRITICAL_CONSISTENCY).order
    status_col = example_column_definitions.get_column_by_name(ExampleColumnNames.STATUS).order
    reviewer_col = example_column_definitions.get_column_by_name(ExampleColumnNames.REVIEWER).order
    
    # Get data rows (excluding header row 0)
    data_rows = {k: v for k, v in rows_data.items() if k > 0}
    
    # Group by section
    sections: dict[str, list[dict[int, str]]] = {}
    for row_data in data_rows.values():
        section = row_data.get(section_col, "General")
        if section not in sections:
            sections[section] = []
        sections[section].append(row_data)
    
    # Add each section
    for section_name, section_rows in sections.items():
        markdown_lines.extend([
            f"## {section_name}",
            "",
        ])
        
        for row_data in section_rows:
            question = row_data.get(question_col, "N/A")
            answer = row_data.get(answer_col, "N/A")
            consistency = row_data.get(consistency_col, "N/A")
            status = row_data.get(status_col, "N/A")
            reviewer = row_data.get(reviewer_col, "Unassigned")
            
            markdown_lines.extend([
                f"**Question:** {question}",
                "",
                f"**Answer:** {answer}",
                "",
                f"**Consistency:** {consistency}",
                "",
                f"**Status:** {status}",
                "",
                f"**Reviewer:** {reviewer}",
                "",
                "---",
                "",
            ])
    
    return "\n".join(markdown_lines)

