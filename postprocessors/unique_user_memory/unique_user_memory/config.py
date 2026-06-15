from typing import Annotated

from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit._common.validators import LMI
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.language_model.default_language_model import DEFAULT_GPT_4o
from unique_toolkit.language_model.infos import LanguageModelInfo


class UserMemoryConfig(BaseModel):
    model_config = get_configuration_dict()

    enabled: Annotated[
        bool,
        RJSFMetaTag.BooleanWidget.checkbox(
            help="Whether to enable persistent per-user memory.",
        ),
    ] = Field(
        default=False,
        description="Whether to enable persistent per-user memory.",
    )
    language_model: LMI = Field(
        default=LanguageModelInfo.from_name(DEFAULT_GPT_4o),
        description="The language model used for post-turn memory consolidation.",
    )
    max_tokens: int = Field(
        default=2000,
        ge=500,
        le=8000,
        description="Maximum size of the memory profile in tokens.",
    )
    root_folder: Annotated[str, RJSFMetaTag.SpecialWidget.hidden()] = Field(
        default="user-memory",
        min_length=1,
        description="Root KB folder used to store per-user memory profiles.",
    )
