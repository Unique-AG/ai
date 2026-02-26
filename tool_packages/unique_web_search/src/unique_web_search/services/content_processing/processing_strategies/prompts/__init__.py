from pathlib import Path

from unique_web_search.utils import load_template

_STRATEGIES_DIR = Path(__file__).parent

DEFAULT_SYSTEM_PROMPT_TEMPLATE: str = load_template(_STRATEGIES_DIR, "system_prompt.j2")
DEFAULT_USER_PROMPT_TEMPLATE: str = load_template(_STRATEGIES_DIR, "user_prompt.j2")
DEFAULT_SANITIZE_RULES: str = load_template(_STRATEGIES_DIR, "sanitize_rules.j2")
