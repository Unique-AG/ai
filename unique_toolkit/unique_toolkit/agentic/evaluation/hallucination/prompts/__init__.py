from pathlib import Path

from unique_toolkit.agentic.evaluation.utils import load_template

HALLUCINATION_PROMPTS_DIR = Path(__file__).parent


def system_prompt_loader():
    return load_template(HALLUCINATION_PROMPTS_DIR, "system_prompt.j2")


def user_prompt_loader():
    return load_template(HALLUCINATION_PROMPTS_DIR, "user_prompt.j2")
