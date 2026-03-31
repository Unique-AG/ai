from typing import Annotated

from pydantic import Field
from pydantic.json_schema import SkipJsonSchema
from unique_toolkit.agentic.tools.schemas import BaseToolConfig

from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag

DEFAULT_TOOL_DESCRIPTION = (
    "Retrieves the list of all file names that are currently searchable "
    "in the knowledge base. "
    "Generally, this tool should be called before performing internal or web search."
)

DEFAULT_TOOL_SYSTEM_PROMPT = (
    "Use RetrieveSearchScope to determine the internally searchable files "
    "and metadata about them.\n\n"
    "**When to call the tool:**\n"
    "1. Before performing Internal Search, verify RetrieveSearchScope has been called. "
    "If not: call RetrieveSearchScope.\n"
    "2. Before performing any other search (e.g. web search) it is usually "
    "sensible to check RetrieveSearchScope to determine if internal search "
    "is the better option.\n"
    "**3. Important: Only call RetrieveSearchScope ONCE per conversation.**\n\n"
    "**How the tool works:**\n"
    "- Returns all file names that are in the currently searchable knowledge base.\n"
    "- Useful metadata is passed along with the file names, e.g. openable files "
    "come with a scope id.\n"
    "- The return is token-limited: if the file list exceeds the budget, "
    "the tail is truncated. (Currently, the files end up in the tail arbitrarily)\n\n"
    "**Use the returned file list to:**\n"
    "1. Decide whether to use Internal Search or Web Search based on whether "
    "relevant documents exist.\n"
    "**IMPORTANT: If the listed files indicate that they contain relevant information "
    "to a query: ALWAYS perform internal search.**\n"
    "2. Craft more targeted search queries using the actual file names "
    "(a file name in the query promotes chunks from that file).\n"
    "3. Inform the user about available sources when relevant.\n"
    "4. Files that come with a content id can be opened with a file opener tool."
)


class RetrieveSearchScopeConfig(BaseToolConfig):
    """Configuration for the RetrieveSearchScope tool."""

    enabled: Annotated[
        bool,
        RJSFMetaTag.BooleanWidget.checkbox(
            help=(
                "Enable the RetrieveSearchScope tool. When enabled, the agent "
                "can list all files available in the knowledge base before searching."
            ),
        ),
    ] = Field(
        default=False,
        description="Enable the RetrieveSearchScope tool.",
    )

    tool_description: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=3),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION,
        description="The tool description shown to the language model.",
    )

    tool_description_for_system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(DEFAULT_TOOL_SYSTEM_PROMPT.split("\n"))
        ),
    ] = Field(
        default=DEFAULT_TOOL_SYSTEM_PROMPT,
        description="Instructions injected into the system prompt to guide when the agent should call this tool.",
    )

    context_window_fraction_for_file_list: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Fraction of the context window reserved for the file list (default 5%).",
    )

    language_model_max_input_tokens: SkipJsonSchema[int | None] = Field(
        default=None,
        description="Language model maximum input tokens. Injected by the orchestrator at validation time.",
    )
