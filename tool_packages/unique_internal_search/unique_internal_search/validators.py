import enum
import re
from string import Template
from typing import Any

from pydantic import (
    Field,
)


class PromptTemplatingEngine(enum.Enum):
    STRING_TEMPLATE = enum.auto()


def check_placeholder_valid(
    placeholder: str,
    templating_engine: PromptTemplatingEngine = PromptTemplatingEngine.STRING_TEMPLATE,
) -> bool:
    match templating_engine:
        case PromptTemplatingEngine.STRING_TEMPLATE:
            return (
                re.fullmatch(Template.idpattern, placeholder, re.IGNORECASE) is not None
            )


def get_prompt_placeholder_regexp(
    *placeholders: str,
    templating_engine: PromptTemplatingEngine = PromptTemplatingEngine.STRING_TEMPLATE,
) -> re.Pattern:
    for placeholder in placeholders:
        if not check_placeholder_valid(placeholder, templating_engine):
            raise ValueError(f"Invalid placeholder: {placeholder}")

    match templating_engine:
        case PromptTemplatingEngine.STRING_TEMPLATE:
            placeholder_patterns = [
                rf"(?=.*(?:\$\{{{p}\}}|\${p}))" for p in placeholders
            ]
            pattern = "".join(placeholder_patterns)
            return re.compile(pattern, re.DOTALL)
        # We will add other templating engines here, such as Jinja2.


def get_prompt_placeholder_regexp_from_text(
    text: str,
    templating_engine: PromptTemplatingEngine = PromptTemplatingEngine.STRING_TEMPLATE,
) -> re.Pattern:
    match templating_engine:
        case PromptTemplatingEngine.STRING_TEMPLATE:
            return get_prompt_placeholder_regexp(
                *Template(text).get_identifiers(),
                templating_engine=templating_engine,
            )


def get_string_field_with_pattern_validation(
    prompt_template: str,
    templating_engine: PromptTemplatingEngine = PromptTemplatingEngine.STRING_TEMPLATE,
    **kwargs,
) -> Any:
    """Create a Pydantic Field with validation for prompt template placeholders.

    Args:
        prompt_template: The prompt template string containing placeholders.
        templating_engine: The engine used for template processing. Defaults to STRING_TEMPLATE.
        **kwargs: Additional keyword arguments to pass to pydantic.Field.
                  Note that `default` will be ignored if present.

    Returns:
        pydantic.FieldInfo: A FieldInfo instance with the default value and placeholder validation pattern.

    Example:
        class ServiceConfig(BaseModel):
            prompt: str = get_prompt_field_from_default(
                "Hello ${name}!"
            ) # Creates a Field with pattern validation for the "name" placeholder
    """
    pattern = get_prompt_placeholder_regexp_from_text(
        prompt_template, templating_engine
    )
    if pattern.pattern:
        kwargs["pattern"] = pattern

    kwargs["default"] = prompt_template

    return Field(**kwargs)
