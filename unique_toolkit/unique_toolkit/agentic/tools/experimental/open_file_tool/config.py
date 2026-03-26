from typing import Annotated

from pydantic import Field

from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit.agentic.tools.schemas import BaseToolConfig

DEFAULT_TOOL_DESCRIPTION = """Open one or more documents so you can read and reason over their full content. ALWAYS call this tool for any file you want to answer questions about — the text chunks from InternalSearch are lossy extracts and miss tables, charts, layout, and context. Opening the full file gives you far superior information.
"""

DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT = """When the user asks you to work with, analyze, summarize, or reason over a document, you MUST open it with OpenFile before answering. The text chunks returned by InternalSearch are extracted fragments — they lose tables, charts, formatting, and cross-page context. Opening the full file gives you the complete document with all visual and structural information intact.

Workflow:
1. Use InternalSearch to find relevant documents and identify their content_ids.
2. Call OpenFile with the content_ids of the files you need.
3. The full files will be available in the next iteration for you to read.
4. Answer the user's question using the full file content, referencing the InternalSearch source numbers for citations.

You should still cite source numbers from InternalSearch in your answer (e.g. [source0]), but base your reasoning on the full opened file when available.
"""

DEFAULT_TOOL_PARAMETER_CONTENT_IDS_DESCRIPTION = """List of content_ids of the documents to open. Each content_id is found in search results as the 'content_id' field (starts with 'cont_')."""


class OpenFileToolConfig(BaseToolConfig):
    """Configuration for the OpenFile tool."""

    enabled: Annotated[
        bool,
        RJSFMetaTag.BooleanWidget.checkbox(
            help=(
                "Master switch for all Open File Tool. When disabled, "
                "none of the other flags in this config block take effect."
            ),
        ),
    ] = Field(
        default=False,
        description="Enable the Open File Tool.",
    )

    send_files_in_payload: Annotated[
        bool,
        RJSFMetaTag.BooleanWidget.checkbox(
            help=(
                "Enable the OpenFile tool for knowledge-base files. When the agent "
                "finds files via InternalSearch, it can call OpenFile with the "
                "content_id to include the full document in the LLM context "
                "(unique://content/<id> URLs, resolved to base64 by the backend). "
                "Only takes effect when use_responses_api is also True."
            ),
        ),
    ] = Field(
        default=False,
        description="Enable the OpenFile tool for knowledge-base files.",
    )

    send_uploaded_files_in_payload: Annotated[
        bool,
        RJSFMetaTag.BooleanWidget.checkbox(
            help=(
                "Attach uploaded files directly to the LLM payload as full "
                "documents (unique://content/<id> URLs, resolved to base64 by the "
                "backend). When enabled, uploaded files bypass InternalSearch and "
                "are included automatically from iteration 1. "
                "Only takes effect when use_responses_api is also True."
            ),
        ),
    ] = Field(
        default=False,
        description="Attach uploaded files directly to the LLM payload.",
    )

    tool_description: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=3),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION,
        description="The description of the tool that will be included in the system prompt.",
    )

    tool_description_for_system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=7),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
        description="The description of the tool that will be included in the system prompt.",
    )

    tool_parameter_description_content_ids: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(DEFAULT_TOOL_PARAMETER_CONTENT_IDS_DESCRIPTION.split("\n"))
        ),
    ] = Field(
        default=DEFAULT_TOOL_PARAMETER_CONTENT_IDS_DESCRIPTION,
        description="The description of the tool parameter 'content_ids'.",
    )
