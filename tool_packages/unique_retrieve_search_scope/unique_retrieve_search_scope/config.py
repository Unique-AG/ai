from pydantic import Field

from unique_toolkit.agentic.tools.schemas import BaseToolConfig

DEFAULT_TOOL_DESCRIPTION = (
    "Retrieves the list of all file names currently searchable in the knowledge base search scope. "
    "This tool MUST be called before performing any search (Internal or Web) to determine the adequacy of internal resources (which are prefered to web search)."
)

DEFAULT_TOOL_SYSTEM_PROMPT = (
    "**IMPORTANT: Before performing any Search (Internal or Web), you MUST first call RetrieveSearchScope** "
    "to see which files are available in the knowledge base. Use the returned file list to:\n"
    "1. Decide whether to use Internal Search or Web Search based on whether relevant documents exist.\n"
    "2. Craft more targeted search queries using the actual file names.\n"
    "3. Inform the user about available sources when relevant.\n\n"
    "You only need to call RetrieveSearchScope once per conversation unless the user asks about different topics "
    "that might require re-checking the scope."
)


class RetrieveSearchScopeConfig(BaseToolConfig):
    tool_description: str = Field(
        default=DEFAULT_TOOL_DESCRIPTION,
        description="Tool description shown to the language model.",
    )
    tool_description_for_system_prompt: str = Field(
        default=DEFAULT_TOOL_SYSTEM_PROMPT,
        description="Instructions injected into the system prompt to guide when the agent should call this tool.",
    )
