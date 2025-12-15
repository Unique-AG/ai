from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template

_PROMPTS_DIR = Path(__file__).parent

_jinja_env = Environment(
    loader=FileSystemLoader(str(_PROMPTS_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
)

CREATE_NEW_SECTION_SYSTEM_PROMPT: Template = _jinja_env.get_template("system_prompt.j2")
CREATE_NEW_SECTION_USER_PROMPT: Template = _jinja_env.get_template("user_prompt.j2")
