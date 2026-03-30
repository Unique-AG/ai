from pathlib import Path

from unique_web_search.utils import load_template

_PROMPTS_DIR = Path(__file__).parent

DEFAULT_SYSTEM_PROMPT: str = load_template(_PROMPTS_DIR, "system_prompt.j2")
DEFAULT_USER_PROMPT_TEMPLATE: str = load_template(_PROMPTS_DIR, "user_prompt.j2")
DEFAULT_GUIDELINES: str = load_template(_PROMPTS_DIR, "guidelines.j2")
