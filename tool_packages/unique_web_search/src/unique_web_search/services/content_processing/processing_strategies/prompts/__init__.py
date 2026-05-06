from pathlib import Path

from unique_web_search.utils import load_template

_STRATEGIES_DIR = Path(__file__).parent

DEFAULT_SYSTEM_PROMPT_TEMPLATE: str = load_template(_STRATEGIES_DIR, "system_prompt.j2")
DEFAULT_USER_PROMPT_TEMPLATE: str = load_template(_STRATEGIES_DIR, "user_prompt.j2")
DEFAULT_SANITIZE_RULES: str = load_template(_STRATEGIES_DIR, "sanitize_rules.j2")
DEFAULT_JUDGE_PROMPT_TEMPLATE: str = load_template(_STRATEGIES_DIR, "judge_prompt.j2")
DEFAULT_JUDGE_AND_SANITIZE_PROMPT_TEMPLATE: str = load_template(
    _STRATEGIES_DIR, "judge_and_sanitize_prompt.j2"
)
DEFAULT_KEYWORD_EXTRACT_PROMPT_TEMPLATE: str = load_template(
    _STRATEGIES_DIR, "keyword_extract_prompt.j2"
)
DEFAULT_PAGE_CONTEXT_TEMPLATE: str = load_template(_STRATEGIES_DIR, "page_context.j2")
