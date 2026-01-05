"""
Agentic Table Artifact Generated Handler Examples

This file demonstrates how to handle artifact generation events in the Agentic Table,
such as when a report generation button is clicked.
"""

from unique_toolkit.agentic_table.schemas import (
    MagicTableEvent,
    MagicTableGenerateArtifactPayload,
    ArtifactType,
    MagicTableSheet,
)
from unique_toolkit import ChatService
from unique_toolkit.agentic_table.service import AgenticTableService
from unique_sdk.api_resources._agentic_table import ActivityStatus
from unique_toolkit._common.docx_generator import DocxGeneratorService, DocxGeneratorConfig
from logging import getLogger
import asyncio

logger = getLogger(__name__)


async def artifact_generated_handler(
    at_service: AgenticTableService, payload: MagicTableGenerateArtifactPayload, chat_service: ChatService
) -> None:
    """
    Handle artifact generation events (report generation).
    
    This demonstrates how to:
    - Check the artifact type
    - Read sheet data
    - Generate a report/artifact
    - Upload the artifact
    - Show activity status during generation
    """
    logger.info(f"Generating artifact of type: {payload.data.artifact_type}")
    
    # Set activity status to show we're generating
    await at_service.set_activity(
        text="Starting artifact generation...",
        activity=payload.action,
        status=ActivityStatus.IN_PROGRESS
    )
    
    try:
        # Get all sheet data
        sheet = await at_service.get_sheet(start_row=0, end_row=None)
        logger.info(f"Retrieved {len(sheet.magic_table_cells)} cells from sheet")
        
        # Generate artifact based on type
        if payload.data.artifact_type == ArtifactType.QUESTIONS:
            await _generate_questions_artifact(at_service, sheet, payload)
        elif payload.data.artifact_type == ArtifactType.FULL_REPORT:
            await _generate_full_report_artifact(at_service, sheet, payload, chat_service)
        else:
            logger.error(f"Unknown artifact type: {payload.data.artifact_type}")
            await at_service.set_activity(
                text=f"Unknown artifact type: {payload.data.artifact_type}",
                activity=payload.action,
                status=ActivityStatus.FAILED
            )
            return
        
        # Set activity to completed
        await at_service.set_activity(
            text="Artifact generation completed successfully!",
            activity=payload.action,
            status=ActivityStatus.COMPLETED
        )
        
    except Exception as e:
        logger.error(f"Error generating artifact: {e}")
        await at_service.set_activity(
            text=f"Artifact generation failed: {str(e)}",
            activity=payload.action,
            status=ActivityStatus.FAILED
        )


async def _generate_questions_artifact(at_service, sheet, payload):
    """Generate a questions-only artifact."""
    await at_service.set_activity(
        text="Extracting questions from sheet...",
        activity=payload.action,
        status=ActivityStatus.IN_PROGRESS
    )
    
    await asyncio.sleep(0.5)  # Simulate processing
    
    # Extract questions from column 0
    questions = []
    for cell in sheet.magic_table_cells:
        if cell.column_order == 0 and cell.row_order > 0:  # Skip header
            questions.append(cell.text)
    
    logger.info(f"Extracted {len(questions)} questions")
    
    # In a real implementation, you would:
    # 1. Generate a document/file with the questions
    # 2. Upload it to the content system
    # 3. Call at_service.set_artifact() with the content_id
    
    # Example (pseudo-code):
    # content_id = await upload_questions_document(questions)
    # await at_service.set_artifact(
    #     artifact_type=ArtifactType.QUESTIONS,
    #     content_id=content_id,
    #     mime_type="application/pdf",
    #     name="Questions Report.pdf"
    # )
    
    
    logger.info("Questions artifact generated")


async def _generate_full_report_artifact(at_service: AgenticTableService, sheet: MagicTableSheet, payload: MagicTableGenerateArtifactPayload, chat_service: ChatService):
    """Generate a full report artifact with all data."""
    await at_service.set_activity(
        text="Generating comprehensive report...",
        activity=payload.action,
        status=ActivityStatus.IN_PROGRESS
    )
    
    await asyncio.sleep(1)  # Simulate processing
    
    # Organize data by rows
    rows = {}
    for cell in sheet.magic_table_cells:
        if cell.row_order not in rows:
            rows[cell.row_order] = {}
        rows[cell.row_order][cell.column_order] = cell.text
    
    logger.info(f"Organized data into {len(rows)} rows")
    
    # In a real implementation, you would:
    # 1. Generate a comprehensive report with all the data
    # 2. Upload it to the content system
    # 3. Call at_service.set_artifact() with the content_id
    
    # Example (pseudo-code):
    # content_id = await upload_full_report(rows)
    # await at_service.set_artifact(
    #     artifact_type=ArtifactType.FULL_REPORT,
    #     content_id=content_id,
    #     mime_type="application/pdf",
    #     name="Full Report.pdf"
    # )
    
    await _example_generate_report_with_docx_generator(at_service, ArtifactType.FULL_REPORT, chat_service)
    
    logger.info("Full report artifact generated")


async def _example_generate_report_with_docx_generator(at_service: AgenticTableService, artifact_type: ArtifactType, chat_service: ChatService):
    docx_generator_service = DocxGeneratorService(
        config=DocxGeneratorConfig(
            template_content_id="content-123",
        )
    )
    markdown_content = (
        "# Hellow World\n"
        "This is a test markdown content.\n"
        "- Item 1\n"
        "- Item 2\n"
        "- Item 3\n"
        "## Subsection 1\n"
        "This is a test subsection.\n"
        "- Item 1\n"
        "- Item 2\n"
        "- Item 3\n"
        "## Subsection 2\n"
        "This is a test subsection 2.\n"
        "- Item 1\n"
        "- Item 2\n"
        "- Item 3\n"
    )
    
    content = docx_generator_service.parse_markdown_to_list_content_fields(markdown_content)
    docx_file = docx_generator_service.generate_from_template(content)
    
    if not docx_file:
        raise Exception("Failed to generate report with docx generator")
    
    content = chat_service.upload_to_chat_from_bytes(
        content=docx_file,
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        content_name="Full Report.docx"
    )
    
    await at_service.set_artifact(
        artifact_type=artifact_type,
        content_id=content.id,
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        name="Full Report.docx"
    )
    
    logger.info(f"Report generated and uploaded to chat: {content.id}")