from enum import StrEnum
from typing import Annotated

from pydantic import Field
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit.agentic.tools.schemas import BaseToolConfig

DEFAULT_TOOL_DESCRIPTION = """Generate a Word document (.docx) from markdown and attach it to this chat.

**When to use:** Call this tool when the user explicitly asks for a document, one-pager, summary export, or meeting prep document to download.

**Before calling:**
1. Summarize the **entire conversation history** into a single, well-structured markdown document.
2. The markdown must be a **complete, standalone document** (not a fragment). Use clear structure:
   - Headings: # for title, ## for main sections, ### for subsections
   - Bullet lists (- or *) and numbered lists (1. 2. 3.) for points
   - **Bold** and *italic* for emphasis
   - Tables with | columns | and header rows where appropriate
3. Set filename to a descriptive name with .docx extension (e.g. "Meeting Prep - Q1 Review.docx").
4. After the tool returns, include the download link using the `<sup>N</sup>` citation from the tool response (e.g. `<sup>1</sup>`). Do NOT write the filename as the link — only use the superscript number.

**Parameters:**
- markdown_content: The full markdown text of the document (you produce this from the conversation).
- filename: Output filename, must end with .docx (default: "document.docx").
""".strip()


class ExportFormat(StrEnum):
    DOCX = "docx"


class DocGeneratorToolConfig(BaseToolConfig):
    template_content_id: str = Field(
        default="",
        description=(
            "Content ID of a branded .docx template from the knowledge base. "
            "The template's styles (fonts, colors, margins, headers/footers) are "
            "applied to all generated documents. Leave empty for plain pandoc defaults."
        ),
    )

    export_format: ExportFormat = Field(
        default=ExportFormat.DOCX,
        description="Output file format for the generated document.",
    )

    tool_description: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=len(DEFAULT_TOOL_DESCRIPTION.split("\n"))),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION,
        description="Tool description shown to the language model.",
    )

    tool_format_information_for_system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=8),
    ] = Field(
        default="",
        description="Formatting instructions for the generated document appended to the system prompt.",
    )
