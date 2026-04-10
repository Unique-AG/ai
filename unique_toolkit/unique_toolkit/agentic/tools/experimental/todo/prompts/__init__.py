from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def _load(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text().strip()


TOOL_DESCRIPTION_TEMPLATE = _load("tool_description.j2")
SYSTEM_PROMPT_TEMPLATE = _load("system_prompt.j2")
EXECUTION_REMINDER_TEMPLATE = _load("execution_reminder.j2")
