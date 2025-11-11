from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field
from unique_toolkit.agentic.tools.config import get_configuration_dict

from unique_web_search.services.helpers import (
    clean_model_title_generator,
)


class WebSearchMode(StrEnum):
    V1 = "v1"
    V2 = "v2 (Beta)"


T = TypeVar("T", bound=WebSearchMode)


class BaseWebSearchModeConfig(BaseModel, Generic[T]):
    model_config = get_configuration_dict(
        model_title_generator=clean_model_title_generator
    )
    mode: T = Field(
        description="The mode of the web search",
    )
