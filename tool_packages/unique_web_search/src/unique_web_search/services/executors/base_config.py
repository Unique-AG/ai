from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field
from unique_toolkit.agentic.tools.config import get_configuration_dict

from unique_web_search.services.helpers import (
    clean_model_title_generator,
)


class WebSearchMode(StrEnum):
    V1 = "v1"
    V2 = "v2"
    V3 = "v3"

    @staticmethod
    def get_enum_names() -> list[str]:
        """Human-readable labels for RJSF ui:enumNames.

        Order must match the enum member definition order (V1, V2, V3).
        """
        return [
            "V1 — Simple keyword searches with optional query refinement",
            "V2 — AI-planned multi-step research (search and read pages in sequence)",
            "V3 [Experimental] — Like V2, but pre-filters results by relevance (snippet judge) before fetching full pages",
        ]

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            aliases = {
                "v2 (beta)": cls.V2,
            }
            return aliases.get(value)
        return super()._missing_(value)


T = TypeVar("T", bound=WebSearchMode)


class BaseWebSearchModeConfig(BaseModel, Generic[T]):
    model_config = get_configuration_dict(
        model_title_generator=clean_model_title_generator
    )
    mode: T = Field(
        description="The mode of the web search",
    )
