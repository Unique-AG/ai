from typing import Any, ClassVar

from unique_mcp.meta.keys import MetaKeys
from unique_mcp.meta.part import MetaPart


class UniqueAIToolMeta(MetaPart):
    """MetaPart that publishes Unique AI configuration."""

    _META_KEY: ClassVar[str] = "unique.app/unique-ai"

    def __init__(
        self,
        *,
        tool_description_for_system_prompt: str = "",
        tool_description_for_user_prompt: str = "",
        tool_format_information_for_system_prompt: str = "",
    ) -> None:
        self._tool_description_for_system_prompt = tool_description_for_system_prompt
        self._tool_description_for_user_prompt = tool_description_for_user_prompt
        self._tool_format_information_for_system_prompt = (
            tool_format_information_for_system_prompt
        )

    def merge_into_meta(self, meta: dict[str, Any]) -> None:
        meta[MetaKeys.UNIQUE_AI_TOOL_SYSTEM_PROMPT.value] = (
            self._tool_description_for_system_prompt
        )
        meta[MetaKeys.UNIQUE_AI_TOOL_USER_PROMPT.value] = (
            self._tool_description_for_user_prompt
        )
        meta[MetaKeys.UNIQUE_AI_TOOL_FORMAT_INFORMATION.value] = (
            self._tool_format_information_for_system_prompt
        )
