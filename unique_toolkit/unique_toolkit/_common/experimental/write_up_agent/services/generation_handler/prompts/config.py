from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field

from unique_toolkit._common.experimental.write_up_agent.utils import template_loader
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

PARENT_DIR = Path(__file__).parent

_SYSTEM_PROMPT_TEMPLATE = template_loader(PARENT_DIR, "system_prompt.j2")
_USER_PROMPT_TEMPLATE = template_loader(PARENT_DIR, "user_prompt.j2")


class GenerationHandlerPromptsConfig(BaseModel):
    model_config = get_configuration_dict()

    system_prompt_template: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(_SYSTEM_PROMPT_TEMPLATE.split("\n"))
        ),
    ] = Field(
        default=_SYSTEM_PROMPT_TEMPLATE,
        description="The system prompt for the source selection.",
    )
    user_prompt_template: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=len(_USER_PROMPT_TEMPLATE.split("\n"))),
    ] = Field(
        default=_USER_PROMPT_TEMPLATE,
        description="The user prompt for the source selection.",
    )
