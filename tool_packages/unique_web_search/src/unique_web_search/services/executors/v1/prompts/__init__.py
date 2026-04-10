from pathlib import Path

from unique_web_search.utils import load_template

_PROMPTS_DIR = Path(__file__).parent

DEFAULT_TOOL_DESCRIPTION: str = load_template(_PROMPTS_DIR, "tool_description.j2")
DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT: str = load_template(
    _PROMPTS_DIR, "tool_description_for_system_prompt.j2"
)
REFINE_QUERY_SYSTEM_PROMPT: str = load_template(
    _PROMPTS_DIR, "refine_query_system_prompt.j2"
)
RESTRICT_DATE_DESCRIPTION: str = load_template(
    _PROMPTS_DIR, "restrict_date_description.j2"
)
