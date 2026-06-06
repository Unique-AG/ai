from pathlib import Path

from unique_toolkit._common.utils.jinja.helpers import load_template

_PROMPTS_DIR = Path(__file__).parent

DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT = load_template(
    _PROMPTS_DIR, "tool_description_for_system_prompt.j2"
)

DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT = (
    "Whenever you use information retrieved with the UploadedSearch, you must adhere to strict reference guidelines. "
    "You must strictly reference each fact used with the `source_number` of the corresponding passage, in the following format: '[source<source_number>]'.\n\n"
    "Example:\n"
    "- The revenue for Q2 was $5M , while expenses were $3M .\n"
    "- The uploaded document highlights a 20% increase in productivity .\n\n"
    "A fact is preferably referenced by ONLY ONE source, e.g [sourceX], which should be the most relevant source for the fact.\n"
    "Follow these guidelines closely and be sure to use the proper `source_number` when referencing facts.\n"
    "Make sure that your reference follow the format [sourceX] and that the source number is correct.\n"
    "Source is written in singular form and the number is written in digits.\n\n"
    "IT IS VERY IMPORTANT TO FOLLOW THESE GUIDELINES!!\n"
    "NEVER CITE A source_number THAT YOU DON'T SEE IN THE TOOL CALL RESPONSE!!!\n"
    "The source_number in old assistant messages are no longer valid.\n"
    "EXAMPLE: If you see  and  in the assistant message, you can't use  again in the next assistant message, this has to be the number you find in the message with role 'tool'.\n"
    "BE AWARE: All tool calls have been filtered to remove uncited sources. Tool calls return much more data than you see.\n\n"
    "### Internal Document Answering Protocol for Uploaded Documents\n"
    "When assisting users with uploaded documents, follow\n"
    "this structured approach to ensure precise, well-grounded,\n"
    "and context-aware responses:\n\n"
    "#### 1. Locate and Prioritize Relevant Information\n"
    "Focus on the **most relevant sections** of the uploaded document.\n"
    "Prioritize documents that are:\n"
    "- **Directly referenced by the user** (e.g., by name or context).\n"
    "- **Recently uploaded** or actively discussed.\n\n"
    "#### 2. Source Reliability Guidelines\n"
    "- Prioritize information that is:\n"
    "  - **Clearly stated in the document**.\n"
    "  - **Part of finalized or approved sections**.\n"
    "- Be cautious with:\n"
    "  - Drafts or incomplete sections.\n"
    "  - Ambiguous or conflicting information.\n\n"
    "#### 3. Acknowledge Limitations\n"
    "- If no relevant information is found, or the document is unclear, state this explicitly.\n"
    "- Indicate where further clarification or investigation may be required."
)

DEFAULT_TOOL_DESCRIPTION = "Search within uploaded documents for information on policies, procedures, benefits, projects, or specific details. This tool is ideal for analyzing user-uploaded files and extracting relevant insights."
DEFAULT_SEARCH_STRING_PARAM_DESCRIPTION = "An expanded term optimized for vector and full-text search based on the user’s query. It must be in English."
DEFAULT_LANGUAGE_PARAM_DESCRIPTION = (
    "The language in which the user’s query is written."
)
