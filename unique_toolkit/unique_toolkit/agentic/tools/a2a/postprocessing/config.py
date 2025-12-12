import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from unique_toolkit._common.pydantic_helpers import get_configuration_dict


class SubAgentResponseDisplayMode(StrEnum):
    HIDDEN = "hidden"
    DETAILS_OPEN = "details_open"
    DETAILS_CLOSED = "details_closed"
    PLAIN = "plain"


class SubAgentAnswerSubstringConfig(BaseModel):
    model_config = get_configuration_dict()

    regexp: re.Pattern[str] = Field(
        description="The regular expression to use to extract the substring. The first capture group will always be used.",
    )
    display_template: str = Field(
        default="{}",
        description="The template to use to display the substring. It should contain exactly one empty placeholder '{}' for the substring.",
    )


_ANSWER_SUBSTRINGS_JINJA_TEMPLATE = """
{% for substring in substrings %}
{{ substring }}
{% endfor %}
""".strip()


class SubAgentDisplayConfig(BaseModel):
    model_config = get_configuration_dict()

    mode: SubAgentResponseDisplayMode = Field(
        default=SubAgentResponseDisplayMode.HIDDEN,
        description="Controls how to display the sub agent response.",
    )
    remove_from_history: bool = Field(
        default=True,
        description="If set, sub agent responses will be removed from the history on subsequent calls to the assistant.",
    )
    add_quote_border: bool = Field(
        default=True,
        description="If set, a quote border is added to the left of the sub agent response.",
    )
    add_block_border: bool = Field(
        default=False,
        description="If set, a block border is added around the sub agent response.",
    )
    display_title_template: str = Field(
        default="Answer from <strong>{}</strong>",
        description=(
            "The template to use for the display title of the sub agent response."
            "If a placeholder '{}' is present, it will be replaced with the display name of the sub agent."
        ),
    )
    position: Literal["before", "after"] = Field(
        default="before",
        description="The position of the sub agent response in the main agent response.",
    )
    force_include_references: bool = Field(
        default=False,
        description="If set, the sub agent references will be added to the main agent response references even if not mentioned in the main agent response text.",
    )

    answer_substrings_config: list[SubAgentAnswerSubstringConfig] = Field(
        default=[],
        description="If set, only parts of the answer matching the provided regular expressions will be displayed.",
    )
    answer_substrings_jinja_template: str = Field(
        default=_ANSWER_SUBSTRINGS_JINJA_TEMPLATE,
        description="The template to use in order to format the different answer substrings, if any.",
    )
