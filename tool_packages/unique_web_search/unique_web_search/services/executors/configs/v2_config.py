from typing import Literal

from pydantic import Field

from unique_web_search.services.executors.configs.base import (
    BaseWebSearchModeConfig,
    WebSearchMode,
)
from unique_web_search.services.executors.configs.prompts import (
    DEFAULT_TOOL_DESCRIPTION,
    DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
)


class WebSearchV2Config(BaseWebSearchModeConfig[WebSearchMode.V2]):
    mode: Literal[WebSearchMode.V2] = WebSearchMode.V2

    max_steps: int = Field(
        default=5,
        description="Maximum number of sequential steps (searches or URL reads) allowed in a single WebSearch V2 plan.",
    )
    tool_description: str = Field(
        default=DEFAULT_TOOL_DESCRIPTION["v2"],
        description="Information to help the language model decide when to select this tool; describes the tool's general purpose and when it is relevant.",
    )
    tool_description_for_system_prompt: str = Field(
        default=DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT["v2"],
        description="Description of the tool's capabilities, intended for inclusion in system prompts to inform the language model what the tool can do.",
    )
